import logging

from app.v4_operations_pipeline import process_operations_pipeline
from app.v4_pipeline_builder import (
    build_block_operations,
    build_structured_operations,
    build_table_operations,
    build_unified_operations,
    count_enabled_mappings,
    detect_mapping_conflicts,
)
from app.v4_render_preview import build_render_preview
from app.v4_validator import validate_order_object


def run_operation_pipeline(order_object, profile=None, template_path=None):
    logger = logging.getLogger(__name__)

    profile = profile if isinstance(profile, dict) else {}
    structured_mapping_file = profile.get("structured_mapping_file") if profile else None
    table_mapping_file = profile.get("table_mapping_file") if profile else None
    block_rules_file = profile.get("block_rules_file") if profile else None

    logger.info(
        "[Pipeline] profile=%s template=%s structured_mapping=%s table_mapping=%s block_rules=%s",
        profile.get("profile_id") if profile else "None",
        template_path or "None",
        structured_mapping_file or "default",
        table_mapping_file or "default",
        block_rules_file or "default",
    )

    validation = validate_order_object(order_object)
    if not validation.get("valid"):
        return {
            "success": False,
            "error": "Validator 校验失败",
            "validation": validation,
            "warnings": validation.get("warnings", []),
            "structured_operations": [],
            "table_operations": [],
            "block_operations": [],
            "unified_operations": [],
            "processed_operations": [],
            "stages": [],
            "render_preview": {},
            "mapping_safety": {
                "has_conflicts": False,
                "conflicts": [],
                "warnings": [],
                "skipped_operations": [],
            },
            "mapping_counts": {
                "enabled_structured_mappings": 0,
                "enabled_table_mappings": 0,
                "enabled_block_rules": 0,
            },
        }

    mapping_counts = count_enabled_mappings(
        structured_mapping_file,
        table_mapping_file,
        block_rules_file,
    )
    structured_result = build_structured_operations(order_object, structured_mapping_file)
    table_result = build_table_operations(order_object, table_mapping_file)
    block_result = build_block_operations(order_object, block_rules_file)

    structured_operations = structured_result.get("operations", [])
    table_operations = table_result.get("operations", [])
    block_operations = block_result.get("operations", [])
    unified_result = build_unified_operations(structured_operations, table_operations, block_operations)
    unified_operations = unified_result.get("operations", [])
    safety_input = list(unified_operations)
    for table_operation in table_operations if isinstance(table_operations, list) else []:
        if isinstance(table_operation, dict) and not table_operation.get("cell_operations"):
            safety_input.append(table_operation)
    mapping_safety = detect_mapping_conflicts(safety_input)
    safe_unified_operations = [
        operation
        for operation in mapping_safety.get("operations", [])
        if isinstance(operation, dict) and operation.get("op_type")
    ]
    pipeline_result = process_operations_pipeline(safe_unified_operations)
    processed_operations = pipeline_result.get("processed_operations", [])
    render_preview = build_render_preview(processed_operations, mapping_safety)

    warnings = []
    warnings.extend(validation.get("warnings", []))
    warnings.extend(structured_result.get("warnings", []))
    warnings.extend(table_result.get("warnings", []))
    warnings.extend(block_result.get("warnings", []))
    warnings.extend(mapping_safety.get("warnings", []))
    warnings.extend(render_preview.get("warnings", []))

    return {
        "success": True,
        "validation": validation,
        "warnings": warnings,
        "structured_operations": structured_operations,
        "table_operations": table_operations,
        "block_operations": block_operations,
        "unified_operations": unified_operations,
        "processed_operations": processed_operations,
        "mapping_safety": mapping_safety,
        "mapping_counts": mapping_counts,
        "stages": pipeline_result.get("stages", []),
        "render_ready": pipeline_result.get("render_ready", False),
        "render_preview": render_preview,
        "counts": {
            "structured": len(structured_operations),
            "tables": len(table_operations),
            "blocks": len(block_operations),
            "unified": len(unified_operations),
            "processed": len(processed_operations),
        },
    }
