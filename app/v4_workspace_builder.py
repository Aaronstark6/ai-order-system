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
        "workspace_components": [],
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
    summary = _semantic_summary(node)
    write_mode = normalize_text(summary.get("write_mode")) or normalize_text(extra.get("write_mode"))
    intent_type = normalize_text(summary.get("intent_type")) or normalize_text(extra.get("intent_type"))
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
    section_summary = _semantic_summary(section)
    section_title = normalize_text(section_summary.get("label")) or normalize_text(section.get("label")) or section_key
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

    summary = _semantic_summary(node)
    section_title = normalize_text(summary.get("label")) or normalize_text(node.get("label")) or section_key
    return {
        "section_key": section_key,
        "section_title": section_title,
        "section_order": _safe_number(node.get("order"), default=0),
        "node_id": node_id,
    }


def _base_workspace_field(model, node):
    section = resolve_workspace_section(model, node)
    extra = _metadata_extra(node)
    coordinates = _visual_coordinates(node)
    visibility = resolve_workspace_visibility(node)
    return {
        "node_id": _node_id(node),
        "field_key": "",
        "label": "",
        "field_type": "",
        "section_key": section.get("section_key", "other"),
        "section_title": section.get("section_title", "其他字段"),
        "section_order": section.get("section_order", 999999),
        "section_node_id": section.get("section_node_id", ""),
        "source_cell": normalize_text(coordinates.get("source_cell", "")),
        "target_cell": normalize_text(coordinates.get("target_cell", "")),
        "write_mode": normalize_text(extra.get("write_mode")),
        "intent_type": normalize_text(extra.get("intent_type")),
        "ai_extract_hint": "",
        "required": bool(node.get("required", False)),
        "editable": bool(
            node.get("editable", True)
        ),
        "display_order": _safe_number(
            node.get("display_order", node.get("row", 0)), default=0
        ),
        "visibility": visibility,
        "metadata": normalize_dict(node.get("metadata")),
        "semantic_summary": _semantic_summary(node),
        "visual_metadata": _visual_metadata(node),
        "condition_metadata": _condition_metadata(node),
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
            "visual_logic": _visual_logic(node),
            "condition_logic": _condition_logic(node),
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
            "choice_logic": _choice_logic(node),
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
            "rows": normalize_list(node.get("rows")),
            "cells": normalize_list(node.get("cells")),
            "data_region": normalize_dict(node.get("data_region")),
            "table_rendering": build_table_rendering_hint(node),
            "table_logic": _table_logic(node),
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


def _component_type_from_workspace_field(field):
    if not isinstance(field, dict):
        return "unknown"

    field_type = normalize_text(field.get("field_type"))
    object_type = normalize_text(field.get("object_type"))

    if field_type == "choice":
        return "choice_group"
    if field_type == "table":
        return "table"
    if field_type in ("image_attachment_area", "image", "object") or object_type:
        return object_type or "object_area"
    if field_type in ("date", "number", "text", "textarea"):
        return field_type
    if field_type:
        return field_type
    return "text"


def _field_metadata_raw(field):
    if not isinstance(field, dict):
        return {}
    metadata = field.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    raw = metadata.get("raw")
    if isinstance(raw, dict):
        return raw
    return {}


def _field_metadata_extra(field):
    if not isinstance(field, dict):
        return {}
    metadata = field.get("metadata")
    if not isinstance(metadata, dict):
        return {}
    extra = metadata.get("extra")
    if isinstance(extra, dict):
        return extra
    return {}


def _first_list_value(*values):
    for value in values:
        if isinstance(value, list) and value:
            return value
    return []


def _build_choice_option_elements(field):
    nested_field = field.get("field") if isinstance(field.get("field"), dict) else {}
    options = _first_list_value(
        field.get("options"),
        nested_field.get("options"),
        _field_metadata_raw(field).get("options"),
    )
    elements = []
    for index, option in enumerate(normalize_list(options), start=1):
        if isinstance(option, dict):
            label = normalize_text(option.get("label"))
            value = normalize_text(option.get("value")) or label
            coordinates = (
                option.get("coordinates")
                if isinstance(option.get("coordinates"), dict)
                else {}
            )
        else:
            label = normalize_text(option)
            value = label
            coordinates = {}
        if not label and not value:
            continue
        elements.append(
            {
                "element_key": f"option_{index}",
                "element_type": "choice_option",
                "label": label,
                "value": value,
                "coordinates": coordinates,
                "raw": option,
            }
        )
    return elements


def _build_table_column_elements(field):
    raw = _field_metadata_raw(field)
    extra = _field_metadata_extra(field)
    nested_field = field.get("field") if isinstance(field.get("field"), dict) else {}
    raw_field = raw.get("field") if isinstance(raw.get("field"), dict) else {}
    raw_table = raw.get("table") if isinstance(raw.get("table"), dict) else {}
    table_extra = extra.get("table") if isinstance(extra.get("table"), dict) else {}

    columns = _first_list_value(
        field.get("columns"),
        nested_field.get("columns"),
        raw.get("columns"),
        raw_field.get("columns"),
        raw_table.get("columns"),
        table_extra.get("columns"),
    )

    elements = []
    for index, column in enumerate(normalize_list(columns), start=1):
        if isinstance(column, dict):
            label = normalize_text(column.get("label")) or normalize_text(
                column.get("field")
            )
            column_key = (
                normalize_text(column.get("field"))
                or normalize_text(column.get("column_key"))
                or f"column_{index}"
            )
            header_cell = normalize_text(column.get("header_cell"))
            target_col = column.get("target_col")
        else:
            label = normalize_text(column)
            column_key = f"column_{index}"
            header_cell = ""
            target_col = None

        if not label and not column_key:
            continue

        elements.append(
            {
                "element_key": column_key,
                "element_type": "table_column",
                "label": label,
                "field": column_key,
                "header_cell": header_cell,
                "target_col": target_col,
                "raw": column,
            }
        )

    return elements


def _build_anchor_elements(field, component_type):
    raw = _field_metadata_raw(field)
    coordinates = {}
    for candidate in (
        field.get("coordinates"),
        raw.get("coordinates"),
        field.get("region"),
        raw.get("region"),
    ):
        if isinstance(candidate, dict):
            nested_coordinates = candidate.get("coordinates")
            coordinates = (
                nested_coordinates
                if isinstance(nested_coordinates, dict)
                else candidate
            )
            break

    source_cell = (
        normalize_text(field.get("source_cell"))
        or normalize_text(raw.get("source_cell"))
        or normalize_text(coordinates.get("source_cell"))
    )
    target_cell = (
        normalize_text(field.get("target_cell"))
        or normalize_text(raw.get("target_cell"))
        or normalize_text(coordinates.get("target_cell"))
    )

    element_type = (
        "image_anchor"
        if component_type in ("image_attachment_area", "image")
        else "object_anchor"
    )

    return [
        {
            "element_key": element_type,
            "element_type": element_type,
            "source_cell": source_cell,
            "target_cell": target_cell,
            "coordinates": coordinates,
            "raw": raw,
        }
    ]


def _build_field_binding_elements(field):
    return [
        {
            "element_key": "field_binding",
            "element_type": "field_binding",
            "source_cell": normalize_text(field.get("source_cell")),
            "target_cell": normalize_text(field.get("target_cell")),
            "write_mode": normalize_text(field.get("write_mode")),
            "intent_type": normalize_text(field.get("intent_type")),
        }
    ]


def build_workspace_component_elements(field, component_type):
    if not isinstance(field, dict):
        return []

    if component_type == "choice_group":
        elements = _build_choice_option_elements(field)
        return elements or _build_field_binding_elements(field)

    if component_type == "table":
        return _build_table_column_elements(field)

    if component_type in ("image_attachment_area", "image", "object_area", "object"):
        return _build_anchor_elements(field, component_type)

    return _build_field_binding_elements(field)


def build_workspace_component_from_workspace_field(field):
    if not isinstance(field, dict):
        return {}

    component_key = normalize_text(field.get("field_key")) or normalize_text(
        field.get("node_id")
    )
    if not component_key:
        return {}

    component_type = _component_type_from_workspace_field(field)
    title = normalize_text(field.get("label")) or component_key

    component = {
        "component_key": component_key,
        "component_type": component_type,
        "component_title": title,
        "node_id": normalize_text(field.get("node_id")),
        "section_key": normalize_text(field.get("section_key")),
        "section_title": normalize_text(field.get("section_title")),
        "section_order": field.get("section_order"),
        "source_cell": normalize_text(field.get("source_cell")),
        "target_cell": normalize_text(field.get("target_cell")),
        "write_mode": normalize_text(field.get("write_mode")),
        "intent_type": normalize_text(field.get("intent_type")),
        "display_order": field.get("display_order"),
        "visibility": normalize_text(field.get("visibility")) or "visible",
        "editable": bool(field.get("editable", True)),
        "required": bool(field.get("required", False)),
        "field": field,
        "elements": [],
    }

    component["elements"] = build_workspace_component_elements(field, component_type)

    return component


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

        component = build_workspace_component_from_workspace_field(field)
        if component:
            workspace_model["workspace_components"].append(component)

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
    workspace_model["workspace_components"].sort(
        key=lambda component: (
            _safe_number(component.get("section_order"), default=999999),
            _safe_number(component.get("display_order"), default=0),
            normalize_text(component.get("component_title")),
        )
    )
    workspace_model["sections"].sort(
        key=lambda section: (
            _safe_number(section.get("section_order"), default=999999),
            normalize_text(section.get("section_title")),
        )
    )
    return workspace_model
