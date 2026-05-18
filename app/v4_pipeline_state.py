from copy import deepcopy
from datetime import datetime
from threading import Lock

from app.v4_schema_version import get_current_schema_version, validate_schema_version


def _default_state():
    schema_result = validate_schema_version()
    return {
        "current_order_object": None,
        "current_template_path": None,
        "validator": {
            "status": "idle",
            "errors": [],
            "warnings": [],
        },
        "operations": {
            "structured": [],
            "tables": [],
            "blocks": [],
            "unified": [],
        },
        "excel": {
            "generated_file": None,
            "generated_time": None,
        },
        "template_profile": {
            "profile_id": "",
            "profile_name": "",
            "schema_version": "",
            "structured_mapping_file": "",
            "table_mapping_file": "",
            "block_rules_file": "",
            "render_config": {},
        },
        "render_targets": {
            "html_preview": None,
        },
        "render_preview": {
            "cell_preview": [],
            "table_preview": [],
            "block_preview": [],
            "warnings": [],
            "generated_time": None,
        },
        "pipeline": {
            "raw_operations": [],
            "processed_operations": [],
            "stages": [],
        },
        "schema": {
            "current_version": get_current_schema_version(),
            "order_object_version": schema_result.get("order_object_version"),
            "compatible": schema_result.get("compatible", True),
            "status": schema_result.get("status", "warning"),
            "message": schema_result.get("message", ""),
        },
    }


_LOCK = Lock()
_STATE = _default_state()


def get_pipeline_state():
    with _LOCK:
        return deepcopy(_STATE)


def reset_pipeline_state():
    global _STATE
    with _LOCK:
        _STATE = _default_state()
        return deepcopy(_STATE)


def set_current_order_object(order_object):
    schema_result = validate_schema_version(order_object=order_object)
    with _LOCK:
        _STATE["current_order_object"] = deepcopy(order_object)
        _STATE["schema"] = {
            "current_version": get_current_schema_version(),
            "order_object_version": schema_result.get("order_object_version"),
            "compatible": schema_result.get("compatible", True),
            "status": schema_result.get("status", "warning"),
            "message": schema_result.get("message", ""),
        }
        return deepcopy(_STATE)


def set_schema_status(order_object=None, mappings=None, pipeline_state=None):
    schema_result = validate_schema_version(
        order_object=order_object,
        mappings=mappings,
        pipeline_state=pipeline_state,
    )
    with _LOCK:
        _STATE["schema"] = {
            "current_version": get_current_schema_version(),
            "order_object_version": schema_result.get("order_object_version"),
            "compatible": schema_result.get("compatible", True),
            "status": schema_result.get("status", "warning"),
            "message": schema_result.get("message", ""),
        }
        return deepcopy(_STATE)


def set_current_template_path(template_path):
    with _LOCK:
        _STATE["current_template_path"] = str(template_path) if template_path else None
        return deepcopy(_STATE)


def set_validator_result(validation_result):
    validation_result = validation_result if isinstance(validation_result, dict) else {}
    errors = validation_result.get("errors", [])
    warnings = validation_result.get("warnings", [])
    if not isinstance(errors, list):
        errors = []
    if not isinstance(warnings, list):
        warnings = []

    with _LOCK:
        _STATE["validator"] = {
            "status": "passed" if validation_result.get("valid") else "failed",
            "errors": deepcopy(errors),
            "warnings": deepcopy(warnings),
        }
        return deepcopy(_STATE)


def set_operations(kind, operations):
    if kind not in {"structured", "tables", "blocks", "unified"}:
        raise ValueError(f"Unknown pipeline operations kind: {kind}")
    if not isinstance(operations, list):
        operations = []

    with _LOCK:
        _STATE["operations"][kind] = deepcopy(operations)
        return deepcopy(_STATE)


def set_excel_result(generated_file, generated_time=None):
    with _LOCK:
        _STATE["excel"] = {
            "generated_file": str(generated_file) if generated_file else None,
            "generated_time": generated_time or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return deepcopy(_STATE)


def set_html_preview(html):
    with _LOCK:
        _STATE["render_targets"]["html_preview"] = str(html) if html is not None else None
        return deepcopy(_STATE)


def set_render_preview(preview):
    preview = preview if isinstance(preview, dict) else {}
    with _LOCK:
        _STATE["render_preview"] = {
            "cell_preview": deepcopy(preview.get("cell_preview", []))
            if isinstance(preview.get("cell_preview", []), list)
            else [],
            "table_preview": deepcopy(preview.get("table_preview", []))
            if isinstance(preview.get("table_preview", []), list)
            else [],
            "block_preview": deepcopy(preview.get("block_preview", []))
            if isinstance(preview.get("block_preview", []), list)
            else [],
            "warnings": deepcopy(preview.get("warnings", []))
            if isinstance(preview.get("warnings", []), list)
            else [],
            "generated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return deepcopy(_STATE)


def set_operations_pipeline(raw_operations, processed_operations, stages):
    if not isinstance(raw_operations, list):
        raw_operations = []
    if not isinstance(processed_operations, list):
        processed_operations = []
    if not isinstance(stages, list):
        stages = []

    with _LOCK:
        _STATE["pipeline"] = {
            "raw_operations": deepcopy(raw_operations),
            "processed_operations": deepcopy(processed_operations),
            "stages": deepcopy(stages),
        }
        return deepcopy(_STATE)
