import json
import re
from copy import deepcopy

from app.runtime_paths import get_base_dir


RULES_DIR = get_base_dir() / "v4" / "rules"
STRUCTURED_RULE_PATH = RULES_DIR / "structured_excel_mapping.json"
TABLE_RULE_PATH = RULES_DIR / "table_mapping.json"
BLOCK_RULE_PATH = RULES_DIR / "block_merge_rules.json"
RULE_VERSION = "V4-Rebuild"


def _read_json(path, default_value):
    if not path.is_file():
        return deepcopy(default_value)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return deepcopy(default_value)
    return data if isinstance(data, dict) else deepcopy(default_value)


def _write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _safe_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text)
    return text.strip("_") or "auto_table"


def _field_key(value):
    text = _safe_key(value)
    if text in {"原料名", "原料"}:
        return "name"
    if text == "含量":
        return "amount"
    if text == "百分比":
        return "percentage"
    if text == "标准":
        return "standard"
    if text == "结果":
        return "result"
    return text


def _valid_structured(item):
    return (
        isinstance(item, dict)
        and str(item.get("label") or "").strip()
        and str(item.get("source_path") or "").strip()
        and str(item.get("target_cell") or "").strip()
    )


def _start_cell(item):
    start_cell = str(item.get("start_cell") or "").strip()
    if start_cell:
        return start_cell

    start_row = str(item.get("start_row") or "").strip()
    columns = item.get("columns", [])
    first_col = "A"
    if isinstance(columns, list) and columns:
        first_col = str(columns[0].get("target_col") or "A").strip() or "A"
    return f"{first_col}{start_row}" if start_row else ""


def _normalize_columns(columns, add_field=True):
    if not isinstance(columns, list):
        return []

    normalized_columns = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        label = str(column.get("label") or "").strip()
        target_col = str(column.get("target_col") or "").strip()
        if not label or not target_col:
            continue

        normalized = deepcopy(column)
        normalized["label"] = label
        normalized["target_col"] = target_col
        if add_field and not str(normalized.get("field") or "").strip():
            normalized["field"] = _field_key(label)
        normalized_columns.append(normalized)
    return normalized_columns


def _normalize_structured_for_save(item, include_confirmation=True):
    mapping = {
        "label": str(item.get("label") or "").strip(),
        "source_path": str(item.get("source_path") or "").strip(),
        "target_cell": str(item.get("target_cell") or "").strip(),
        "operation": str(item.get("operation") or "write_text").strip() or "write_text",
    }
    if include_confirmation:
        mapping["auto_generated"] = True
        mapping["confirmed"] = True
    return mapping


def _save_structured(items):
    data = _read_json(STRUCTURED_RULE_PATH, {"version": RULE_VERSION, "mappings": []})
    mappings = data.get("mappings", [])
    if not isinstance(mappings, list):
        mappings = []

    index = {
        (str(item.get("label") or "").strip(), str(item.get("target_cell") or "").strip()): idx
        for idx, item in enumerate(mappings)
        if isinstance(item, dict)
    }
    saved = 0
    for item in items:
        if not _valid_structured(item):
            continue
        mapping = _normalize_structured_for_save(item, include_confirmation=True)
        key = (mapping["label"], mapping["target_cell"])
        if key in index:
            mappings[index[key]].update(mapping)
        else:
            index[key] = len(mappings)
            mappings.append(mapping)
        saved += 1

    data["version"] = data.get("version") or RULE_VERSION
    data["mappings"] = mappings
    _write_json(STRUCTURED_RULE_PATH, data)
    return saved


def _save_tables(items):
    data = _read_json(TABLE_RULE_PATH, {"version": RULE_VERSION, "tables": []})
    tables = data.get("tables", [])
    if not isinstance(tables, list):
        tables = []

    index = {
        str(item.get("table_name") or "").strip(): idx
        for idx, item in enumerate(tables)
        if isinstance(item, dict) and str(item.get("table_name") or "").strip()
    }
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        table_name = str(item.get("table_name") or "").strip()
        if not table_name:
            continue

        table = {
            "table_key": str(item.get("table_key") or _safe_key(table_name)),
            "table_name": table_name,
            "source_path": str(item.get("source_path") or f"product.tables.{_safe_key(table_name)}"),
            "start_cell": _start_cell(item),
            "columns": _normalize_columns(item.get("columns", []), add_field=True),
        }
        if item.get("semantic_type"):
            table["semantic_type"] = item.get("semantic_type")

        if table_name in index:
            tables[index[table_name]].update(table)
        else:
            index[table_name] = len(tables)
            tables.append(table)
        saved += 1

    data["version"] = data.get("version") or RULE_VERSION
    data["tables"] = tables
    _write_json(TABLE_RULE_PATH, data)
    return saved


def _save_blocks(items):
    data = _read_json(BLOCK_RULE_PATH, {"version": RULE_VERSION, "blocks": []})
    blocks = data.get("blocks", [])
    if not isinstance(blocks, list):
        blocks = []

    index = {
        str(item.get("block_name") or "").strip(): idx
        for idx, item in enumerate(blocks)
        if isinstance(item, dict) and str(item.get("block_name") or "").strip()
    }
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        block_name = str(item.get("block_name") or "").strip()
        target_cell = str(item.get("target_cell") or "").strip()
        if not block_name or not target_cell:
            continue
        block = {
            "block_name": block_name,
            "target_cell": target_cell,
            "lines": item.get("lines") if isinstance(item.get("lines"), list) else [],
        }
        if item.get("source_path"):
            block["source_path"] = item.get("source_path")

        if block_name in index:
            blocks[index[block_name]].update(block)
        else:
            index[block_name] = len(blocks)
            blocks.append(block)
        saved += 1

    data["version"] = data.get("version") or RULE_VERSION
    data["blocks"] = blocks
    _write_json(BLOCK_RULE_PATH, data)
    return saved


def _apply_structured(items):
    data = _read_json(STRUCTURED_RULE_PATH, {"version": RULE_VERSION, "mappings": []})
    existing = data.get("mappings", [])
    mappings = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []

    saved = 0
    for item in items:
        if not _valid_structured(item):
            continue
        mapping = _normalize_structured_for_save(item, include_confirmation=False)
        label = mapping["label"]
        target_cell = mapping["target_cell"]

        mappings = [
            current
            for current in mappings
            if str(current.get("target_cell") or "").strip() != target_cell
            and (
                str(current.get("label") or "").strip(),
                str(current.get("target_cell") or "").strip(),
            )
            != (label, target_cell)
        ]
        mappings.append(mapping)
        saved += 1

    data["version"] = RULE_VERSION
    data["mappings"] = mappings
    _write_json(STRUCTURED_RULE_PATH, data)
    return saved


def _apply_tables(items):
    data = _read_json(TABLE_RULE_PATH, {"version": RULE_VERSION, "tables": []})
    existing = data.get("tables", [])
    tables = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []

    index = {
        str(item.get("table_key") or "").strip(): idx
        for idx, item in enumerate(tables)
        if str(item.get("table_key") or "").strip()
    }
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        table_name = str(item.get("table_name") or "").strip()
        if not table_name:
            continue
        table_key = str(item.get("table_key") or _safe_key(table_name)).strip()
        table = {
            "table_key": table_key,
            "table_name": table_name,
            "source_path": str(item.get("source_path") or f"product.tables.{table_key}"),
            "start_cell": _start_cell(item),
            "columns": _normalize_columns(item.get("columns", []), add_field=True),
        }
        if item.get("semantic_type"):
            table["semantic_type"] = item.get("semantic_type")

        if table_key in index:
            tables[index[table_key]] = table
        else:
            index[table_key] = len(tables)
            tables.append(table)
        saved += 1

    data["version"] = RULE_VERSION
    data["tables"] = tables
    _write_json(TABLE_RULE_PATH, data)
    return saved


def _apply_blocks(items):
    data = _read_json(BLOCK_RULE_PATH, {"version": RULE_VERSION, "blocks": []})
    existing = data.get("blocks", [])
    blocks = [item for item in existing if isinstance(item, dict)] if isinstance(existing, list) else []

    index = {
        str(item.get("block_name") or "").strip(): idx
        for idx, item in enumerate(blocks)
        if str(item.get("block_name") or "").strip()
    }
    saved = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        block_name = str(item.get("block_name") or "").strip()
        target_cell = str(item.get("target_cell") or "").strip()
        if not block_name or not target_cell:
            continue
        block = {
            "block_name": block_name,
            "target_cell": target_cell,
            "lines": deepcopy(item.get("lines")) if isinstance(item.get("lines"), list) else [],
            "source_path": str(item.get("source_path") or ""),
        }

        if block_name in index:
            blocks[index[block_name]] = block
        else:
            index[block_name] = len(blocks)
            blocks.append(block)
        saved += 1

    data["version"] = RULE_VERSION
    data["blocks"] = blocks
    _write_json(BLOCK_RULE_PATH, data)
    return saved


def _payload_lists(payload):
    payload = payload if isinstance(payload, dict) else {}
    structured = payload.get("structured", [])
    tables = payload.get("tables", [])
    blocks = payload.get("blocks", [])
    return {
        "structured": structured if isinstance(structured, list) else [],
        "tables": tables if isinstance(tables, list) else [],
        "blocks": blocks if isinstance(blocks, list) else [],
    }


def save_selected_mappings(payload):
    lists = _payload_lists(payload)
    if not lists["structured"] and not lists["tables"] and not lists["blocks"]:
        return {
            "success": False,
            "error": "没有选择任何映射",
        }

    result = {
        "structured_saved": _save_structured(lists["structured"]),
        "tables_saved": _save_tables(lists["tables"]),
        "blocks_saved": _save_blocks(lists["blocks"]),
    }
    return {
        "success": True,
        "message": "映射规则保存成功",
        "result": result,
    }


def apply_auto_mapping(payload):
    lists = _payload_lists(payload)
    if not lists["structured"] and not lists["tables"] and not lists["blocks"]:
        return {
            "success": False,
            "error": "没有选择任何映射",
        }

    result = {
        "structured_saved": _apply_structured(lists["structured"]),
        "tables_saved": _apply_tables(lists["tables"]),
        "blocks_saved": _apply_blocks(lists["blocks"]),
    }
    return {
        "success": True,
        "message": "已成功写入正式 Mapping",
        "result": result,
    }
