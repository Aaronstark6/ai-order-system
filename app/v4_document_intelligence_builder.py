"""
Phase2 Builder for V4 Document Intelligence.

This module only converts an existing template_analysis dict into the
Document Intelligence Model defined in app.v4_document_intelligence. It does
not connect to Workspace, AI, Export, or Pipeline logic.
"""

from app.v4_document_intelligence import (
    LINK_TYPE_BELONGS_TO,
    LINK_TYPE_CONTAINS,
    LINK_TYPE_USES_POLICY,
    LINK_TYPE_WRITES_TO,
    NODE_TYPE_CHOICE_GROUP,
    NODE_TYPE_FIELD,
    NODE_TYPE_OBJECT,
    NODE_TYPE_RUNTIME_POLICY,
    NODE_TYPE_SECTION,
    NODE_TYPE_TABLE,
    NODE_TYPE_VISUAL,
    SOURCE_TYPE_TEMPLATE_ANALYSIS,
    build_choice_group_node,
    build_empty_document_intelligence_model,
    build_field_node,
    build_link,
    build_metadata,
    build_node_source,
    build_object_node,
    build_runtime_policy_node,
    build_section_node,
    build_table_node,
    build_visual_semantic_node as _build_visual_semantic_node,
    make_node_id,
    normalize_dict,
    normalize_document_intelligence_model,
    normalize_list,
    normalize_text,
    refresh_document_intelligence_summary,
    validate_document_intelligence_model,
)


SEMANTIC_TYPE_FIELD_LABEL = "field_label"
SEMANTIC_TYPE_INLINE_FIELD = "inline_field"
SEMANTIC_TYPE_SECTION_HEADER = "section_header"
SEMANTIC_TYPE_TABLE_REGION = "table_region"
SEMANTIC_TYPE_TABLE_HEADER = "table_header"
SEMANTIC_TYPE_OPTION_GROUP = "option_group"
SEMANTIC_TYPE_OPTION_ITEM = "option_item"
SEMANTIC_TYPE_IMAGE_ATTACHMENT_AREA = "image_attachment_area"
SEMANTIC_TYPE_NOTE_INSTRUCTION = "note_instruction"
SEMANTIC_TYPE_TITLE = "title"

_NODE_COLLECTION_BY_TYPE = {
    NODE_TYPE_FIELD: "fields",
    NODE_TYPE_SECTION: "sections",
    NODE_TYPE_TABLE: "tables",
    NODE_TYPE_CHOICE_GROUP: "choice_groups",
    NODE_TYPE_OBJECT: "objects",
    NODE_TYPE_VISUAL: "visual_semantics",
    NODE_TYPE_RUNTIME_POLICY: "runtime_policies",
}


def build_visual_semantic_node(
    node_id,
    semantic_type,
    label="",
    coordinates=None,
    region=None,
    style=None,
    confidence=0,
    metadata=None,
    source=None,
    orientation="",
    role="",
    priority=0,
    merge=None,
    cell=None,
    row=None,
    col=None,
    page=None,
    bbox=None,
):
    coordinates_dict = normalize_dict(coordinates)
    if cell is not None and not coordinates_dict.get("source_cell"):
        coordinates_dict["source_cell"] = normalize_text(cell)
    if row is not None:
        coordinates_dict["row"] = row
    if col is not None:
        coordinates_dict["col"] = col
    if page is not None:
        coordinates_dict["page"] = page
    if bbox is not None:
        coordinates_dict["bbox"] = normalize_dict(bbox)
    return _build_visual_semantic_node(
        node_id=node_id,
        semantic_type=semantic_type,
        label=label,
        coordinates=coordinates_dict,
        region=region,
        style=style,
        confidence=confidence,
        metadata=metadata,
        source=source,
        orientation=orientation,
        role=role,
        priority=priority,
        merge=merge,
    )


def _safe_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _region_type(region):
    if not isinstance(region, dict):
        return ""
    region_type = normalize_text(region.get("type"))
    if not region_type:
        region_type = normalize_text(region.get("semantic_type"))
    return region_type


def _region_coordinates(region):
    region = normalize_dict(region)
    return normalize_dict(region.get("coordinates"))


def _region_source_cell(region):
    coordinates = _region_coordinates(region)
    return normalize_text(coordinates.get("source_cell"))


def _region_target_cell(region):
    coordinates = _region_coordinates(region)
    return normalize_text(coordinates.get("target_cell"))


def _region_cells(region):
    coordinates = _region_coordinates(region)
    return normalize_list(coordinates.get("cells"))


def _region_row(region):
    coordinates = _region_coordinates(region)
    number = _safe_number(coordinates.get("row"), default=0)
    if number == int(number):
        return int(number)
    return number


def _region_col(region):
    coordinates = _region_coordinates(region)
    number = _safe_number(coordinates.get("col"), default=0)
    if number == int(number):
        return int(number)
    return number


def _region_area(region):
    coordinates = _region_coordinates(region)
    return {
        "coordinates": coordinates,
    }


def _region_label(region):
    if not isinstance(region, dict):
        return ""
    for key in ("label", "suggested_name", "name", "region_id"):
        value = normalize_text(region.get(key))
        if value:
            return value
    source_cell = _region_source_cell(region)
    if source_cell:
        return source_cell
    return ""


def _region_node_source(region):
    region = normalize_dict(region)
    return build_node_source(
        source_type=SOURCE_TYPE_TEMPLATE_ANALYSIS,
        source_id=region.get("region_id", ""),
        source_detail=_region_type(region),
        confidence=region.get("confidence", 0),
        metadata={
            "coordinates": _region_coordinates(region),
        },
    )


def extract_semantic_regions(template_analysis):
    if not isinstance(template_analysis, dict):
        return []

    semantic_regions = template_analysis.get("semantic_regions")
    if not isinstance(semantic_regions, list):
        return []

    return [region for region in semantic_regions if isinstance(region, dict)]


def append_node_to_model(model, node):
    if not isinstance(model, dict) or not isinstance(node, dict):
        return model

    nodes = model.get("nodes")
    if not isinstance(nodes, dict):
        model["nodes"] = {}
        nodes = model["nodes"]

    node_type = normalize_text(node.get("node_type"))
    collection_key = _NODE_COLLECTION_BY_TYPE.get(node_type)
    if not collection_key:
        warnings = model.setdefault("warnings", [])
        if isinstance(warnings, list):
            warnings.append(f"unknown node_type skipped: {node_type}")
        return model

    collection = nodes.setdefault(collection_key, [])
    if isinstance(collection, list):
        collection.append(node)
    return model


def _is_section_node(node):
    return isinstance(node, dict) and normalize_text(
        node.get("node_type")
    ) == NODE_TYPE_SECTION


def _node_id(node):
    if isinstance(node, dict):
        return normalize_text(node.get("node_id"))
    return ""


def build_option_from_region(region):
    if not isinstance(region, dict):
        return {}

    label = _region_label(region)
    value = normalize_text(region.get("option_value"))
    if not value:
        value = normalize_text(region.get("value")) or label

    return {
        "label": label,
        "value": value,
        "coordinates": _region_coordinates(region),
        "write_mode": normalize_text(region.get("write_mode")),
        "intent_type": normalize_text(region.get("intent_type")),
        "confidence": _safe_number(region.get("confidence")),
        "metadata": build_metadata(
            origin="template_analysis.semantic_regions.option_item",
            raw=region,
            extra={"row": _region_row(region), "region_type": _region_type(region)},
        ),
    }


def collect_option_items_by_row(semantic_regions):
    if not isinstance(semantic_regions, list):
        return {}

    option_items_by_row = {}
    for region in semantic_regions:
        if not isinstance(region, dict):
            continue
        if _region_type(region) != SEMANTIC_TYPE_OPTION_ITEM:
            continue

        option = build_option_from_region(region)
        if not option:
            continue

        row_key = str(_region_row(region))
        option_items_by_row.setdefault(row_key, []).append(option)
    return option_items_by_row


def _choice_group_row(region):
    return _region_row(region)


def normalize_table_columns(columns):
    if not isinstance(columns, list):
        return []

    normalized_columns = []
    for column in columns:
        if not isinstance(column, dict):
            continue
        normalized_columns.append(
            {
                "label": normalize_text(column.get("label")),
                "field": normalize_text(column.get("field")),
                "target_col": column.get("target_col"),
                "header_cell": normalize_text(column.get("header_cell")),
                "metadata": build_metadata(
                    origin="template_analysis.table_region.columns",
                    raw=column,
                    extra={},
                ),
            }
        )
    return normalized_columns


def build_table_metadata_extra(region):
    if not isinstance(region, dict):
        return {}

    extra = {}
    for key in (
        "bounds",
        "score",
        "candidate_type",
        "reason",
        "columns_count",
        "rows_count",
        "start_row",
        "end_row",
        "start_col",
        "end_col",
    ):
        if key in region:
            extra[key] = region.get(key)
    return extra


def build_visual_metadata_extra(region):
    if not isinstance(region, dict):
        return {}

    region_type = _region_type(region)
    extra = {
        "region_type": region_type,
        "write_mode": normalize_text(region.get("write_mode")),
        "intent_type": normalize_text(region.get("intent_type")),
    }
    if region_type == SEMANTIC_TYPE_TABLE_HEADER:
        extra["role"] = "table_header"
    return extra


def append_link_to_model(model, link):
    if not isinstance(model, dict) or not isinstance(link, dict):
        return model

    if not isinstance(model.get("links"), list):
        model["links"] = []
    model["links"].append(link)
    return model


def append_section_relationship_links(model, node, current_section_id):
    if not isinstance(node, dict):
        return model

    current_section_id = normalize_text(current_section_id)
    if not current_section_id or _is_section_node(node):
        return model

    node_id = _node_id(node)
    if not node_id:
        return model

    append_link_to_model(
        model,
        build_link(
            LINK_TYPE_BELONGS_TO,
            from_node_id=node_id,
            to_node_id=current_section_id,
            label="belongs to section",
        ),
    )
    append_link_to_model(
        model,
        build_link(
            LINK_TYPE_CONTAINS,
            from_node_id=current_section_id,
            to_node_id=node_id,
            label="section contains node",
        ),
    )
    return model


def append_runtime_policy_links(model, node, runtime_policy, region):
    if not isinstance(node, dict) or not isinstance(runtime_policy, dict):
        return model

    node_id = _node_id(node)
    policy_id = _node_id(runtime_policy)
    if not node_id or not policy_id:
        return model

    append_link_to_model(
        model,
        build_link(
            LINK_TYPE_USES_POLICY,
            from_node_id=node_id,
            to_node_id=policy_id,
            label="uses runtime policy",
        ),
    )

    target_cell = _region_target_cell(region)
    if target_cell:
        append_link_to_model(
            model,
            build_link(
                LINK_TYPE_WRITES_TO,
                from_node_id=node_id,
                to_node_id=f"cell.{target_cell}",
                label="writes to target cell",
                metadata={"target_cell": target_cell},
            ),
        )

    return model


def build_field_node_from_region(region):
    region_type = _region_type(region)
    label = _region_label(region)
    field_key = normalize_text(region.get("field_key")) or label
    source_cell = _region_source_cell(region)
    target_cell = _region_target_cell(region)
    write_mode = normalize_text(region.get("write_mode"))
    field_type = "text"
    if region_type == SEMANTIC_TYPE_INLINE_FIELD:
        field_type = "textarea" if write_mode == "append_after_colon" else "text"

    return build_field_node(
        node_id=make_node_id(NODE_TYPE_FIELD, field_key or label or source_cell),
        field_key=field_key,
        label=label,
        source_cell=source_cell,
        target_cell=target_cell,
        field_type=field_type,
        ai_extract_hint=label,
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions",
            raw=region,
            extra={
                "region_type": region_type,
                "write_mode": write_mode,
                "intent_type": normalize_text(region.get("intent_type")),
            },
        ),
        source=_region_node_source(region),
    )


def build_section_node_from_region(region):
    label = _region_label(region)
    source_cell = _region_source_cell(region)
    section_key = normalize_text(region.get("section_key")) or label
    return build_section_node(
        node_id=make_node_id(NODE_TYPE_SECTION, section_key or label or source_cell),
        label=label,
        section_key=section_key,
        bounds=_region_area(region),
        order=_safe_number(_region_row(region)),
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions",
            raw=region,
            extra={"region_type": _region_type(region)},
        ),
        source=_region_node_source(region),
    )


def build_table_node_from_region(region):
    label = _region_label(region)
    source_cell = _region_source_cell(region)
    target_cell = _region_target_cell(region)
    return build_table_node(
        node_id=make_node_id(NODE_TYPE_TABLE, label or source_cell),
        label=label,
        section_id="",
        header_cells=(region.get("header_cells") or _region_cells(region)),
        data_region={
            "coordinates": _region_coordinates(region),
        },
        columns=normalize_table_columns(region.get("columns")),
        rows=region.get("rows"),
        cells=_region_cells(region),
        merged_cells=region.get("merged_cells"),
        orientation=region.get("orientation", "row"),
        header_mode=region.get("header_mode", "first_row"),
        allow_dynamic_rows=region.get("allow_dynamic_rows", False),
        allow_dynamic_columns=region.get("allow_dynamic_columns", False),
        min_rows=region.get("min_rows", 0),
        max_rows=region.get("max_rows"),
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions.table_region",
            raw=region,
            extra={
                "region_type": _region_type(region),
                "write_mode": normalize_text(region.get("write_mode")),
                "intent_type": normalize_text(region.get("intent_type")),
                "table": build_table_metadata_extra(region),
            },
        ),
        source=_region_node_source(region),
    )


def build_choice_group_node_from_region(region, option_items_by_row=None):
    label = _region_label(region)
    field_key = normalize_text(region.get("field_key")) or label
    source_cell = _region_source_cell(region)
    options = normalize_list(region.get("options"))
    if not options:
        options = [
            {
                "label": str(cell),
                "value": str(cell),
                "coordinates": {
                    "source_cell": str(cell),
                    "target_cell": str(cell),
                    "cells": [str(cell)],
                },
            }
            for cell in _region_cells(region)
        ]
    row_key = str(_choice_group_row(region))
    if isinstance(option_items_by_row, dict) and row_key in option_items_by_row:
        row_options = [
            option
            for option in normalize_list(option_items_by_row.get(row_key))
            if isinstance(option, dict)
        ]
        if row_options:
            options = row_options

    options = [option for option in options if isinstance(option, dict)]

    return build_choice_group_node(
        node_id=make_node_id(
            NODE_TYPE_CHOICE_GROUP, field_key or label or source_cell
        ),
        field_key=field_key,
        label=label,
        options=options,
        selection_mode=region.get("selection_mode", "single"),
        required=region.get("required", False),
        default_value=region.get("default_value"),
        allowed_values=region.get("allowed_values"),
        disabled_values=region.get("disabled_values"),
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions",
            raw=region,
            extra={"region_type": _region_type(region)},
        ),
        source=_region_node_source(region),
    )


def build_object_node_from_region(region):
    label = _region_label(region)
    source_cell = _region_source_cell(region)
    return build_object_node(
        node_id=make_node_id(NODE_TYPE_OBJECT, label or source_cell),
        object_type=SEMANTIC_TYPE_IMAGE_ATTACHMENT_AREA,
        label=label,
        cell=source_cell,
        region=_region_area(region),
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions",
            raw=region,
            extra={"region_type": _region_type(region)},
        ),
        source=_region_node_source(region),
    )


def build_visual_node_from_region(region):
    region_type = _region_type(region)
    label = _region_label(region)
    source_cell = _region_source_cell(region)
    return build_visual_semantic_node(
        node_id=make_node_id(
            NODE_TYPE_VISUAL,
            f"{region_type}.{label or source_cell}",
        ),
        semantic_type=region_type,
        label=label,
        cell=source_cell,
        region=_region_area(region),
        style=normalize_dict(region.get("style")),
        row=_region_row(region),
        col=_region_col(region),
        page=region.get("page"),
        bbox=region.get("bbox"),
        orientation=region.get("orientation", ""),
        role=region.get("role", ""),
        priority=region.get("priority", 0),
        merge=region.get("merge"),
        confidence=_safe_number(region.get("confidence")),
        metadata=build_metadata(
            origin="template_analysis.semantic_regions.visual",
            raw=region,
            extra=build_visual_metadata_extra(region),
        ),
        source=_region_node_source(region),
    )


def build_runtime_policy_from_region(region, source_node_id):
    write_mode = normalize_text(region.get("write_mode"))
    intent_type = normalize_text(region.get("intent_type"))
    if not write_mode or write_mode == "skip":
        return None

    return build_runtime_policy_node(
        node_id=make_node_id(
            NODE_TYPE_RUNTIME_POLICY,
            f"{source_node_id}.{write_mode}",
        ),
        policy_type=write_mode,
        source_node_id=source_node_id,
        action=write_mode,
        metadata=build_metadata(
            origin="template_analysis.semantic_regions.runtime_policy",
            raw=region,
            extra={"intent_type": intent_type},
        ),
        source=_region_node_source(region),
    )


def convert_semantic_region(region, option_items_by_row=None):
    if not isinstance(region, dict):
        return None, None

    region_type = _region_type(region)
    if region_type in (SEMANTIC_TYPE_FIELD_LABEL, SEMANTIC_TYPE_INLINE_FIELD):
        node = build_field_node_from_region(region)
    elif region_type == SEMANTIC_TYPE_SECTION_HEADER:
        node = build_section_node_from_region(region)
    elif region_type == SEMANTIC_TYPE_TABLE_REGION:
        node = build_table_node_from_region(region)
    elif region_type == SEMANTIC_TYPE_OPTION_GROUP:
        node = build_choice_group_node_from_region(
            region, option_items_by_row=option_items_by_row
        )
    elif region_type == SEMANTIC_TYPE_IMAGE_ATTACHMENT_AREA:
        node = build_object_node_from_region(region)
    else:
        node = build_visual_node_from_region(region)

    runtime_policy = None
    if isinstance(node, dict):
        runtime_policy = build_runtime_policy_from_region(
            region, normalize_text(node.get("node_id"))
        )
    return node, runtime_policy


def enrich_model_summary_from_template_analysis(model, template_analysis):
    if not isinstance(model, dict) or not isinstance(template_analysis, dict):
        return model

    semantic_summary = template_analysis.get("semantic_summary")
    if isinstance(semantic_summary, dict):
        if not isinstance(model.get("summary"), dict):
            model["summary"] = {}
        model["summary"]["semantic_summary"] = normalize_dict(semantic_summary)
    return model


def build_document_intelligence_model(template_analysis, source=None):
    model = build_empty_document_intelligence_model()
    if isinstance(source, dict):
        model["source"].update(source)

    semantic_regions = extract_semantic_regions(template_analysis)
    option_items_by_row = collect_option_items_by_row(semantic_regions)
    if not semantic_regions:
        model["warnings"].append("template_analysis.semantic_regions is empty")

    current_section_id = ""
    for region in semantic_regions:
        node, runtime_policy = convert_semantic_region(
            region, option_items_by_row=option_items_by_row
        )
        if isinstance(node, dict):
            append_node_to_model(model, node)
            if _is_section_node(node):
                current_section_id = _node_id(node)
            else:
                model = append_section_relationship_links(
                    model, node, current_section_id
                )

        if isinstance(runtime_policy, dict):
            append_node_to_model(model, runtime_policy)
            if isinstance(node, dict):
                model = append_runtime_policy_links(
                    model, node, runtime_policy, region
                )

        if node is None and runtime_policy is None:
            model["warnings"].append("semantic region skipped")

    refresh_document_intelligence_summary(model)
    model = enrich_model_summary_from_template_analysis(model, template_analysis)
    validation = validate_document_intelligence_model(model)
    model["warnings"].extend(normalize_list(validation.get("warnings")))
    model["errors"].extend(normalize_list(validation.get("errors")))
    normalized_model = normalize_document_intelligence_model(model)
    return enrich_model_summary_from_template_analysis(
        normalized_model, template_analysis
    )
