import re
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils.cell import get_column_letter

from app.logger import get_logger


logger = get_logger(__name__)


DEFAULT_TARGET_CELLS = ("B10", "B14", "B18", "B22", "B26", "B30")


def _normalize_text(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "", text)
    return re.sub(r"[:：/／\\|_\-（）()【】\[\]{}]+", "", text)


def _cell_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _field_entries(field_library):
    entries = []

    description_fields = []
    if isinstance(field_library, dict):
        raw_description_fields = field_library.get("description_fields")
        if isinstance(raw_description_fields, dict):
            description_fields = list(raw_description_fields.keys())
        elif isinstance(raw_description_fields, list):
            description_fields = raw_description_fields

    for key in description_fields:
        key_text = str(key or "").strip()
        if not key_text:
            continue
        entries.append({
            "key": key_text,
            "label": key_text,
            "source": "description_field",
            "terms": [_normalize_text(key_text)],
        })

    raw_fields = field_library.get("fields") if isinstance(field_library, dict) else None
    if isinstance(raw_fields, dict):
        raw_fields = list(raw_fields.values())
    if isinstance(raw_fields, list):
        for field in raw_fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("key") or "").strip()
            label = str(field.get("label") or key).strip()
            description = str(field.get("description") or "").strip()
            terms = [_normalize_text(part) for part in [key, label, description] if str(part or "").strip()]
            entries.append({
                "key": key,
                "label": label,
                "source": "field_library",
                "terms": terms,
            })

    return entries


def _iter_text_cells(ws):
    merged_anchors = {}
    for merged_range in ws.merged_cells.ranges:
        merged_anchors[str(merged_range.start_cell.coordinate)] = str(merged_range)

    max_row = min(ws.max_row or 1, 200)
    max_column = min(ws.max_column or 1, 80)
    for row in ws.iter_rows(min_row=1, max_row=max_row, min_col=1, max_col=max_column):
        for cell in row:
            text = _cell_text(cell.value)
            if not text:
                continue
            yield {
                "coordinate": cell.coordinate,
                "row": cell.row,
                "column": cell.column,
                "text": text,
                "normalized_text": _normalize_text(text),
                "merged_range": merged_anchors.get(cell.coordinate, ""),
            }


def _find_target_cell(ws, row, column):
    max_column = min(ws.max_column or 1, 80)

    for offset in range(1, 6):
        target_column = column + offset
        if target_column > max_column:
            break
        cell = ws.cell(row=row, column=target_column)
        if _cell_text(cell.value) == "":
            return cell.coordinate

    for offset in range(1, 4):
        target_row = row + offset
        if target_row > (ws.max_row or row):
            break
        cell = ws.cell(row=target_row, column=column)
        if _cell_text(cell.value) == "":
            return cell.coordinate

    return f"{get_column_letter(column + 1)}{row}"


def _match_entry(cell, entries):
    text = cell.get("normalized_text", "")
    if not text:
        return None

    best = None
    best_score = 0
    for entry in entries:
        for term in entry.get("terms", []):
            if not term:
                continue
            if term == text:
                score = 100 + len(term)
            elif term in text or text in term:
                score = 60 + min(len(term), len(text))
            else:
                score = 0
            if score > best_score:
                best_score = score
                best = entry

    return best if best_score >= 62 else None


def _build_text_rule(entry, target_cell, index):
    source_key = entry.get("key") or f"field_{index}"
    return {
        "id": f"ai_{source_key}_{index}",
        "type": "text",
        "source": {
            "description_field": source_key,
        },
        "target": {
            "sheet": "active",
            "cell": target_cell,
        },
    }


def _build_checkbox_rule(cell, index):
    return {
        "id": f"ai_checkbox_{index}",
        "type": "checkbox",
        "condition": {
            "path": "product.form",
            "equals": "soft_capsule",
        },
        "target": {
            "sheet": "active",
            "cell": cell["coordinate"],
        },
        "checked_text": "☑",
        "unchecked_text": "☐",
    }


def _fallback_rules(entries, warnings):
    description_entries = [entry for entry in entries if entry.get("source") == "description_field"]
    if not description_entries:
        warnings.append("未找到可用于生成规则的 V4 description_fields")
        return []

    warnings.append("模板文本未匹配到明确字段，已按 description_fields 顺序生成回退规则")
    rules = []
    for index, entry in enumerate(description_entries[:len(DEFAULT_TARGET_CELLS)]):
        rules.append(_build_text_rule(entry, DEFAULT_TARGET_CELLS[index], index + 1))
    return rules


def analyze_template(template_path: str, field_library: dict) -> dict:
    warnings = []

    try:
        template_file = Path(str(template_path or "")).expanduser()
        if not template_file.is_file():
            return {
                "success": False,
                "error": f"template file not found: {template_path}",
            }

        entries = _field_entries(field_library if isinstance(field_library, dict) else {})
        if not entries:
            warnings.append("字段库为空，无法进行字段匹配")

        wb = load_workbook(template_file, data_only=False)
        ws = wb.active
        rules = []
        matched_keys = set()

        for cell in _iter_text_cells(ws):
            text = cell["text"]
            if "☐" in text or "☑" in text or "□" in text:
                rules.append(_build_checkbox_rule(cell, len(rules) + 1))
                continue

            entry = _match_entry(cell, entries)
            if not entry:
                continue

            if entry["source"] != "description_field":
                warnings.append(f"字段 {entry.get('label') or entry.get('key')} 暂未映射到 V4 description_fields，已跳过")
                continue

            if entry["key"] in matched_keys:
                continue

            matched_keys.add(entry["key"])
            target_cell = _find_target_cell(ws, cell["row"], cell["column"])
            rules.append(_build_text_rule(entry, target_cell, len(rules) + 1))

        if not rules:
            rules = _fallback_rules(entries, warnings)

        template_key = f"ai_{template_file.stem}_template"
        rules_config = {
            "version": "v4.15-ai-template",
            "description": "AI template parser generated Excel render rules",
            "templates": {
                template_key: {
                    "label": f"AI 自动解析模板：{template_file.name}",
                    "rules": rules,
                }
            },
        }

        logger.info(
            "V4 AI template parser finished: template_path=%s template_key=%s rules=%s warnings=%s",
            template_file,
            template_key,
            len(rules),
            len(warnings),
        )
        return {
            "success": True,
            "template_key": template_key,
            "rules_config": rules_config,
            "rules_count": len(rules),
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception("V4 AI template parser failed: template_path=%s", template_path)
        return {
            "success": False,
            "error": str(exc),
            "warnings": warnings,
        }
