import json
import re
from copy import deepcopy
from datetime import datetime

from app.runtime_paths import get_base_dir


RULES_DIR = get_base_dir() / "v4" / "rules"
STRUCTURED_RULE_PATH = RULES_DIR / "structured_excel_mapping.json"
TABLE_RULE_PATH = RULES_DIR / "table_mapping.json"
BLOCK_RULE_PATH = RULES_DIR / "block_merge_rules.json"
CANDIDATE_RULE_PATH = RULES_DIR / "auto_mapping_candidates.json"
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


def _now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_key(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "_", text)
    return text.strip("_") or "auto_table"


def _field_key(value):
    text = _safe_key(value)
    aliases = {
        "原料名": "name",
        "原料": "name",
        "含量": "amount",
        "百分比": "percentage",
        "标准": "standard",
        "结果": "result",
    }
    return aliases.get(text, text)


def _start_cell(item):
    start_cell = str(item.get("start_cell") or "").strip().upper()
    if start_cell:
        return start_cell

    start_row = str(item.get("start_row") or "").strip()
    columns = item.get("columns", [])
    first_col = "A"
    if isinstance(columns, list) and columns:
        first_col = str(columns[0].get("target_col") or "A").strip().upper() or "A"
    return f"{first_col}{start_row}" if start_row else ""


def _normalize_columns(columns, add_field=True):
    if not isinstance(columns, list):
        return []

    normalized_columns = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        label = str(column.get("label") or "").strip()
        target_col = str(column.get("target_col") or "").strip().upper()
        if not label or not target_col:
            continue

        normalized = {
            "label": label,
            "target_col": target_col,
        }
        field = str(column.get("field") or "").strip()
        if field:
            normalized["field"] = field
        elif add_field:
            normalized["field"] = _field_key(label)
        normalized_columns.append(normalized)
    return normalized_columns


def _confirmation_meta():
    return {
        "enabled": True,
        "confirmed": True,
        "confirmed_at": _now(),
        "mapping_source": "human_confirmed",
    }


def _candidate_meta(source):
    return {
        "enabled": False,
        "confirmed": False,
        "mapping_source": source,
        "candidate_created_at": _now(),
    }


def _valid_structured(item):
    return (
        isinstance(item, dict)
        and str(item.get("label") or "").strip()
        and str(item.get("source_path") or "").strip()
        and str(item.get("target_cell") or "").strip()
    )


def _normalize_structured(item, confirmed=False):
    mapping = {
        "label": str(item.get("label") or "").strip(),
        "source_path": str(item.get("source_path") or "").strip(),
        "target_cell": str(item.get("target_cell") or "").strip().upper(),
        "operation": str(item.get("operation") or "write_text").strip() or "write_text",
    }
    mapping.update(_confirmation_meta() if confirmed else _candidate_meta("auto_mapping_candidate"))
    return mapping


def _normalize_table(item, confirmed=False):
    table_name = str(item.get("table_name") or "").strip()
    table_key = str(item.get("table_key") or _safe_key(table_name)).strip()
    table = {
        "table_key": table_key,
        "table_name": table_name,
        "source_path": str(item.get("source_path") or f"product.tables.{table_key}").strip(),
        "start_cell": _start_cell(item),
        "columns": _normalize_columns(item.get("columns", []), add_field=True),
    }
    if item.get("semantic_type"):
        table["semantic_type"] = item.get("semantic_type")
    table.update(_confirmation_meta() if confirmed else _candidate_meta("auto_mapping_candidate"))
    return table


def _normalize_block(item, confirmed=False):
    block = {
        "block_name": str(item.get("block_name") or "").strip(),
        "target_cell": str(item.get("target_cell") or "").strip().upper(),
        "operation": str(item.get("operation") or "write_block").strip() or "write_block",
        "lines": deepcopy(item.get("lines")) if isinstance(item.get("lines"), list) else [],
        "source_path": str(item.get("source_path") or "").strip(),
    }
    block.update(_confirmation_meta() if confirmed else _candidate_meta("auto_mapping_candidate"))
    return block


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


def _upsert_by_key(items, next_item, keys):
    next_key = tuple(str(next_item.get(key) or "").strip() for key in keys)
    for index, item in enumerate(items):
        current_key = tuple(str(item.get(key) or "").strip() for key in keys)
        if current_key == next_key:
            items[index] = next_item
            return
    items.append(next_item)


def _save_structured(items):
    data = _read_json(STRUCTURED_RULE_PATH, {"version": RULE_VERSION, "mappings": []})
    mappings = data.get("mappings", [])
    mappings = [item for item in mappings if isinstance(item, dict)] if isinstance(mappings, list) else []

    saved = 0
    for item in items:
        if not _valid_structured(item):
            continue
        mapping = _normalize_structured(item, confirmed=True)
        _upsert_by_key(mappings, mapping, ("label", "source_path"))
        saved += 1

    data["version"] = RULE_VERSION
    data["mappings"] = mappings
    _write_json(STRUCTURED_RULE_PATH, data)
    return saved


def _save_tables(items):
    data = _read_json(TABLE_RULE_PATH, {"version": RULE_VERSION, "tables": []})
    tables = data.get("tables", [])
    tables = [item for item in tables if isinstance(item, dict)] if isinstance(tables, list) else []

    saved = 0
    for item in items:
        if not isinstance(item, dict) or not str(item.get("table_name") or "").strip():
            continue
        table = _normalize_table(item, confirmed=True)
        if not table.get("start_cell") or not table.get("columns"):
            continue
        _upsert_by_key(tables, table, ("table_key",))
        saved += 1

    data["version"] = RULE_VERSION
    data["tables"] = tables
    _write_json(TABLE_RULE_PATH, data)
    return saved


def _save_blocks(items):
    data = _read_json(BLOCK_RULE_PATH, {"version": RULE_VERSION, "blocks": []})
    blocks = data.get("blocks", [])
    blocks = [item for item in blocks if isinstance(item, dict)] if isinstance(blocks, list) else []

    saved = 0
    for item in items:
        if not isinstance(item, dict) or not str(item.get("block_name") or "").strip():
            continue
        block = _normalize_block(item, confirmed=True)
        if not block.get("target_cell"):
            continue
        _upsert_by_key(blocks, block, ("block_name",))
        saved += 1

    data["version"] = RULE_VERSION
    data["blocks"] = blocks
    _write_json(BLOCK_RULE_PATH, data)
    return saved


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
        "message": "已保存选中且确认的映射规则",
        "result": result,
    }


def save_auto_mapping_candidates(payload):
    lists = _payload_lists(payload)
    candidates = {
        "structured": [
            _normalize_structured(item, confirmed=False)
            for item in lists["structured"]
            if _valid_structured(item)
        ],
        "tables": [
            _normalize_table(item, confirmed=False)
            for item in lists["tables"]
            if isinstance(item, dict) and str(item.get("table_name") or "").strip()
        ],
        "blocks": [
            _normalize_block(item, confirmed=False)
            for item in lists["blocks"]
            if isinstance(item, dict) and str(item.get("block_name") or "").strip()
        ],
    }

    if not candidates["structured"] and not candidates["tables"] and not candidates["blocks"]:
        return {
            "success": False,
            "error": "没有可保存的候选映射",
        }

    data = {
        "version": RULE_VERSION,
        "generated_at": _now(),
        "note": "Auto Mapping 候选区。不会进入正式 mapping，必须在 Mapping Workbench 人工勾选确认后才能写入正式规则。",
        "candidates": candidates,
    }
    _write_json(CANDIDATE_RULE_PATH, data)
    return {
        "success": True,
        "message": "已保存为候选映射，未写入正式 Mapping",
        "result": {
            "structured_candidates": len(candidates["structured"]),
            "table_candidates": len(candidates["tables"]),
            "block_candidates": len(candidates["blocks"]),
            "candidate_file": str(CANDIDATE_RULE_PATH),
        },
    }


def apply_auto_mapping(payload):
    return save_auto_mapping_candidates(payload)
