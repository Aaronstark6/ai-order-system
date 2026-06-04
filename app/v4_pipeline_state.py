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
            "structured_operations": [],
            "table_operations": [],
            "block_operations": [],
            "unified_operations": [],
        },
        "pipeline": {
            "operations": [],
            "stages": [],
        },
        "mapping_safety": {
            "has_conflicts": False,
            "conflicts": [],
            "warnings": [],
            "skipped_operations": [],
            "overwrite_warnings": [],
        },
        "mapping_counts": {
            "enabled_structured_mappings": 0,
            "enabled_table_mappings": 0,
            "enabled_block_rules": 0,
        },
        "excel": {
            "generated_file": None,
            "generated_time": None,
        },
        "render_preview": {
            "cells": [],
            "cell_preview": [],
            "table_preview": [],
            "block_preview": [],
            "skipped_preview": [],
            "mapping_safety": {},
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
            "template_structure": {
                "regions": [],
                "raw_regions": [],
                "deduped_regions": [],
                "recommended_regions": [],
                "tables": [],
                "blocks": [],
                "labels": [],
            },
            "auto_mapping_preview": {
                "structured": [],
                "tables": [],
                "blocks": [],
                "needs_review": [],
                "rejected_candidates": [],
            },
            "summary": {},
        },
        "template_learning": {
            "last_run_time": None,
            "success": False,
            "summary": {},
            "needs_review": [],
            "rejected_candidates": [],
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
    value = deepcopy(ops) if isinstance(ops, list) else []
    _PIPELINE_STATE["operations"]["structured"] = value
    _PIPELINE_STATE["operations"]["structured_operations"] = deepcopy(value)
    return get_pipeline_state()


def set_table_operations(ops):
    value = deepcopy(ops) if isinstance(ops, list) else []
    _PIPELINE_STATE["operations"]["tables"] = value
    _PIPELINE_STATE["operations"]["table_operations"] = deepcopy(value)
    return get_pipeline_state()


def set_block_operations(ops):
    value = deepcopy(ops) if isinstance(ops, list) else []
    _PIPELINE_STATE["operations"]["blocks"] = value
    _PIPELINE_STATE["operations"]["block_operations"] = deepcopy(value)
    return get_pipeline_state()


def set_unified_operations(ops):
    value = deepcopy(ops) if isinstance(ops, list) else []
    _PIPELINE_STATE["operations"]["unified"] = value
    _PIPELINE_STATE["operations"]["unified_operations"] = deepcopy(value)
    return get_pipeline_state()


def set_excel_result(file_path):
    _PIPELINE_STATE["excel"] = {
        "generated_file": str(file_path) if file_path else None,
        "generated_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S") if file_path else None,
    }
    return get_pipeline_state()


def set_pipeline_result(operations, stages):
    _PIPELINE_STATE["pipeline"] = {
        "operations": deepcopy(operations) if isinstance(operations, list) else [],
        "stages": deepcopy(stages) if isinstance(stages, list) else [],
    }
    _PIPELINE_STATE["render_preview"] = {
        "cells": [],
        "cell_preview": [],
        "table_preview": [],
        "block_preview": [],
        "skipped_preview": [],
        "mapping_safety": {},
        "generated_time": None,
    }
    _PIPELINE_STATE["render_targets"]["html_preview"] = ""
    return get_pipeline_state()


def set_mapping_safety(mapping_safety):
    mapping_safety = mapping_safety if isinstance(mapping_safety, dict) else {}
    _PIPELINE_STATE["mapping_safety"] = {
        "has_conflicts": bool(mapping_safety.get("has_conflicts")),
        "conflicts": deepcopy(mapping_safety.get("conflicts", []))
        if isinstance(mapping_safety.get("conflicts", []), list)
        else [],
        "warnings": deepcopy(mapping_safety.get("warnings", []))
        if isinstance(mapping_safety.get("warnings", []), list)
        else [],
        "skipped_operations": deepcopy(mapping_safety.get("skipped_operations", []))
        if isinstance(mapping_safety.get("skipped_operations", []), list)
        else [],
        "overwrite_warnings": deepcopy(mapping_safety.get("overwrite_warnings", []))
        if isinstance(mapping_safety.get("overwrite_warnings", []), list)
        else [],
    }
    return get_pipeline_state()


def merge_mapping_safety(mapping_safety):
    current = deepcopy(_PIPELINE_STATE.get("mapping_safety", {}))
    incoming = mapping_safety if isinstance(mapping_safety, dict) else {}
    conflicts = current.get("conflicts", []) if isinstance(current.get("conflicts"), list) else []
    warnings = current.get("warnings", []) if isinstance(current.get("warnings"), list) else []
    skipped = current.get("skipped_operations", []) if isinstance(current.get("skipped_operations"), list) else []
    overwrite = current.get("overwrite_warnings", []) if isinstance(current.get("overwrite_warnings"), list) else []

    conflicts.extend(incoming.get("conflicts", []) if isinstance(incoming.get("conflicts"), list) else [])
    warnings.extend(incoming.get("warnings", []) if isinstance(incoming.get("warnings"), list) else [])
    skipped.extend(incoming.get("skipped_operations", []) if isinstance(incoming.get("skipped_operations"), list) else [])
    overwrite.extend(incoming.get("overwrite_warnings", []) if isinstance(incoming.get("overwrite_warnings"), list) else [])

    return set_mapping_safety(
        {
            "has_conflicts": bool(current.get("has_conflicts") or incoming.get("has_conflicts") or conflicts),
            "conflicts": conflicts,
            "warnings": warnings,
            "skipped_operations": skipped,
            "overwrite_warnings": overwrite,
        }
    )


def set_mapping_counts(mapping_counts):
    mapping_counts = mapping_counts if isinstance(mapping_counts, dict) else {}
    _PIPELINE_STATE["mapping_counts"] = {
        "enabled_structured_mappings": int(mapping_counts.get("enabled_structured_mappings") or 0),
        "enabled_table_mappings": int(mapping_counts.get("enabled_table_mappings") or 0),
        "enabled_block_rules": int(mapping_counts.get("enabled_block_rules") or 0),
    }
    return get_pipeline_state()


def set_render_preview(render_preview):
    render_preview = render_preview if isinstance(render_preview, dict) else {}
    _PIPELINE_STATE["render_preview"] = {
        "cells": deepcopy(render_preview.get("cells", []))
        if isinstance(render_preview.get("cells", []), list)
        else [],
        "cell_preview": deepcopy(render_preview.get("cell_preview", []))
        if isinstance(render_preview.get("cell_preview", []), list)
        else [],
        "table_preview": deepcopy(render_preview.get("table_preview", []))
        if isinstance(render_preview.get("table_preview", []), list)
        else [],
        "block_preview": deepcopy(render_preview.get("block_preview", []))
        if isinstance(render_preview.get("block_preview", []), list)
        else [],
        "skipped_preview": deepcopy(render_preview.get("skipped_preview", []))
        if isinstance(render_preview.get("skipped_preview", []), list)
        else [],
        "mapping_safety": deepcopy(render_preview.get("mapping_safety", {}))
        if isinstance(render_preview.get("mapping_safety", {}), dict)
        else {},
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
        "template_structure": deepcopy(analysis.get("template_structure", {}))
        if isinstance(analysis.get("template_structure", {}), dict)
        else {
            "regions": [],
            "raw_regions": [],
            "deduped_regions": [],
            "recommended_regions": [],
            "tables": [],
            "blocks": [],
            "labels": [],
        },
        "auto_mapping_preview": deepcopy(analysis.get("auto_mapping_preview", {}))
        if isinstance(analysis.get("auto_mapping_preview", {}), dict)
        else {
            "structured": [],
            "tables": [],
            "blocks": [],
            "needs_review": [],
            "rejected_candidates": [],
        },
        "semantic_regions": deepcopy(analysis.get("semantic_regions", []))
        if isinstance(analysis.get("semantic_regions", []), list)
        else [],
        "semantic_summary": deepcopy(analysis.get("semantic_summary", {}))
        if isinstance(analysis.get("semantic_summary", {}), dict)
        else {},
        "summary": deepcopy(analysis.get("summary", {})) if isinstance(analysis.get("summary", {}), dict) else {},
    }
    return get_pipeline_state()


def set_template_learning(result):
    result = result if isinstance(result, dict) else {}
    _PIPELINE_STATE["template_learning"] = {
        "last_run_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success": bool(result.get("success")),
        "summary": deepcopy(result.get("summary", {})) if isinstance(result.get("summary", {}), dict) else {},
        "needs_review": deepcopy(result.get("needs_review", []))
        if isinstance(result.get("needs_review", []), list)
        else [],
        "rejected_candidates": deepcopy(result.get("rejected_candidates", []))
        if isinstance(result.get("rejected_candidates", []), list)
        else [],
    }
    return get_pipeline_state()
