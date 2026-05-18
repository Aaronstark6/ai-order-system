from copy import deepcopy
from datetime import datetime
import re


PIPELINE_STAGE_NAMES = ["normalize", "sort", "format", "finalize"]


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value):
    return "" if value is None else str(value)


def _normalize_target_cell(value):
    text = str(value or "").strip().upper()
    return re.sub(r"\s+", "", text)


def _stage_record(stage, input_count, output_count):
    return {
        "stage": stage,
        "input_count": input_count,
        "output_count": output_count,
        "processed_count": output_count,
        "render_ready": stage == "finalize",
    }


def _normalize_operations(operations):
    normalized = []
    for operation in _as_list(operations):
        if not isinstance(operation, dict):
            continue

        op_type = str(operation.get("op_type") or operation.get("operation") or "").strip().lower()
        target_cell = _normalize_target_cell(operation.get("target_cell"))
        if not op_type or not target_cell:
            continue

        item = deepcopy(operation)
        item["op_type"] = op_type
        item["source"] = str(item.get("source") or "").strip().lower()
        item["target_cell"] = target_cell
        item["value"] = _text(item.get("value"))

        if "table_name" in item:
            item["table_name"] = str(item.get("table_name") or "").strip()
        if "block_name" in item:
            item["block_name"] = str(item.get("block_name") or "").strip()

        normalized.append(item)
    return normalized


def _sort_operations(operations):
    return sorted(
        operations,
        key=lambda operation: (
            str(operation.get("target_cell") or ""),
            str(operation.get("op_type") or ""),
        ),
    )


def _format_table_value(value):
    text = _text(value).strip()
    percent_match = re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%", text)
    if percent_match:
        number = percent_match.group(1).rstrip("0").rstrip(".")
        return f"{number}%"
    return text


def _format_operations(operations):
    formatted = []
    for operation in operations:
        item = deepcopy(operation)
        value = _text(item.get("value")).strip()
        op_type = str(item.get("op_type") or "").strip()
        source = str(item.get("source") or "").strip()

        if op_type == "write_block" or source == "block":
            lines = [line.strip() for line in re.split(r"\r\n|\r|\n", value)]
            item["value"] = "\n".join(line for line in lines if line)
        elif op_type == "write_table_cell" or source == "table":
            item["value"] = _format_table_value(value)
        else:
            item["value"] = value

        formatted.append(item)
    return formatted


def _finalize_operations(operations):
    processed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    finalized = []
    for operation in operations:
        item = deepcopy(operation)
        item["pipeline_meta"] = {
            "pipeline_stage": "finalized",
            "processed_at": processed_at,
            "render_ready": True,
        }
        finalized.append(item)
    return finalized


def process_operations_pipeline(unified_operations):
    raw_operations = deepcopy(_as_list(unified_operations))
    stages = []

    normalized = _normalize_operations(raw_operations)
    stages.append(_stage_record("normalize", len(raw_operations), len(normalized)))

    sorted_operations = _sort_operations(normalized)
    stages.append(_stage_record("sort", len(normalized), len(sorted_operations)))

    formatted = _format_operations(sorted_operations)
    stages.append(_stage_record("format", len(sorted_operations), len(formatted)))

    finalized = _finalize_operations(formatted)
    stages.append(_stage_record("finalize", len(formatted), len(finalized)))

    return {
        "success": True,
        "raw_operations": raw_operations,
        "processed_operations": finalized,
        "stages": stages,
        "pipeline_meta": {
            "pipeline_stage": "finalized",
            "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "render_ready": True,
        },
    }
