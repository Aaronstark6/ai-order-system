from copy import deepcopy
import re


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value):
    return "" if value is None else str(value)


def _parse_cell(cell_ref):
    match = re.fullmatch(r"\s*([A-Za-z]+)\s*(\d+)\s*", str(cell_ref or ""))
    if not match:
        return "", None
    return match.group(1).upper(), int(match.group(2))


def _normalized_operation(operation):
    if not isinstance(operation, dict):
        return None
    item = deepcopy(operation)
    item["op_type"] = str(item.get("op_type") or item.get("operation") or "").strip().lower()
    item["source"] = str(item.get("source") or "").strip().lower()
    item["target_cell"] = str(item.get("target_cell") or "").strip().upper()
    item["value"] = _text(item.get("value"))
    return item


def _table_name(operation):
    return str(operation.get("table_name") or operation.get("table_key") or "未命名表格").strip() or "未命名表格"


def _row_number(operation):
    explicit = operation.get("row_number")
    if explicit is not None:
        try:
            return int(explicit)
        except (TypeError, ValueError):
            pass
    _, row_number = _parse_cell(operation.get("target_cell"))
    return row_number


def build_render_preview(operations):
    operation_list = _as_list(operations)
    warnings = []
    cell_preview = []
    table_groups = {}
    block_preview = []

    if not operation_list:
        return {
            "success": False,
            "error": "暂无 operations，无法生成预览",
            "cell_preview": [],
            "table_preview": [],
            "block_preview": [],
            "warnings": ["暂无 operations，无法生成预览"],
        }

    for index, operation in enumerate(operation_list, start=1):
        item = _normalized_operation(operation)
        if not item:
            warnings.append(f"第 {index} 条 operation 格式无效，已跳过。")
            continue

        op_type = item.get("op_type")
        source = item.get("source")
        target_cell = item.get("target_cell")
        value = item.get("value")

        if op_type == "write_text" and source == "structured":
            cell_preview.append(
                {
                    "cell": target_cell,
                    "value": value,
                    "op_type": op_type,
                    "source": source,
                }
            )
            continue

        if op_type == "write_table_cell" and source == "table":
            column, parsed_row_number = _parse_cell(target_cell)
            row_number = _row_number(item) or parsed_row_number
            if not column or row_number is None:
                warnings.append(f"第 {index} 条 table operation 缺少有效 target_cell，已跳过。")
                continue

            name = _table_name(item)
            table = table_groups.setdefault(name, {})
            row = table.setdefault(row_number, {})
            row[column] = value
            continue

        if op_type == "write_block" and source == "block":
            block_preview.append(
                {
                    "block_name": str(item.get("block_name") or "未命名区块").strip() or "未命名区块",
                    "target_cell": target_cell,
                    "value": value,
                }
            )
            continue

    table_preview = []
    for table_name in sorted(table_groups):
        rows = []
        for row_number in sorted(table_groups[table_name]):
            rows.append(
                {
                    "row_number": row_number,
                    "cells": dict(sorted(table_groups[table_name][row_number].items())),
                }
            )
        table_preview.append(
            {
                "table_name": table_name,
                "rows": rows,
            }
        )

    if not cell_preview and not table_preview and not block_preview:
        warnings.append("没有可预览内容")

    return {
        "success": True,
        "cell_preview": cell_preview,
        "table_preview": table_preview,
        "block_preview": block_preview,
        "warnings": warnings,
    }
