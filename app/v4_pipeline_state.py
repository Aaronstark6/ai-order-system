from copy import deepcopy
from datetime import datetime


def _default_state():
    return {
        "current_order_object": {},
        "current_template_path": None,
        "current_profile": {},
        "validator": {},
        "operations": {
            "structured": [],
            "tables": [],
            "blocks": [],
            "unified": [],
        },
        "pipeline": {
            "processed_operations": [],
            "stages": [],
        },
        "excel": {
            "generated_file": None,
            "generated_time": None,
        },
        "render_preview": {
            "cell_preview": [],
            "table_preview": [],
            "block_preview": [],
            "generated_time": None,
        },
        "render_targets": {
            "html_preview": "",
            "excel_preview": [],
        },
        "template_analysis": {
            "labels": [],
            "structured_mapping_preview": [],
            "table_regions": [],
            "block_regions": [],
            "summary": {},
        },
    }


_PIPELINE_STATE = _default_state()


def get_pipeline_state():
    return deepcopy(_PIPELINE_STATE)


def reset_pipeline_state():
    global _PIPELINE_STATE
    _PIPELINE_STATE = _default_state()
    return get_pipeline_state()


def load_order_object_into_pipeline(order_object):
    _PIPELINE_STATE["current_order_object"] = deepcopy(order_object) if isinstance(order_object, dict) else {}
    return get_pipeline_state()


def set_current_template(template_path):
    _PIPELINE_STATE["current_template_path"] = str(template_path) if template_path else None
    return get_pipeline_state()


def set_current_profile(profile):
    _PIPELINE_STATE["current_profile"] = deepcopy(profile) if isinstance(profile, dict) else {}
    return get_pipeline_state()


def set_validator_result(result):
    _PIPELINE_STATE["validator"] = deepcopy(result) if isinstance(result, dict) else {}
    return get_pipeline_state()


def set_structured_operations(ops):
    _PIPELINE_STATE["operations"]["structured"] = deepcopy(ops) if isinstance(ops, list) else []
    return get_pipeline_state()


def set_table_operations(ops):
    _PIPELINE_STATE["operations"]["tables"] = deepcopy(ops) if isinstance(ops, list) else []
    return get_pipeline_state()


def set_block_operations(ops):
    _PIPELINE_STATE["operations"]["blocks"] = deepcopy(ops) if isinstance(ops, list) else []
    return get_pipeline_state()


def set_unified_operations(ops):
    _PIPELINE_STATE["operations"]["unified"] = deepcopy(ops) if isinstance(ops, list) else []
    return get_pipeline_state()


def set_excel_result(file_path):
    _PIPELINE_STATE["excel"] = {
        "generated_file": str(file_path) if file_path else None,
        "generated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if file_path else None,
    }
    return get_pipeline_state()


def set_pipeline_result(processed_operations, stages):
    _PIPELINE_STATE["pipeline"] = {
        "processed_operations": deepcopy(processed_operations) if isinstance(processed_operations, list) else [],
        "stages": deepcopy(stages) if isinstance(stages, list) else [],
    }
    _PIPELINE_STATE["render_preview"] = {
        "cell_preview": [],
        "table_preview": [],
        "block_preview": [],
        "generated_time": None,
    }
    _PIPELINE_STATE["render_targets"]["html_preview"] = ""
    return get_pipeline_state()


def set_render_preview(render_preview):
    render_preview = render_preview if isinstance(render_preview, dict) else {}
    _PIPELINE_STATE["render_preview"] = {
        "cell_preview": deepcopy(render_preview.get("cell_preview", []))
        if isinstance(render_preview.get("cell_preview", []), list)
        else [],
        "table_preview": deepcopy(render_preview.get("table_preview", []))
        if isinstance(render_preview.get("table_preview", []), list)
        else [],
        "block_preview": deepcopy(render_preview.get("block_preview", []))
        if isinstance(render_preview.get("block_preview", []), list)
        else [],
        "generated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return get_pipeline_state()


def set_render_targets(targets):
    if not isinstance(targets, dict):
        targets = {}

    _PIPELINE_STATE["render_targets"] = {
        "html_preview": str(targets.get("html_preview") or ""),
        "excel_preview": deepcopy(targets.get("excel_preview")) if isinstance(targets.get("excel_preview"), list) else [],
    }
    return get_pipeline_state()


def set_template_analysis(analysis):
    analysis = analysis if isinstance(analysis, dict) else {}
    _PIPELINE_STATE["template_analysis"] = {
        "labels": deepcopy(analysis.get("labels", [])) if isinstance(analysis.get("labels", []), list) else [],
        "structured_mapping_preview": deepcopy(analysis.get("structured_mapping_preview", []))
        if isinstance(analysis.get("structured_mapping_preview", []), list)
        else [],
        "table_regions": deepcopy(analysis.get("table_regions", []))
        if isinstance(analysis.get("table_regions", []), list)
        else [],
        "block_regions": deepcopy(analysis.get("block_regions", []))
        if isinstance(analysis.get("block_regions", []), list)
        else [],
        "summary": deepcopy(analysis.get("summary", {})) if isinstance(analysis.get("summary", {}), dict) else {},
    }
    return get_pipeline_state()
