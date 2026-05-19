import json
import re
from copy import deepcopy

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string, get_column_letter

from app.runtime_paths import get_base_dir


RULES_DIR = get_base_dir() / "v4" / "rules"
STRUCTURED_MAPPING_PATH = RULES_DIR / "structured_excel_mapping.json"
TABLE_MAPPING_PATH = RULES_DIR / "table_mapping.json"
BLOCK_RULES_PATH = RULES_DIR / "block_merge_rules.json"
SOURCE_PRIORITY = {"structured": 3, "table": 2, "block": 1}
SUSPECT_TEMPLATE_TEXT_ROWS = range(10, 19)
SUSPECT_TEMPLATE_TEXT_COLS = {"A", "B", "C"}
LEGACY_TEST_CELLS = {"B1", "B2", "B6"}


def _read_rule_file(path, default_value):
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(default_value, f, ensure_ascii=False, indent=2)
            f.write("\n")
        return deepcopy(default_value)
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return deepcopy(default_value)
    return data if isinstance(data, dict) else deepcopy(default_value)


def load_structured_mapping():
    return _read_rule_file(STRUCTURED_MAPPING_PATH, {"version": "V4-Rebuild", "mappings": []})


def load_table_mapping():
    return _read_rule_file(TABLE_MAPPING_PATH, {"version": "V4-Rebuild", "tables": []})


def load_block_rules():
    return _read_rule_file(BLOCK_RULES_PATH, {"version": "V4-Rebuild", "blocks": []})


def _is_enabled(item):
    return isinstance(item, dict) and item.get("enabled") is not False


def count_enabled_mappings():
    structured = load_structured_mapping().get("mappings", [])
    tables = load_table_mapping().get("tables", [])
    blocks = load_block_rules().get("blocks", [])
    structured = structured if isinstance(structured, list) else []
    tables = tables if isinstance(tables, list) else []
    blocks = blocks if isinstance(blocks, list) else []
    return {
        "enabled_structured_mappings": sum(1 for item in structured if _is_enabled(item)),
        "enabled_table_mappings": sum(1 for item in tables if _is_enabled(item)),
        "enabled_block_rules": sum(1 for item in blocks if _is_enabled(item)),
    }


def _get_nested(data, source_path):
    current = data
    for part in str(source_path or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current.get(part)
    return current, True


def _field_entry_value(entry):
    if isinstance(entry, dict):
        for key in ("value", "text", "name", "label"):
            if key in entry:
                return entry.get(key)
        return ""
    return entry


def _get_product_field(order_object, identifier):
    product = order_object.get("product", {}) if isinstance(order_object, dict) else {}
    fields = product.get("fields", {}) if isinstance(product, dict) else {}
    if not isinstance(fields, dict):
        return None, False

    target = str(identifier or "").strip()
    if target in fields:
        return _field_entry_value(fields.get(target)), True

    for field_key, entry in fields.items():
        if str(field_key) == target:
            return _field_entry_value(entry), True
        if isinstance(entry, dict):
            aliases = {
                str(entry.get("label") or "").strip(),
                str(entry.get("name") or "").strip(),
                str(entry.get("field_name") or "").strip(),
                str(entry.get("field_id") or "").strip(),
                str(entry.get("key") or "").strip(),
            }
            if target in aliases:
                return _field_entry_value(entry), True
    return None, False


def resolve_source_value(order_object, source_path):
    source_path = str(source_path or "").strip()
    if not source_path:
        return None, False
    if source_path.startswith("product.fields."):
        return _get_product_field(order_object, source_path[len("product.fields."):])
    return _get_nested(order_object, source_path)


def _string_value(value):
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "\n".join(_string_value(item) for item in value if _string_value(item))
    if isinstance(value, dict):
        return "\n".join(f"{key}: {_string_value(item)}" for key, item in value.items() if _string_value(item))
    return str(value)


def _format_structured_value(value, operation):
    operation = str(operation or "write_text").strip()
    if operation == "write_number":
        if value is None or value == "":
            return ""
        try:
            number = float(str(value).replace(",", "").strip())
        except (TypeError, ValueError):
            return _string_value(value)
        return int(number) if number.is_integer() else number
    if operation == "write_multiline":
        return _string_value(value)
    return "" if value is None else str(value)


def _parse_cell(cell_ref):
    try:
        column, row = coordinate_from_string(str(cell_ref or "").strip())
        return column.upper(), int(row)
    except Exception:
        return "", None


def _start_row(start_cell):
    _, row = _parse_cell(start_cell)
    return row or 1


def _row_value(row, field):
    if not isinstance(row, dict):
        return ""
    value = row.get(str(field or ""), "")
    return "" if value is None else value


def _target_cell(target_col, row_number):
    col = str(target_col or "").strip().upper()
    if not col:
        return ""
    if col.isdigit():
        col = get_column_letter(int(col))
    return f"{col}{row_number}"


def _operation_source(operation):
    source = str(operation.get("source") or operation.get("type") or "").strip().lower()
    if source in {"structured", "table", "block"}:
        return source
    op_type = str(operation.get("op_type") or operation.get("operation") or "").strip().lower()
    if op_type == "write_table_cell":
        return "table"
    if op_type == "write_block":
        return "block"
    return "structured" if op_type else source


def _operation_target_cell(operation):
    return str(operation.get("target_cell") or operation.get("start_cell") or "").strip().upper()


def _operation_value_for_safety(operation):
    source = _operation_source(operation)
    if source == "block":
        return operation.get("content", operation.get("value"))
    return operation.get("value")


def _is_empty_write_operation(operation):
    source = _operation_source(operation)
    if source == "table" and "cell_operations" in operation:
        rows = operation.get("rows")
        cells = operation.get("cell_operations")
        return not rows or not cells
    value = _operation_value_for_safety(operation)
    if value is None:
        return True
    return str(value).strip() == ""


def _operation_title(operation):
    for key in ("label", "table_name", "table_key", "block_name", "source_path", "field"):
        text = str(operation.get(key) or "").strip()
        if text:
            return text
    return _operation_source(operation) or "operation"


def _is_suspect_template_text_cell(target_cell):
    column, row_number = _parse_cell(target_cell)
    return column in SUSPECT_TEMPLATE_TEXT_COLS and row_number in SUSPECT_TEMPLATE_TEXT_ROWS


def _skip_operation(operation, reason, code):
    item = deepcopy(operation)
    item["skipped"] = True
    item["safety_status"] = "skipped"
    item["skip_reason"] = reason
    item["skip_code"] = code
    return item


def detect_mapping_conflicts(operations):
    conflicts = []
    warnings = []
    skipped_operations = []
    candidates = []
    by_cell = {}
    all_by_cell = {}

    for index, operation in enumerate(operations if isinstance(operations, list) else [], start=1):
        if not isinstance(operation, dict):
            warnings.append(f"第 {index} 条 operation 格式无效，已跳过。")
            skipped_operations.append(
                {
                    "skipped": True,
                    "safety_status": "skipped",
                    "skip_code": "invalid_operation",
                    "skip_reason": "operation 格式无效",
                }
            )
            continue

        item = deepcopy(operation)
        source = _operation_source(item)
        target_cell = _operation_target_cell(item)
        item["source"] = source
        item["type"] = item.get("type") or source
        item["target_cell"] = target_cell
        item["_safety_index"] = index

        if not target_cell:
            reason = f"{_operation_title(item)} 缺少 target_cell，已跳过。"
            warnings.append(reason)
            skipped_operations.append(_skip_operation(item, reason, "missing_target_cell"))
            continue

        all_by_cell.setdefault(target_cell, []).append(item)

        if _is_empty_write_operation(item):
            reason = f"{target_cell} value 为空，已跳过 {_operation_title(item)}。"
            warnings.append(reason)
            skipped_operations.append(_skip_operation(item, reason, "empty_value"))
            continue

        if _is_suspect_template_text_cell(target_cell):
            item["template_text_area_warning"] = True
            warnings.append(f"{target_cell} 位于疑似模板大文本区域，请确认 mapping 不会覆盖模板原内容。")

        if target_cell in LEGACY_TEST_CELLS:
            item["legacy_test_cell_warning"] = True
            warnings.append(f"{target_cell} 属于旧测试坐标，请确认是否适配当前真实模板。")

        candidates.append(item)
        by_cell.setdefault(target_cell, []).append(item)

    skipped_indexes = set()
    conflict_cells = set()
    for target_cell, items in by_cell.items():
        if len(items) <= 1:
            continue

        sources = sorted({_operation_source(item) for item in items})
        keep = sorted(
            items,
            key=lambda item: (-SOURCE_PRIORITY.get(_operation_source(item), 0), item.get("_safety_index", 0)),
        )[0]
        conflict_cells.add(target_cell)
        conflict = {
            "target_cell": target_cell,
            "sources": sources,
            "operation_count": len(items),
            "kept_source": _operation_source(keep),
            "kept_operation": _operation_title(keep),
            "skipped": [],
        }
        for item in items:
            if item is keep:
                continue
            reason = (
                f"{target_cell} 同时存在 {'、'.join(sources)} 写入，"
                f"已保留 {_operation_source(keep)}，跳过 {_operation_source(item)}。"
            )
            skipped_indexes.add(item.get("_safety_index"))
            skipped = _skip_operation(item, reason, "same_cell_conflict")
            skipped["conflict"] = True
            skipped_operations.append(skipped)
            conflict["skipped"].append(
                {
                    "source": _operation_source(item),
                    "operation": _operation_title(item),
                    "reason": reason,
                }
            )
            warnings.append(reason)
        conflicts.append(conflict)

    for target_cell, items in all_by_cell.items():
        if target_cell in conflict_cells or len(items) <= 1:
            continue
        sources = sorted({_operation_source(item) for item in items})
        if len(sources) <= 1:
            continue
        keep_candidates = by_cell.get(target_cell, [])
        if not keep_candidates:
            continue
        keep = sorted(
            keep_candidates,
            key=lambda item: (-SOURCE_PRIORITY.get(_operation_source(item), 0), item.get("_safety_index", 0)),
        )[0]
        conflict_cells.add(target_cell)
        skipped_sources = [
            _operation_source(item)
            for item in items
            if item.get("_safety_index") != keep.get("_safety_index")
        ]
        reason = (
            f"{target_cell} 同时存在 {'、'.join(sources)} 写入，"
            f"已保留 {_operation_source(keep)}，跳过 {'、'.join(skipped_sources)}。"
        )
        warnings.append(reason)
        conflicts.append(
            {
                "target_cell": target_cell,
                "sources": sources,
                "operation_count": len(items),
                "kept_source": _operation_source(keep),
                "kept_operation": _operation_title(keep),
                "skipped": [
                    {
                        "source": _operation_source(item),
                        "operation": _operation_title(item),
                        "reason": reason,
                    }
                    for item in items
                    if item.get("_safety_index") != keep.get("_safety_index")
                ],
            }
        )

    for item in skipped_operations:
        if isinstance(item, dict) and item.get("target_cell") in conflict_cells:
            item["conflict"] = True

    safe_operations = []
    for item in candidates:
        if item.get("_safety_index") in skipped_indexes:
            continue
        item = deepcopy(item)
        item.pop("_safety_index", None)
        item["safety_status"] = "ok"
        item["conflict"] = item.get("target_cell") in conflict_cells
        safe_operations.append(item)

    for item in skipped_operations:
        if isinstance(item, dict):
            item.pop("_safety_index", None)

    return {
        "has_conflicts": bool(conflicts),
        "conflicts": conflicts,
        "warnings": warnings,
        "skipped_operations": skipped_operations,
        "operations": safe_operations,
    }


def build_structured_operations(order_object):
    mapping = load_structured_mapping()
    operations = []
    warnings = []
    for item in mapping.get("mappings", []) if isinstance(mapping.get("mappings"), list) else []:
        if not isinstance(item, dict):
            continue
        if not _is_enabled(item):
            continue
        source_path = str(item.get("source_path") or "").strip()
        target_cell = str(item.get("target_cell") or "").strip().upper()
        operation = str(item.get("operation") or "write_text").strip() or "write_text"
        value, found = resolve_source_value(order_object, source_path)
        if not found:
            warnings.append(f"{source_path} 未找到，已使用空值。")
            value = ""
        operations.append(
            {
                "type": "structured",
                "label": str(item.get("label") or ""),
                "operation": operation,
                "target_cell": target_cell,
                "value": _format_structured_value(value, operation),
                "source_path": source_path,
                "mapping_confirmed": bool(item.get("confirmed") or item.get("mapping_confirmed")),
            }
        )
    return {"success": True, "operations": operations, "warnings": warnings}


def build_table_operations(order_object):
    mapping = load_table_mapping()
    operations = []
    warnings = []
    for table in mapping.get("tables", []) if isinstance(mapping.get("tables"), list) else []:
        if not isinstance(table, dict):
            continue
        if not _is_enabled(table):
            continue
        table_name = str(table.get("table_name") or table.get("table_key") or "").strip()
        table_key = str(table.get("table_key") or table_name or "").strip()
        source_path = str(table.get("source_path") or "").strip()
        rows, found = resolve_source_value(order_object, source_path)
        if not found:
            warnings.append(f"{source_path} 未找到，已跳过 {table_name or table_key}。")
            rows = []
        if not isinstance(rows, list):
            warnings.append(f"{source_path} 不是数组，已跳过 {table_name or table_key}。")
            rows = []

        start_cell = str(table.get("start_cell") or "").strip().upper()
        row_number = _start_row(start_cell)
        columns = table.get("columns", [])
        columns = columns if isinstance(columns, list) else []
        rendered_rows = []
        cell_operations = []

        for row_index, row in enumerate(rows):
            current_row_number = row_number + row_index
            cells = []
            values = {}
            for column in columns:
                if not isinstance(column, dict):
                    continue
                target_col = str(column.get("target_col") or "").strip().upper()
                field = str(column.get("field") or column.get("source_path") or column.get("label") or "").strip()
                cell_ref = _target_cell(target_col, current_row_number)
                if not cell_ref or not field:
                    continue
                value = _row_value(row, field)
                cell = {
                    "target_cell": cell_ref,
                    "target_col": target_col,
                    "row_number": current_row_number,
                    "label": str(column.get("label") or ""),
                    "field": field,
                    "value": "" if value is None else value,
                    "mapping_confirmed": bool(table.get("confirmed") or table.get("mapping_confirmed")),
                }
                cells.append(cell)
                values[target_col] = "" if value is None else value
                cell_operations.append(cell)
            rendered_rows.append(
                {
                    "row_number": current_row_number,
                    "cells": cells,
                    "values": values,
                }
            )

        operations.append(
            {
                "type": "table",
                "table_key": table_key,
                "table_name": table_name,
                "source_path": source_path,
                "start_cell": start_cell,
                "columns": deepcopy(columns),
                "rows": rendered_rows,
                "cell_operations": cell_operations,
                "mapping_confirmed": bool(table.get("confirmed") or table.get("mapping_confirmed")),
            }
        )
    return {"success": True, "operations": operations, "warnings": warnings}


def _line_value(order_object, line):
    if not isinstance(line, dict):
        return None, False
    if line.get("field_id"):
        return _get_product_field(order_object, line.get("field_id"))
    return resolve_source_value(order_object, line.get("source_path"))


def build_block_operations(order_object):
    rules = load_block_rules()
    operations = []
    warnings = []
    for block in rules.get("blocks", []) if isinstance(rules.get("blocks"), list) else []:
        if not isinstance(block, dict):
            continue
        if not _is_enabled(block):
            continue
        target_cell = str(block.get("target_cell") or "").strip().upper()
        lines_config = block.get("lines", [])
        lines_config = lines_config if isinstance(lines_config, list) else []
        rendered_lines = []

        if lines_config:
            for line in lines_config:
                if not isinstance(line, dict):
                    continue
                label = str(line.get("label") or line.get("field_id") or line.get("source_path") or "").strip()
                value, found = _line_value(order_object, line)
                value = _string_value(value).strip()
                if not found:
                    warnings.append(f"{label or '未命名字段'} 未找到，已跳过。")
                    continue
                if not value:
                    continue
                rendered_lines.append(f"{label}: {value}" if label else value)
        elif block.get("source_path"):
            value, found = resolve_source_value(order_object, block.get("source_path"))
            if found and _string_value(value).strip():
                rendered_lines.append(_string_value(value).strip())

        operations.append(
            {
                "type": "block",
                "block_name": str(block.get("block_name") or "").strip(),
                "target_cell": target_cell,
                "operation": str(block.get("operation") or "write_multiline").strip() or "write_multiline",
                "content": "\n".join(rendered_lines),
                "value": "\n".join(rendered_lines),
                "lines": deepcopy(lines_config),
                "source_path": str(block.get("source_path") or "").strip(),
                "mapping_confirmed": bool(block.get("confirmed") or block.get("mapping_confirmed")),
            }
        )
    return {"success": True, "operations": operations, "warnings": warnings}


def build_unified_operations(structured_operations, table_operations, block_operations):
    unified = []
    for operation in structured_operations if isinstance(structured_operations, list) else []:
        if not isinstance(operation, dict):
            continue
        unified.append(
            {
                "op_type": str(operation.get("operation") or "write_text").strip() or "write_text",
                "source": "structured",
                "type": "structured",
                "target_cell": str(operation.get("target_cell") or "").strip().upper(),
                "value": operation.get("value", ""),
                "source_path": str(operation.get("source_path") or ""),
                "label": str(operation.get("label") or ""),
                "mapping_confirmed": bool(operation.get("mapping_confirmed") or operation.get("confirmed")),
            }
        )

    for table in table_operations if isinstance(table_operations, list) else []:
        if not isinstance(table, dict):
            continue
        for cell in table.get("cell_operations", []) if isinstance(table.get("cell_operations"), list) else []:
            if not isinstance(cell, dict):
                continue
            unified.append(
                {
                    "op_type": "write_table_cell",
                    "source": "table",
                    "type": "table",
                    "table_key": str(table.get("table_key") or ""),
                    "table_name": str(table.get("table_name") or ""),
                    "target_cell": str(cell.get("target_cell") or "").strip().upper(),
                    "value": cell.get("value", ""),
                    "field": str(cell.get("field") or ""),
                    "label": str(cell.get("label") or ""),
                    "row_number": cell.get("row_number"),
                    "mapping_confirmed": bool(table.get("mapping_confirmed") or table.get("confirmed")),
                }
            )

    for operation in block_operations if isinstance(block_operations, list) else []:
        if not isinstance(operation, dict):
            continue
        unified.append(
            {
                "op_type": "write_block",
                "source": "block",
                "type": "block",
                "block_name": str(operation.get("block_name") or ""),
                "target_cell": str(operation.get("target_cell") or "").strip().upper(),
                "value": operation.get("content", operation.get("value", "")),
                "source_path": str(operation.get("source_path") or ""),
                "mapping_confirmed": bool(operation.get("mapping_confirmed") or operation.get("confirmed")),
            }
        )

    return {
        "success": True,
        "operations": unified,
        "counts": {
            "structured": len(structured_operations) if isinstance(structured_operations, list) else 0,
            "tables": len(table_operations) if isinstance(table_operations, list) else 0,
            "blocks": len(block_operations) if isinstance(block_operations, list) else 0,
            "unified": len(unified),
        },
    }
