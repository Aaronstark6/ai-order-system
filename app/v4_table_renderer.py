import json
import re
from copy import deepcopy

from app.runtime_paths import get_base_dir


DEFAULT_TABLE_MAPPING = {
    "version": "V4-Rebuild.4",
    "tables": [
        {
            "table_key": "formula_items",
            "table_name": "配方表",
            "source_path": "product.tables.formula_items",
            "start_cell": "A10",
            "columns": [
                {"label": "原料名", "field": "name", "target_col": "A"},
                {"label": "含量", "field": "amount", "target_col": "B"},
                {"label": "百分比", "field": "percentage", "target_col": "C"},
            ],
        },
        {
            "table_key": "test_items",
            "table_name": "检测项目表",
            "source_path": "product.tables.test_items",
            "start_cell": "A30",
            "columns": [
                {"label": "项目名称", "field": "name", "target_col": "A"},
                {"label": "标准", "field": "standard", "target_col": "B"},
                {"label": "结果", "field": "result", "target_col": "C"},
            ],
        },
    ],
}


def _mapping_path():
    return get_base_dir() / "v4" / "rules" / "table_mapping.json"


def _ensure_mapping_file():
    path = _mapping_path()
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_TABLE_MAPPING, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return path


def load_table_mapping():
    path = _ensure_mapping_file()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = deepcopy(DEFAULT_TABLE_MAPPING)
    return data if isinstance(data, dict) else deepcopy(DEFAULT_TABLE_MAPPING)


def _get_nested(data, source_path):
    current = data
    for part in str(source_path or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict) or part not in current:
            return None
        current = current.get(part)
    return current


def _start_row(start_cell):
    match = re.fullmatch(r"\s*[A-Za-z]+\s*(\d+)\s*", str(start_cell or ""))
    return int(match.group(1)) if match else 1


def _row_value(row, field):
    if not isinstance(row, dict):
        return ""
    value = row.get(field, "")
    return "" if value is None else str(value)


def build_table_operations(order_object):
    mapping = load_table_mapping()
    warnings = []
    operations = []

    for table in mapping.get("tables", []) if isinstance(mapping.get("tables"), list) else []:
        if not isinstance(table, dict):
            continue

        table_name = str(table.get("table_name") or table.get("table_key") or "").strip()
        table_key = str(table.get("table_key") or "").strip()
        rows = _get_nested(order_object, table.get("source_path"))
        if rows is None:
            warnings.append(f"{table.get('source_path', '')} 未找到，已跳过 {table_name or table_key}。")
            rows = []
        if not isinstance(rows, list):
            warnings.append(f"{table.get('source_path', '')} 不是 list，已跳过 {table_name or table_key}。")
            rows = []

        start_row = _start_row(table.get("start_cell"))
        columns = table.get("columns", [])
        columns = columns if isinstance(columns, list) else []

        for row_index, row in enumerate(rows):
            row_number = start_row + row_index
            for column in columns:
                if not isinstance(column, dict):
                    continue
                target_col = str(column.get("target_col") or "").strip().upper()
                field = str(column.get("field") or "").strip()
                if not target_col or not field:
                    continue
                operations.append(
                    {
                        "table_key": table_key,
                        "table_name": table_name,
                        "row_number": row_number,
                        "label": str(column.get("label") or ""),
                        "field": field,
                        "target_cell": f"{target_col}{row_number}",
                        "operation": "write_text",
                        "value": _row_value(row, field),
                    }
                )

    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
