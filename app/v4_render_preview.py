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


def _normalize_operation(operation):
    if not isinstance(operation, dict):
        return None
    item = deepcopy(operation)
    item["source"] = str(item.get("source") or "").strip().lower()
    item["op_type"] = str(item.get("op_type") or "").strip().lower()
    item["target_cell"] = str(item.get("target_cell") or "").strip().upper()
    item["value"] = _text(item.get("value"))
    return item


def _table_name(operation):
    return str(operation.get("table_name") or "未命名表格").strip() or "未命名表格"


def build_render_preview(processed_operations):
    warnings = []
    cell_preview = []
    table_groups = {}
    block_preview = []

    for index, operation in enumerate(_as_list(processed_operations), start=1):
        item = _normalize_operation(operation)
        if not item:
            warnings.append(f"第 {index} 条 operation 格式无效，已跳过。")
            continue

        source = item.get("source")
        target_cell = item.get("target_cell")
        value = item.get("value")

        if source == "structured":
            cell_preview.append(
                {
                    "cell": target_cell,
                    "source": source,
                    "op_type": item.get("op_type"),
                    "value": value,
                }
            )
            continue

        if source == "table":
            column, row_number = _parse_cell(target_cell)
            if not column or row_number is None:
                warnings.append(f"第 {index} 条 table operation 缺少有效 target_cell，已跳过。")
                continue
            table = table_groups.setdefault(_table_name(item), {})
            row = table.setdefault(row_number, {})
            row[column] = value
            continue

        if source == "block":
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

    return {
        "success": True,
        "cell_preview": cell_preview,
        "table_preview": table_preview,
        "block_preview": block_preview,
        "warnings": warnings,
    }
