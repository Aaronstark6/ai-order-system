from copy import deepcopy


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value):
    return "" if value is None else str(value)


def _base_operation(operation, op_type, source):
    if not isinstance(operation, dict):
        return None

    target_cell = str(operation.get("target_cell") or "").strip()
    if not target_cell:
        return None

    return {
        "op_type": op_type,
        "source": source,
        "target_cell": target_cell,
        "value": _text(operation.get("value")),
    }


def _structured_to_unified(operations):
    unified = []
    for operation in _as_list(operations):
        item = _base_operation(operation, "write_text", "structured")
        if not item:
            continue
        unified.append(item)
    return unified


def _tables_to_unified(operations):
    unified = []
    for operation in _as_list(operations):
        item = _base_operation(operation, "write_table_cell", "table")
        if not item:
            continue
        item["table_name"] = str(operation.get("table_name") or operation.get("table_key") or "").strip()
        unified.append(item)
    return unified


def _blocks_to_unified(operations):
    unified = []
    for operation in _as_list(operations):
        item = _base_operation(operation, "write_block", "block")
        if not item:
            continue
        item["block_name"] = str(operation.get("block_name") or "").strip()
        unified.append(item)
    return unified


def build_unified_operations(structured=None, tables=None, blocks=None):
    structured_operations = _as_list(structured)
    table_operations = _as_list(tables)
    block_operations = _as_list(blocks)

    unified = (
        _structured_to_unified(structured_operations)
        + _tables_to_unified(table_operations)
        + _blocks_to_unified(block_operations)
    )

    skipped_count = (
        len(structured_operations)
        + len(table_operations)
        + len(block_operations)
        - len(unified)
    )
    warnings = []
    if skipped_count:
        warnings.append(f"{skipped_count} 条 operation 缺少 target_cell 或格式无效，已跳过。")

    return {
        "success": True,
        "operations": deepcopy(unified),
        "warnings": warnings,
        "counts": {
            "structured": len(structured_operations),
            "tables": len(table_operations),
            "blocks": len(block_operations),
            "unified": len(unified),
        },
    }
