from copy import deepcopy
from datetime import datetime
import re


def _as_list(value):
    return value if isinstance(value, list) else []


def _stage(name):
    return {
        "name": name,
        "status": "ok",
    }


def _normalize_target_cell(value):
    return re.sub(r"\s+", "", str(value or "").strip().upper())


def _normalize_operations(operations):
    normalized = []
    for operation in _as_list(operations):
        if not isinstance(operation, dict):
            continue
        item = deepcopy(operation)
        item["op_type"] = str(item.get("op_type") or "").strip().lower()
        item["source"] = str(item.get("source") or "").strip().lower()
        item["target_cell"] = _normalize_target_cell(item.get("target_cell"))
        if item["op_type"] == "write_number" and isinstance(item.get("value"), (int, float)):
            item["value"] = item.get("value")
        else:
            item["value"] = "" if item.get("value") is None else str(item.get("value"))
        if item.get("target_cell") and item.get("op_type"):
            normalized.append(item)
    return normalized


def _format_value(operation):
    item = deepcopy(operation)
    if item.get("op_type") == "write_number" and isinstance(item.get("value"), (int, float)):
        return item
    value = str(item.get("value") or "").strip()
    if item.get("op_type") == "write_block":
        lines = [line.strip() for line in re.split(r"\r\n|\r|\n", value)]
        item["value"] = "\n".join(line for line in lines if line)
    else:
        item["value"] = value
    return item


def process_operations_pipeline(unified_operations):
    normalized = _normalize_operations(unified_operations)
    sorted_operations = sorted(
        normalized,
        key=lambda item: (str(item.get("target_cell") or ""), str(item.get("op_type") or "")),
    )
    formatted = [_format_value(operation) for operation in sorted_operations]
    processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finalized = []
    for operation in formatted:
        item = deepcopy(operation)
        item["pipeline_meta"] = {
            "stage": "finalize",
            "processed_at": processed_at,
            "render_ready": True,
        }
        finalized.append(item)

    return {
        "success": True,
        "operations": finalized,
        "stages": [
            _stage("normalize"),
            _stage("sort"),
            _stage("format"),
            _stage("finalize"),
        ],
        "render_ready": True,
    }
