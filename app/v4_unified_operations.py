from copy import deepcopy


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value):
    return "" if value is None else str(value)


def build_unified_operations(structured_ops, table_ops, block_ops):
    unified = []

    for operation in _as_list(structured_ops):
        if not isinstance(operation, dict):
            continue
        unified.append(
            {
                "op_type": "write_text",
                "source": "structured",
                "target_cell": str(operation.get("target_cell") or "").strip(),
                "value": _text(operation.get("value")),
            }
        )

    for operation in _as_list(table_ops):
        if not isinstance(operation, dict):
            continue
        unified.append(
            {
                "op_type": "write_table_cell",
                "source": "table",
                "table_name": str(operation.get("table_name") or "").strip(),
                "target_cell": str(operation.get("target_cell") or "").strip(),
                "value": _text(operation.get("value")),
            }
        )

    for operation in _as_list(block_ops):
        if not isinstance(operation, dict):
            continue
        unified.append(
            {
                "op_type": "write_block",
                "source": "block",
                "block_name": str(operation.get("block_name") or "").strip(),
                "target_cell": str(operation.get("target_cell") or "").strip(),
                "value": _text(operation.get("value")),
            }
        )

    return {
        "success": True,
        "operations": deepcopy(unified),
        "counts": {
            "structured": len(_as_list(structured_ops)),
            "tables": len(_as_list(table_ops)),
            "blocks": len(_as_list(block_ops)),
            "unified": len(unified),
        },
    }
