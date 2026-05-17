import json
from json import JSONDecodeError

from openpyxl.utils.cell import coordinate_to_tuple

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_table_mapping_path():
    return get_base_dir() / "v4" / "rules" / "table_mapping.json"


def load_table_mapping():
    mapping_path = _get_table_mapping_path()
    try:
        with mapping_path.open("r", encoding="utf-8") as f:
            mapping = json.load(f)
    except JSONDecodeError as exc:
        logger.error("[TableRenderer] Table mapping JSON parse failed: path=%s error=%s", mapping_path, exc)
        return {}
    except OSError as exc:
        logger.error("[TableRenderer] Table mapping read failed: path=%s error=%s", mapping_path, exc)
        return {}

    return mapping if isinstance(mapping, dict) else {}


def _resolve_source_path(data, source_path):
    current = data
    for part in str(source_path or "").split("."):
        if not part:
            return None, False
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current.get(part)
    return current, True


def _normalize_tables(table_mapping):
    tables = table_mapping.get("tables", []) if isinstance(table_mapping, dict) else []
    return tables if isinstance(tables, list) else []


def _normalize_columns(table):
    columns = table.get("columns", []) if isinstance(table, dict) else []
    if not isinstance(columns, list):
        return []

    normalized = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        field = str(column.get("field") or "").strip()
        target_col = str(column.get("target_col") or "").strip().upper()
        if field and target_col:
            normalized.append({
                "label": str(column.get("label") or field).strip(),
                "field": field,
                "target_col": target_col,
            })
    return normalized


def _start_row_from_cell(start_cell):
    try:
        row, _ = coordinate_to_tuple(str(start_cell or "").strip())
        return row
    except ValueError:
        return None


def order_object_to_table_operations(order_object, table_mapping):
    warnings = []
    operations = []

    if not isinstance(order_object, dict):
        return {
            "success": False,
            "operations": [],
            "warnings": ["Order Object 必须是对象"],
        }

    for table in _normalize_tables(table_mapping):
        if not isinstance(table, dict):
            continue

        table_name = str(table.get("table_name") or "").strip() or "未命名表格"
        source_path = str(table.get("source_path") or "").strip()
        start_cell = str(table.get("start_cell") or "").strip()
        start_row = _start_row_from_cell(start_cell)
        columns = _normalize_columns(table)

        if not source_path:
            warnings.append(f"{table_name} 缺少 source_path，已跳过。")
            continue
        if start_row is None:
            warnings.append(f"{table_name} 的 start_cell 无效，已跳过。")
            continue
        if not columns:
            warnings.append(f"{table_name} 缺少 columns，已跳过。")
            continue

        rows, found = _resolve_source_path(order_object, source_path)
        if not found:
            warnings.append(f"未找到表格数据：{source_path}")
            continue
        if not isinstance(rows, list):
            warnings.append(f"表格数据不是数组：{source_path}")
            continue

        for row_index, row_data in enumerate(rows):
            if not isinstance(row_data, dict):
                warnings.append(f"{table_name} 第 {row_index + 1} 行不是对象，已跳过。")
                continue
            excel_row = start_row + row_index
            for column in columns:
                value = row_data.get(column["field"], "")
                operations.append({
                    "operation": "write_text",
                    "target_cell": f"{column['target_col']}{excel_row}",
                    "value": "" if value is None else str(value),
                    "table_name": table_name,
                    "row_index": row_index,
                    "field": column["field"],
                })

    logger.info(
        "[TableRenderer] Table operations generated: operations=%s warnings=%s",
        len(operations),
        len(warnings),
    )
    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
