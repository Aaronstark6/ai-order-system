import logging
from copy import deepcopy

from app.v4_operations_pipeline import process_operations_pipeline
from app.v4_pipeline_builder import (
    build_block_operations,
    build_block_runtime_operations,
    build_structured_operations,
    build_table_operations,
    build_table_runtime_operations,
    build_unified_operations,
    count_enabled_mappings,
    detect_mapping_conflicts,
    resolve_field_key_value,
)
from app.v4_render_preview import build_render_preview
from app.v4_validator import validate_order_object


def run_operation_pipeline(order_object, profile=None, template_path=None, export_operations=None):
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
            "operations": [],
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
    use_export_source = isinstance(export_operations, list) and len(export_operations) > 0
    if use_export_source:
        logger.info("V4 structured builder skipped: export_operations source active")
        structured_result = {
            "success": True,
            "operations": [],
            "count": 0,
            "skipped": True,
            "reason": "export_operations source active",
        }
        structured_operations = []
    else:
        structured_result = build_structured_operations(order_object, structured_mapping_file)
        structured_operations = structured_result.get("operations", [])

    if use_export_source:
        logger.info("V4 table builder skipped: export_operations source active")
        table_result = {
            "success": True,
            "operations": [],
            "count": 0,
            "skipped": True,
            "reason": "export_operations source active",
        }
        table_operations = []
        logger.info("V4 block builder skipped: export_operations source active")
        block_result = {
            "success": True,
            "operations": [],
            "count": 0,
            "skipped": True,
            "reason": "export_operations source active",
        }
        block_operations = []
    else:
        table_result = build_table_operations(order_object, table_mapping_file)
        block_result = build_block_operations(order_object, block_rules_file)
        table_operations = table_result.get("operations", [])
        block_operations = block_result.get("operations", [])

    if use_export_source:
        logger.info("V4 runtime source: export_operations")
        bound_export_operations = []
        runtime_table_operations = []
        for operation in export_operations:
            bound_operation = deepcopy(operation)
            if isinstance(bound_operation, dict):
                operation_type = str(
                    bound_operation.get("op_type") or bound_operation.get("operation") or ""
                ).strip()
                if operation_type == "write_table_cell":
                    metadata = bound_operation.get("metadata", {})
                    metadata = metadata if isinstance(metadata, dict) else {}
                    table_logic = metadata.get("table_logic", {})
                    table_logic = table_logic if isinstance(table_logic, dict) else {}
                    rows = table_logic.get("rows", [])
                    columns = table_logic.get("columns", [])
                    start_cell = table_logic.get("start_cell") or bound_operation.get("target_cell")
                    table_name = table_logic.get("table_name") or bound_operation.get("label") or ""
                    table_key = (
                        table_logic.get("table_key")
                        or bound_operation.get("field_key")
                        or bound_operation.get("source_node_id")
                        or ""
                    )

                    if isinstance(rows, list) and rows and isinstance(columns, list) and columns:
                        table_runtime_result = build_table_runtime_operations(
                            table_name=table_name,
                            table_key=table_key,
                            rows=rows,
                            columns=columns,
                            start_cell=start_cell,
                            mapping_confirmed=True,
                        )
                        runtime_table_operations.append(table_runtime_result)
                        continue

                if operation_type == "write_block":
                    metadata = bound_operation.get("metadata", {})
                    metadata = metadata if isinstance(metadata, dict) else {}
                    block_logic = metadata.get("block_logic", {})
                    block_logic = block_logic if isinstance(block_logic, dict) else {}
                    lines = block_logic.get("lines", [])
                    target_cell = block_logic.get("target_cell") or bound_operation.get("target_cell")
                    block_name = block_logic.get("block_name") or bound_operation.get("label") or ""
                    block_key = (
                        block_logic.get("block_key")
                        or bound_operation.get("field_key")
                        or bound_operation.get("source_node_id")
                        or ""
                    )
                    block_operation = (
                        block_logic.get("operation")
                        or bound_operation.get("op_type")
                        or bound_operation.get("operation")
                        or "write_block"
                    )

                    if isinstance(lines, list) and lines and str(target_cell or "").strip():
                        block_runtime_result = build_block_runtime_operations(
                            block_name=block_name,
                            block_key=block_key,
                            lines=lines,
                            target_cell=target_cell,
                            operation=block_operation,
                            mapping_confirmed=True,
                        )
                        block_runtime_result["op_type"] = "write_block"
                        block_runtime_result["source"] = "block"
                        block_runtime_result["type"] = "block"
                        bound_export_operations.append(block_runtime_result)
                        continue

                field_key = bound_operation.get("field_key")
                if not str(field_key or "").strip():
                    field_key = bound_operation.get("value_source")

                resolved_value = resolve_field_key_value(order_object, field_key)
                if resolved_value not in (None, ""):
                    bound_operation["value"] = resolved_value
            bound_export_operations.append(bound_operation)

        for table_op in runtime_table_operations:
            if not isinstance(table_op, dict):
                continue
            for cell_op in table_op.get("cell_operations", []):
                if not isinstance(cell_op, dict):
                    continue
                bound_cell_operation = deepcopy(cell_op)
                bound_cell_operation["op_type"] = "write_table_cell"
                bound_cell_operation["source"] = "table"
                bound_cell_operation["type"] = "table"
                bound_cell_operation["table_key"] = str(table_op.get("table_key") or "")
                bound_cell_operation["table_name"] = str(table_op.get("table_name") or "")
                bound_cell_operation["mapping_confirmed"] = bool(
                    table_op.get("mapping_confirmed") or bound_cell_operation.get("mapping_confirmed")
                )
                bound_export_operations.append(bound_cell_operation)

        unified_result = build_unified_operations(
            [],
            [],
            [],
            export_operations=bound_export_operations,
        )
    else:
        logger.info("V4 runtime source: legacy")
        unified_result = build_unified_operations(
            structured_operations,
            table_operations,
            block_operations,
        )
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
    operations = pipeline_result.get("operations", [])
    render_preview = build_render_preview(operations, mapping_safety)

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
        "operations": operations,
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
            "processed": len(operations),
        },
    }
