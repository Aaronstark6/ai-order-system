"""
Build an ExportPlan from a V4 Document Intelligence Model.

This module only converts in-memory document intelligence data into a
normalized export strategy. It does not write Excel, call executors, or
connect to routes, Pipeline, static pages, Word/PDF, or existing export APIs.
"""

from app.v4_document_intelligence import (
    LINK_TYPE_USES_POLICY,
    LINK_TYPE_WRITES_TO,
    NODE_TYPE_CHOICE_GROUP,
    NODE_TYPE_FIELD,
    NODE_TYPE_OBJECT,
    NODE_TYPE_RUNTIME_POLICY,
    NODE_TYPE_TABLE,
    collect_all_nodes,
    normalize_dict,
    normalize_list,
    normalize_text,
)


SUPPORTED_EXPORT_OP_TYPES = {
    "write_text",
    "write_number",
    "write_multiline",
    "write_table_cell",
    "write_block",
    "write_image",
    "check_option",
    "select_option_text",
}

DEFAULT_OP_TYPE = "write_text"


def _empty_export_plan():
    return {
        "operations": [],
        "warnings": [],
    }


def _node_id(node):
    if isinstance(node, dict):
        return normalize_text(node.get("node_id"))
    return ""


def _node_type(node):
    if isinstance(node, dict):
        return normalize_text(node.get("node_type"))
    return ""


def _metadata_extra(node):
    if not isinstance(node, dict):
        return {}

    metadata = normalize_dict(node.get("metadata"))
    extra = metadata.get("extra")
    if isinstance(extra, dict):
        return normalize_dict(extra)
    return {}


def _semantic_summary(node):
    if not isinstance(node, dict):
        return {}

    summary = node.get("semantic_summary")
    if isinstance(summary, dict):
        return normalize_dict(summary)
    return {}


def _visual_metadata(node):
    if not isinstance(node, dict):
        return {}

    visual = node.get("visual_metadata")
    if isinstance(visual, dict):
        return normalize_dict(visual)

    return {}


def _condition_metadata(node):
    if not isinstance(node, dict):
        return {}

    metadata = node.get("condition_metadata")

    if isinstance(metadata, dict):
        return normalize_dict(metadata)

    return {}


def _visual_logic(node):
    if not isinstance(node, dict):
        return {}

    visual_logic = node.get("visual_logic")
    if isinstance(visual_logic, dict):
        return visual_logic
    return {}


def _visual_coordinates(node):
    visual_logic = _visual_logic(node)
    coordinates = visual_logic.get("coordinates")
    if isinstance(coordinates, dict):
        return coordinates

    visual_metadata = node.get("visual_metadata")
    if isinstance(visual_metadata, dict):
        return {
            "source_cell": visual_metadata.get("source_cell", ""),
            "target_cell": visual_metadata.get("target_cell", ""),
            "row": visual_metadata.get("row"),
            "col": visual_metadata.get("col"),
            "page": visual_metadata.get("page"),
            "bbox": visual_metadata.get("bbox", {}),
        }

    return {
        "source_cell": "",
        "target_cell": "",
        "row": None,
        "col": None,
        "page": None,
        "bbox": {},
    }


def _condition_logic(node):
    if not isinstance(node, dict):
        return {}

    condition_logic = node.get("condition_logic")
    if isinstance(condition_logic, dict):
        return condition_logic
    return {}


def _choice_logic(node):
    if not isinstance(node, dict):
        return {}

    choice_logic = node.get("choice_logic")
    if isinstance(choice_logic, dict):
        return choice_logic
    return {}


def _table_logic(node):
    if not isinstance(node, dict):
        return {}

    table_logic = node.get("table_logic")
    if isinstance(table_logic, dict):
        return table_logic
    return {}


def _links(model):
    if not isinstance(model, dict):
        return []

    links = model.get("links")
    if not isinstance(links, list):
        return []
    return [link for link in links if isinstance(link, dict)]


def _nodes_by_id(model):
    nodes_by_id = {}
    for node in collect_all_nodes(model):
        node_id = _node_id(node)
        if node_id and node_id not in nodes_by_id:
            nodes_by_id[node_id] = node
    return nodes_by_id


def _find_linked_node(model, from_node_id, link_type, target_node_type=""):
    from_node_id = normalize_text(from_node_id)
    link_type = normalize_text(link_type)
    target_node_type = normalize_text(target_node_type)
    if not from_node_id or not link_type:
        return {}

    nodes_by_id = _nodes_by_id(model)
    for link in _links(model):
        if normalize_text(link.get("from_node_id")) != from_node_id:
            continue
        if normalize_text(link.get("link_type")) != link_type:
            continue

        node = nodes_by_id.get(normalize_text(link.get("to_node_id")), {})
        if not isinstance(node, dict):
            continue
        if target_node_type and _node_type(node) != target_node_type:
            continue
        return node
    return {}


def _target_cell_from_writes_to_link(model, node):
    node_id = _node_id(node)
    if not node_id:
        return ""

    for link in _links(model):
        if normalize_text(link.get("link_type")) != LINK_TYPE_WRITES_TO:
            continue
        if normalize_text(link.get("from_node_id")) != node_id:
            continue

        metadata = normalize_dict(link.get("metadata"))
        target_cell = normalize_text(metadata.get("target_cell"))
        if target_cell:
            return target_cell

        to_node_id = normalize_text(link.get("to_node_id"))
        if to_node_id.startswith("cell."):
            return to_node_id[len("cell.") :]
    return ""


def resolve_runtime_policy_for_node(model, node):
    return _find_linked_node(
        model, _node_id(node), LINK_TYPE_USES_POLICY, NODE_TYPE_RUNTIME_POLICY
    )


def resolve_target_cell_for_node(model, node):
    target_cell = _target_cell_from_writes_to_link(model, node)
    if target_cell:
        return target_cell

    coordinates = _visual_coordinates(node)
    target_cell = normalize_text(coordinates.get("target_cell"))
    if target_cell:
        return target_cell

    metadata = normalize_dict(node.get("metadata")) if isinstance(node, dict) else {}
    raw = metadata.get("raw")
    if isinstance(raw, dict):
        return normalize_text(raw.get("target_cell"))
    return ""


def resolve_write_mode_for_node(model, node):
    runtime_policy = resolve_runtime_policy_for_node(model, node)
    if isinstance(runtime_policy, dict) and runtime_policy:
        action = normalize_text(runtime_policy.get("action"))
        if action:
            return action

        policy_type = normalize_text(runtime_policy.get("policy_type"))
        if policy_type:
            return policy_type

    extra = _metadata_extra(node)
    summary = _semantic_summary(node)
    write_mode = normalize_text(summary.get("write_mode")) or normalize_text(extra.get("write_mode"))
    if write_mode:
        return write_mode

    node_type = _node_type(node)
    if node_type == NODE_TYPE_TABLE:
        return "write_table_cell"
    if node_type == NODE_TYPE_OBJECT:
        return "write_image"
    return DEFAULT_OP_TYPE


def normalize_export_op_type(write_mode, node_type=""):
    write_mode = normalize_text(write_mode)
    node_type = normalize_text(node_type)
    if write_mode in SUPPORTED_EXPORT_OP_TYPES:
        return write_mode

    op_type_map = {
        "write_right_cell": "write_text",
        "write_below_cell": "write_multiline",
        "append_after_colon": "write_multiline",
        "image_attachment_area": "write_image",
        "table_region": "write_table_cell",
    }
    if write_mode in op_type_map:
        return op_type_map[write_mode]

    if node_type == NODE_TYPE_TABLE:
        return "write_table_cell"
    if node_type == NODE_TYPE_OBJECT:
        return "write_image"
    return DEFAULT_OP_TYPE


def append_warning(plan, code, message, node_id="", field_key=""):
    if not isinstance(plan, dict):
        return plan

    if not isinstance(plan.get("warnings"), list):
        plan["warnings"] = []
    plan["warnings"].append(
        {
            "code": normalize_text(code),
            "message": normalize_text(message),
            "node_id": normalize_text(node_id),
            "field_key": normalize_text(field_key),
        }
    )
    return plan


def build_export_operation_from_node(model, node):
    if not isinstance(node, dict):
        return {}

    node_type = _node_type(node)
    if node_type not in {
        NODE_TYPE_FIELD,
        NODE_TYPE_TABLE,
        NODE_TYPE_CHOICE_GROUP,
        NODE_TYPE_OBJECT,
    }:
        return {}

    node_id = _node_id(node)
    field_key = normalize_text(node.get("field_key")) or node_id
    label = normalize_text(node.get("label")) or field_key
    write_mode = resolve_write_mode_for_node(model, node)
    op_type = normalize_export_op_type(write_mode, node_type)
    target_cell = resolve_target_cell_for_node(model, node)
    if op_type == "write_table_cell":
        runtime_source = "table"
    elif op_type == "write_block":
        runtime_source = "block"
    else:
        runtime_source = "structured"

    runtime_value = (
        node.get("value")
        if node.get("value") is not None
        else node.get("default_value")
        if node.get("default_value") is not None
        else node.get("sample_value")
        if node.get("sample_value") is not None
        else node.get("example_value")
        if node.get("example_value") is not None
        else ""
    )
    metadata = {
        "node_type": node_type,
        "raw_node": node,
    }
    if node_type == NODE_TYPE_FIELD:
        metadata.update(
            {
                "visual_logic": _visual_logic(node),
                "visual_coordinates": _visual_coordinates(node),
                "condition_logic": _condition_logic(node),
            }
        )
    elif node_type == NODE_TYPE_CHOICE_GROUP:
        metadata["choice_logic"] = _choice_logic(node)
    elif node_type == NODE_TYPE_TABLE:
        metadata["table_logic"] = _table_logic(node)

    return {
        "op_id": f"export.{node_id}",
        "op_type": op_type,
        "source_node_id": node_id,
        "field_key": field_key,
        "label": label,
        "target_cell": target_cell,
        "write_mode": write_mode,
        "value_source": field_key,
        "source": runtime_source,
        "value": runtime_value,
        "metadata": metadata,
    }


def _append_operation_warnings(plan, operation):
    if not isinstance(operation, dict):
        return plan

    node_id = normalize_text(operation.get("source_node_id"))
    field_key = normalize_text(operation.get("field_key"))
    op_type = normalize_text(operation.get("op_type"))
    target_cell = normalize_text(operation.get("target_cell"))

    if not target_cell:
        append_warning(
            plan,
            "missing_target_cell",
            "export operation missing target_cell",
            node_id,
            field_key,
        )
    if not op_type:
        append_warning(
            plan,
            "missing_operation_type",
            "export operation missing op_type",
            node_id,
            field_key,
        )
    if op_type and op_type not in SUPPORTED_EXPORT_OP_TYPES:
        append_warning(
            plan,
            "unsupported_write_mode",
            "export operation has unsupported op_type",
            node_id,
            field_key,
        )

    metadata = normalize_dict(operation.get("metadata"))
    raw_node = normalize_dict(metadata.get("raw_node"))
    table_children = [
        child
        for child in normalize_list(raw_node.get("children"))
        if isinstance(child, dict)
        and normalize_text(child.get("field_type")) == "table_column"
    ]
    if op_type == "write_table_cell" and not table_children:
        append_warning(
            plan,
            "table_without_children",
            "table export operation has no table_column children",
            node_id,
            field_key,
        )
    if op_type == "write_image" and not normalize_dict(raw_node.get("region")):
        append_warning(
            plan,
            "object_without_region",
            "image export operation has no region",
            node_id,
            field_key,
        )
    return plan


def build_export_plan_from_document_model(model):
    plan = _empty_export_plan()
    if not isinstance(model, dict):
        append_warning(
            plan,
            "invalid_document_model",
            "document model is not dict",
        )
        return plan

    for node in collect_all_nodes(model):
        operation = build_export_operation_from_node(model, node)
        if not operation:
            continue

        plan["operations"].append(operation)
        _append_operation_warnings(plan, operation)

    plan["operations"].sort(
        key=lambda operation: (
            normalize_text(operation.get("field_key")),
            normalize_text(operation.get("source_node_id")),
        )
    )
    return plan
