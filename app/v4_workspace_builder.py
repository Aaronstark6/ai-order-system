"""
Build a standalone Workspace model from a V4 Document Intelligence Model.

This module only converts in-memory document intelligence data into a
Workspace-friendly structure. It does not connect to existing Workspace,
Export, Pipeline, AI, routes, or page logic.
"""

from app.v4_document_intelligence import (
    LINK_TYPE_BELONGS_TO,
    NODE_TYPE_CHOICE_GROUP,
    NODE_TYPE_FIELD,
    NODE_TYPE_OBJECT,
    NODE_TYPE_SECTION,
    NODE_TYPE_TABLE,
    collect_all_nodes,
    normalize_dict,
    normalize_list,
    normalize_text,
)


def _empty_workspace_model():
    return {
        "sections": [],
        "workspace_fields": [],
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


def _find_belongs_to_section(model, node):
    node_id = _node_id(node)
    if not node_id:
        return {}

    nodes_by_id = _nodes_by_id(model)
    for link in _links(model):
        if normalize_text(link.get("link_type")) != LINK_TYPE_BELONGS_TO:
            continue
        if normalize_text(link.get("from_node_id")) != node_id:
            continue

        section = nodes_by_id.get(normalize_text(link.get("to_node_id")), {})
        if isinstance(section, dict) and _node_type(section) == NODE_TYPE_SECTION:
            return section
    return {}


def _safe_number(value, default=0):
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def resolve_workspace_visibility(node):
    if not isinstance(node, dict):
        return "hidden"

    extra = _metadata_extra(node)
    write_mode = normalize_text(extra.get("write_mode"))
    intent_type = normalize_text(extra.get("intent_type"))
    if write_mode in {"skip", "none"}:
        return "hidden"
    if write_mode == "readonly":
        return "readonly"
    if intent_type in {"note_instruction", "readonly_example", "title"}:
        return "readonly"
    if intent_type == "table_column_header":
        return "advanced_only"
    return "visible"


def resolve_choice_render_hint(node):
    if not isinstance(node, dict):
        return "text_choice"

    selection_mode = normalize_text(node.get("selection_mode")) or "single"
    options = normalize_list(node.get("options"))
    if selection_mode == "multiple":
        return "checkbox"
    if not options:
        return "text_choice"
    if len(options) <= 4:
        return "radio"
    return "dropdown"


def build_table_rendering_hint(node):
    if not isinstance(node, dict):
        return {}

    columns = normalize_list(node.get("columns"))
    column_labels = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        label = normalize_text(column.get("label"))
        if label:
            column_labels.append(label)

    return {
        "has_columns": bool(columns),
        "column_count": len(columns),
        "column_labels": column_labels,
        "dynamic_rows": True,
    }


def append_warning(result, code, message, node_id="", field_key=""):
    if not isinstance(result, dict):
        return result

    if not isinstance(result.get("warnings"), list):
        result["warnings"] = []
    result["warnings"].append(
        {
            "code": normalize_text(code),
            "message": normalize_text(message),
            "node_id": normalize_text(node_id),
            "field_key": normalize_text(field_key),
        }
    )
    return result


def resolve_workspace_section(model, node):
    fallback = {
        "section_key": "other",
        "section_title": "其他字段",
        "section_order": 999999,
        "section_node_id": "",
    }
    if not isinstance(node, dict):
        return fallback

    section = {}
    section_id = normalize_text(node.get("section_id"))
    if section_id:
        candidate = _nodes_by_id(model).get(section_id, {})
        if isinstance(candidate, dict) and _node_type(candidate) == NODE_TYPE_SECTION:
            section = candidate
        else:
            return {
                "section_key": section_id,
                "section_title": section_id,
                "section_order": 999999,
                "section_node_id": section_id,
            }
    else:
        section = _find_belongs_to_section(model, node)

    if not isinstance(section, dict) or not section:
        return fallback

    section_node_id = _node_id(section)
    section_key = normalize_text(section.get("section_key")) or section_node_id
    section_title = normalize_text(section.get("label")) or section_key
    return {
        "section_key": section_key or fallback["section_key"],
        "section_title": section_title or fallback["section_title"],
        "section_order": _safe_number(section.get("order"), default=0),
        "section_node_id": section_node_id,
    }


def build_workspace_section_from_section_node(node):
    if not isinstance(node, dict):
        return {}

    node_id = _node_id(node)
    section_key = normalize_text(node.get("section_key")) or node_id
    if not section_key:
        return {}

    section_title = normalize_text(node.get("label")) or section_key
    return {
        "section_key": section_key,
        "section_title": section_title,
        "section_order": _safe_number(node.get("order"), default=0),
        "node_id": node_id,
    }


def _base_workspace_field(model, node):
    section = resolve_workspace_section(model, node)
    extra = _metadata_extra(node)
    return {
        "node_id": _node_id(node),
        "field_key": "",
        "label": "",
        "field_type": "",
        "section_key": section.get("section_key", "other"),
        "section_title": section.get("section_title", "其他字段"),
        "section_order": section.get("section_order", 999999),
        "section_node_id": section.get("section_node_id", ""),
        "source_cell": normalize_text(node.get("source_cell")),
        "target_cell": normalize_text(node.get("target_cell")),
        "write_mode": normalize_text(extra.get("write_mode")),
        "intent_type": normalize_text(extra.get("intent_type")),
        "ai_extract_hint": "",
        "display_order": _safe_number(
            node.get("display_order", node.get("row", 0)), default=0
        ),
        "visibility": resolve_workspace_visibility(node),
        "metadata": normalize_dict(node.get("metadata")),
    }


def build_workspace_field_from_field_node(model, node):
    if not isinstance(node, dict):
        return {}

    field_key = normalize_text(node.get("field_key"))
    if not field_key:
        return {}

    label = normalize_text(node.get("label")) or field_key
    field = _base_workspace_field(model, node)
    field.update(
        {
            "field_key": field_key,
            "label": label,
            "field_type": normalize_text(node.get("field_type")) or "text",
            "ai_extract_hint": normalize_text(node.get("ai_extract_hint")) or label,
        }
    )
    return field


def build_workspace_field_from_choice_group_node(model, node):
    if not isinstance(node, dict):
        return {}

    field_key = normalize_text(node.get("field_key"))
    if not field_key:
        return {}

    label = normalize_text(node.get("label")) or field_key
    field = _base_workspace_field(model, node)
    field.update(
        {
            "field_key": field_key,
            "label": label,
            "field_type": "choice",
            "options": normalize_list(node.get("options")),
            "selection_mode": normalize_text(node.get("selection_mode")) or "single",
            "render_hint": resolve_choice_render_hint(node),
        }
    )
    return field


def build_workspace_field_from_table_node(model, node):
    if not isinstance(node, dict):
        return {}

    node_id = _node_id(node)
    field_key = normalize_text(node.get("field_key")) or node_id
    if not field_key:
        return {}

    label = normalize_text(node.get("label")) or field_key
    field = _base_workspace_field(model, node)
    field.update(
        {
            "field_key": field_key,
            "label": label,
            "field_type": "table",
            "columns": normalize_list(node.get("columns")),
            "data_region": normalize_dict(node.get("data_region")),
            "table_rendering": build_table_rendering_hint(node),
        }
    )
    return field


def build_workspace_field_from_object_node(model, node):
    if not isinstance(node, dict):
        return {}

    node_id = _node_id(node)
    field_key = normalize_text(node.get("field_key")) or node_id
    if not field_key:
        return {}

    object_type = normalize_text(node.get("object_type"))
    label = normalize_text(node.get("label")) or field_key
    field = _base_workspace_field(model, node)
    field.update(
        {
            "field_key": field_key,
            "label": label,
            "field_type": object_type or "object",
            "object_type": object_type,
            "region": normalize_dict(node.get("region")),
        }
    )
    return field


def _append_section(sections, section, seen_section_keys):
    if not isinstance(section, dict):
        return

    section_key = normalize_text(section.get("section_key"))
    if not section_key or section_key in seen_section_keys:
        return

    seen_section_keys.add(section_key)
    sections.append(section)


def _section_from_workspace_field(field):
    if not isinstance(field, dict):
        return {}

    section_key = normalize_text(field.get("section_key"))
    if not section_key:
        return {}

    return {
        "section_key": section_key,
        "section_title": normalize_text(field.get("section_title")) or section_key,
        "section_order": _safe_number(field.get("section_order"), default=999999),
        "node_id": normalize_text(field.get("section_node_id")),
    }


def _append_workspace_field_warnings(result, field):
    if not isinstance(field, dict):
        return result

    field_key = normalize_text(field.get("field_key"))
    node_id = normalize_text(field.get("node_id"))
    field_type = normalize_text(field.get("field_type"))

    if not field_key:
        append_warning(
            result,
            "missing_field_key",
            "workspace field missing field_key",
            node_id=node_id,
        )
    if normalize_text(field.get("section_key")) == "other":
        append_warning(
            result,
            "unresolved_section",
            "workspace field fallback to other section",
            node_id=node_id,
            field_key=field_key,
        )
    if field_type == "choice" and not normalize_list(field.get("options")):
        append_warning(
            result,
            "choice_without_options",
            "choice workspace field has no options",
            node_id=node_id,
            field_key=field_key,
        )
    if field_type == "table" and not normalize_list(field.get("columns")):
        append_warning(
            result,
            "table_without_columns",
            "table workspace field has no columns",
            node_id=node_id,
            field_key=field_key,
        )
    if normalize_text(field.get("object_type")) and not normalize_dict(
        field.get("region")
    ):
        append_warning(
            result,
            "object_without_region",
            "object workspace field has no region",
            node_id=node_id,
            field_key=field_key,
        )
    return result


def build_workspace_model_from_document_model(model):
    workspace_model = _empty_workspace_model()
    if not isinstance(model, dict):
        workspace_model["warnings"].append("document model is not dict")
        return workspace_model

    nodes = collect_all_nodes(model)
    seen_section_keys = set()
    for node in nodes:
        if _node_type(node) != NODE_TYPE_SECTION:
            continue
        _append_section(
            workspace_model["sections"],
            build_workspace_section_from_section_node(node),
            seen_section_keys,
        )

    field_builders = {
        NODE_TYPE_FIELD: build_workspace_field_from_field_node,
        NODE_TYPE_CHOICE_GROUP: build_workspace_field_from_choice_group_node,
        NODE_TYPE_TABLE: build_workspace_field_from_table_node,
        NODE_TYPE_OBJECT: build_workspace_field_from_object_node,
    }
    for node in nodes:
        builder = field_builders.get(_node_type(node))
        if not builder:
            continue

        field = builder(model, node)
        if not field:
            continue

        workspace_model["workspace_fields"].append(field)
        _append_workspace_field_warnings(workspace_model, field)
        _append_section(
            workspace_model["sections"],
            _section_from_workspace_field(field),
            seen_section_keys,
        )

    workspace_model["workspace_fields"].sort(
        key=lambda field: (
            _safe_number(field.get("section_order"), default=999999),
            _safe_number(field.get("display_order"), default=0),
            normalize_text(field.get("label")),
        )
    )
    workspace_model["sections"].sort(
        key=lambda section: (
            _safe_number(section.get("section_order"), default=999999),
            normalize_text(section.get("section_title")),
        )
    )
    return workspace_model
