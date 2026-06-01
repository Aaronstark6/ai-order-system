"""
V4 Document Intelligence Layer unified middle-layer skeleton.

This module only defines the future V4 document intelligence data model,
normalization helpers, lightweight validation, and node builders. It is not
connected to existing V4 routes, pages, workspace, export, executor, or
pipeline logic at this stage.
"""

import re


NODE_TYPE_FIELD = "field"
NODE_TYPE_SECTION = "section"
NODE_TYPE_TABLE = "table"
NODE_TYPE_CHOICE_GROUP = "choice_group"
NODE_TYPE_CONDITION = "condition"
NODE_TYPE_OBJECT = "object"
NODE_TYPE_VISUAL = "visual"
NODE_TYPE_RUNTIME_POLICY = "runtime_policy"

LINK_TYPE_BELONGS_TO = "belongs_to"
LINK_TYPE_CONTAINS = "contains"
LINK_TYPE_CONTROLS = "controls"
LINK_TYPE_DEPENDS_ON = "depends_on"
LINK_TYPE_WRITES_TO = "writes_to"
LINK_TYPE_USES_POLICY = "uses_policy"

SOURCE_TYPE_TEMPLATE_ANALYSIS = "template_analysis"
SOURCE_TYPE_MANUAL_CONFIG = "manual_config"
SOURCE_TYPE_WORKSPACE = "workspace"
SOURCE_TYPE_AI_PARSER = "ai_parser"
SOURCE_TYPE_LEGACY_RULES = "legacy_rules"
SOURCE_TYPE_SCHEMA = "schema"
SOURCE_TYPE_SYSTEM = "system"

SCHEMA_VERSION = "v4.document_intelligence.v1"

NODE_COLLECTION_KEYS = (
    "fields",
    "sections",
    "tables",
    "choice_groups",
    "conditions",
    "objects",
    "visual_semantics",
    "runtime_policies",
)


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_list(value):
    if isinstance(value, list):
        return list(value)
    return []


def normalize_dict(value):
    if isinstance(value, dict):
        return dict(value)
    return {}


def _normalize_number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_node_source(source):
    if isinstance(source, dict):
        return normalize_dict(source)
    return build_node_source()


def make_node_id(node_type, key="", fallback=""):
    normalized_type = normalize_text(node_type) or "node"
    normalized_key = normalize_text(key) or normalize_text(fallback) or "unknown"
    normalized_key = normalized_key.lower().replace(" ", "_")
    normalized_key = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9_.-]", "_", normalized_key)
    normalized_key = normalized_key.strip("._-") or "unknown"
    return f"{normalized_type}.{normalized_key}"


def build_node_source(
    source_type=SOURCE_TYPE_SYSTEM,
    source_id="",
    source_detail="",
    confidence=0,
    metadata=None,
):
    return {
        "source_type": normalize_text(source_type) or SOURCE_TYPE_SYSTEM,
        "source_id": normalize_text(source_id),
        "source_detail": normalize_text(source_detail),
        "confidence": _normalize_number(confidence),
        "metadata": normalize_dict(metadata),
    }


def build_metadata(origin="", raw=None, notes=None, extra=None):
    return {
        "origin": normalize_text(origin),
        "raw": raw,
        "notes": normalize_list(notes),
        "extra": normalize_dict(extra),
    }


def build_semantic_summary(
    label="",
    description="",
    intent_type="",
    write_mode="",
    field_type="",
    node_role="",
    source_cell="",
    target_cell="",
):
    return {
        "label": normalize_text(label),
        "description": normalize_text(description),
        "intent_type": normalize_text(intent_type),
        "write_mode": normalize_text(write_mode),
        "field_type": normalize_text(field_type),
        "node_role": normalize_text(node_role),
        "source_cell": normalize_text(source_cell),
        "target_cell": normalize_text(target_cell),
    }


def build_semantic_summary_from_metadata(
    label="",
    description="",
    field_type="",
    source_cell="",
    target_cell="",
    metadata=None,
):
    metadata_dict = normalize_dict(metadata)
    extra = metadata_dict.get("extra")
    if not isinstance(extra, dict):
        extra = {}

    return build_semantic_summary(
        label=label,
        description=description,
        intent_type=extra.get("intent_type", ""),
        write_mode=extra.get("write_mode", ""),
        field_type=field_type,
        node_role=extra.get("role", ""),
        source_cell=source_cell,
        target_cell=target_cell,
    )


def build_visual_metadata(
    source_cell="",
    target_cell="",
    row=None,
    col=None,
    region="",
    page=None,
    bbox=None,
):
    return {
        "source_cell": normalize_text(source_cell),
        "target_cell": normalize_text(target_cell),
        "row": row,
        "col": col,
        "region": normalize_text(region),
        "page": page,
        "bbox": normalize_dict(bbox),
    }


def build_condition_metadata(
    visibility="",
    validation="",
    trigger="",
    operator="",
    value=None,
    rule="",
):
    return {
        "visibility": normalize_text(visibility),
        "validation": normalize_text(validation),
        "trigger": normalize_text(trigger),
        "operator": normalize_text(operator),
        "value": value,
        "rule": normalize_text(rule),
    }


def normalize_condition_logic(value=None):
    value_dict = normalize_dict(value)
    logic = value_dict.get("logic", "AND")
    if logic not in ["AND", "OR", "NOT"]:
        logic = "AND"
    return {
        "logic": logic,
        "conditions": normalize_list(value_dict.get("conditions")),
    }


def build_condition_logic(
    applies_to=None,
    depends_on=None,
    operator="equals",
    value=None,
    action="visible",
    logic="AND",
    conditions=None,
):
    if logic not in ["AND", "OR", "NOT"]:
        logic = "AND"
    return {
        "applies_to": normalize_list(applies_to),
        "depends_on": normalize_list(depends_on),
        "operator": operator or "equals",
        "value": value,
        "action": action or "visible",
        "logic": logic,
        "conditions": normalize_list(conditions),
    }


def build_condition_logic_from_when_then(
    when=None,
    then=None,
    otherwise=None,
    applies_to=None,
    depends_on=None,
    operator="equals",
    value=None,
    action="visible",
    logic="AND",
    conditions=None,
):
    when_dict = normalize_dict(when)
    then_dict = normalize_dict(then)
    else_dict = normalize_dict(otherwise)

    normalized_depends_on = normalize_list(depends_on)
    normalized_applies_to = normalize_list(applies_to)

    if not normalized_depends_on:
        normalized_depends_on = normalize_list(
            when_dict.get("depends_on")
            or when_dict.get("field")
            or when_dict.get("field_key")
            or when_dict.get("source")
        )

    if not normalized_applies_to:
        normalized_applies_to = normalize_list(
            then_dict.get("applies_to")
            or then_dict.get("field")
            or then_dict.get("field_key")
            or then_dict.get("target")
        )

    resolved_operator = (
        when_dict.get("operator")
        or when_dict.get("op")
        or operator
        or "equals"
    )

    resolved_value = (
        when_dict.get("value")
        if "value" in when_dict
        else value
    )

    resolved_action = (
        then_dict.get("action")
        or then_dict.get("effect")
        or action
        or "visible"
    )

    merged_conditions = normalize_list(conditions)
    if not merged_conditions and when_dict:
        merged_conditions = [when_dict]

    return build_condition_logic(
        applies_to=normalized_applies_to,
        depends_on=normalized_depends_on,
        operator=resolved_operator,
        value=resolved_value,
        action=resolved_action,
        logic=logic,
        conditions=merged_conditions,
    )


def normalize_metadata(value=None):
    value_dict = normalize_dict(value)
    return build_metadata(
        origin=value_dict.get("origin", ""),
        raw=value_dict.get("raw"),
        notes=value_dict.get("notes", []),
        extra=value_dict.get("extra", {}),
    )


def normalize_semantic_summary(value=None):
    value_dict = normalize_dict(value)
    return build_semantic_summary(
        label=value_dict.get("label", ""),
        description=value_dict.get("description", ""),
        intent_type=value_dict.get("intent_type", ""),
        write_mode=value_dict.get("write_mode", ""),
        field_type=value_dict.get("field_type", ""),
        node_role=value_dict.get("node_role", ""),
        source_cell=value_dict.get("source_cell", ""),
        target_cell=value_dict.get("target_cell", ""),
    )


def normalize_visual_metadata(value=None):
    value_dict = normalize_dict(value)
    return build_visual_metadata(
        source_cell=value_dict.get("source_cell", ""),
        target_cell=value_dict.get("target_cell", ""),
        row=value_dict.get("row"),
        col=value_dict.get("col"),
        region=value_dict.get("region", ""),
        page=value_dict.get("page"),
        bbox=value_dict.get("bbox", {}),
    )


def normalize_condition_metadata(value=None):
    value_dict = normalize_dict(value)
    return build_condition_metadata(
        visibility=value_dict.get("visibility", ""),
        validation=value_dict.get("validation", ""),
        trigger=value_dict.get("trigger", ""),
        operator=value_dict.get("operator", ""),
        value=value_dict.get("value"),
        rule=value_dict.get("rule", ""),
    )


def build_node_shared_contract(
    label="",
    description="",
    field_type="",
    source_cell="",
    target_cell="",
    metadata=None,
    visual_metadata=None,
    condition_metadata=None,
    include_visual_metadata=False,
    include_condition_metadata=False,
):
    normalized_metadata = normalize_metadata(metadata)
    shared_contract = {
        "metadata": normalized_metadata,
        "semantic_summary": build_semantic_summary_from_metadata(
            label=label,
            description=description,
            field_type=field_type,
            source_cell=source_cell,
            target_cell=target_cell,
            metadata=normalized_metadata,
        ),
    }

    if include_visual_metadata:
        default_visual_metadata = build_visual_metadata(
            source_cell=source_cell,
            target_cell=target_cell,
        )
        merged_visual_metadata = {
            **default_visual_metadata,
            **normalize_dict(visual_metadata),
        }
        shared_contract["visual_metadata"] = normalize_visual_metadata(
            merged_visual_metadata
        )

    if include_condition_metadata:
        default_condition_metadata = build_condition_metadata()
        merged_condition_metadata = {
            **default_condition_metadata,
            **normalize_dict(condition_metadata),
        }
        shared_contract["condition_metadata"] = normalize_condition_metadata(
            merged_condition_metadata
        )

    return shared_contract


def build_empty_document_intelligence_model():
    return {
        "schema_version": SCHEMA_VERSION,
        "source": {
            "document_type": "",
            "template_path": "",
            "profile_id": "",
            "profile_name": "",
        },
        "nodes": {
            "fields": [],
            "sections": [],
            "tables": [],
            "choice_groups": [],
            "conditions": [],
            "objects": [],
            "visual_semantics": [],
            "runtime_policies": [],
        },
        "links": [],
        "summary": {
            "fields_count": 0,
            "sections_count": 0,
            "tables_count": 0,
            "choice_groups_count": 0,
            "conditions_count": 0,
            "objects_count": 0,
            "visual_semantics_count": 0,
            "runtime_policies_count": 0,
            "links_count": 0,
        },
        "warnings": [],
        "errors": [],
    }


def build_field_node(
    node_id,
    field_key,
    label,
    source_cell="",
    target_cell="",
    section_id="",
    field_type="text",
    required=False,
    ai_extract_hint="",
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=ai_extract_hint,
        field_type=field_type,
        source_cell=source_cell,
        target_cell=target_cell,
        metadata=metadata,
        include_visual_metadata=True,
        include_condition_metadata=True,
    )

    return {
        "node_type": NODE_TYPE_FIELD,
        "node_id": normalize_text(node_id),
        "field_key": normalize_text(field_key),
        "label": normalize_text(label),
        "source_cell": normalize_text(source_cell),
        "target_cell": normalize_text(target_cell),
        "section_id": normalize_text(section_id),
        "field_type": normalize_text(field_type),
        "required": bool(required),
        "ai_extract_hint": normalize_text(ai_extract_hint),
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_section_node(
    node_id,
    label,
    section_key="",
    bounds=None,
    parent_section_id="",
    order=0,
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=label,
        field_type="section",
        metadata=metadata,
    )

    return {
        "node_type": NODE_TYPE_SECTION,
        "node_id": normalize_text(node_id),
        "section_key": normalize_text(section_key),
        "label": normalize_text(label),
        "bounds": normalize_dict(bounds),
        "parent_section_id": normalize_text(parent_section_id),
        "order": order,
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_table_node(
    node_id,
    label,
    section_id="",
    header_cells=None,
    data_region=None,
    columns=None,
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=label,
        field_type="table",
        metadata=metadata,
        include_visual_metadata=True,
    )

    return {
        "node_type": NODE_TYPE_TABLE,
        "node_id": normalize_text(node_id),
        "label": normalize_text(label),
        "section_id": normalize_text(section_id),
        "header_cells": normalize_list(header_cells),
        "data_region": normalize_dict(data_region),
        "columns": normalize_list(columns),
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_choice_group_node(
    node_id,
    field_key,
    label,
    options=None,
    selection_mode="single",
    section_id="",
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=label,
        field_type="choice_group",
        metadata=metadata,
    )

    return {
        "node_type": NODE_TYPE_CHOICE_GROUP,
        "node_id": normalize_text(node_id),
        "field_key": normalize_text(field_key),
        "label": normalize_text(label),
        "selection_mode": normalize_text(selection_mode),
        "options": normalize_list(options),
        "section_id": normalize_text(section_id),
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_condition_node(
    node_id,
    when=None,
    then=None,
    else_=None,
    confidence=0,
    metadata=None,
    source=None,
    applies_to=None,
    depends_on=None,
    operator="equals",
    value=None,
    action="visible",
    logic="AND",
    conditions=None,
):
    shared_contract = build_node_shared_contract(
        label=node_id,
        description="condition",
        field_type="condition",
        metadata=metadata,
        condition_metadata=build_condition_metadata(trigger=node_id),
        include_condition_metadata=True,
    )

    condition_logic = build_condition_logic_from_when_then(
        when=when,
        then=then,
        otherwise=else_,
        applies_to=applies_to,
        depends_on=depends_on,
        operator=operator,
        value=value,
        action=action,
        logic=logic,
        conditions=conditions,
    )

    return {
        "node_type": NODE_TYPE_CONDITION,
        "node_id": normalize_text(node_id),
        "when": normalize_dict(when),
        "then": normalize_dict(then),
        "else": normalize_dict(else_),
        "condition_logic": condition_logic,
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_object_node(
    node_id,
    object_type,
    label="",
    cell="",
    region=None,
    section_id="",
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=object_type,
        field_type=object_type,
        source_cell=cell,
        metadata=metadata,
    )

    return {
        "node_type": NODE_TYPE_OBJECT,
        "node_id": normalize_text(node_id),
        "object_type": normalize_text(object_type),
        "label": normalize_text(label),
        "cell": normalize_text(cell),
        "region": normalize_dict(region),
        "section_id": normalize_text(section_id),
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_visual_semantic_node(
    node_id,
    semantic_type,
    label="",
    cell="",
    region=None,
    style=None,
    confidence=0,
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=label,
        description=semantic_type,
        field_type="visual",
        source_cell=cell,
        metadata=metadata,
        visual_metadata=build_visual_metadata(source_cell=cell),
        include_visual_metadata=True,
    )

    return {
        "node_type": NODE_TYPE_VISUAL,
        "node_id": normalize_text(node_id),
        "semantic_type": normalize_text(semantic_type),
        "label": normalize_text(label),
        "cell": normalize_text(cell),
        "region": normalize_dict(region),
        "style": normalize_dict(style),
        "confidence": confidence,
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_runtime_policy_node(
    node_id,
    policy_type,
    source_node_id="",
    action="",
    condition_node_id="",
    metadata=None,
    source=None,
):
    shared_contract = build_node_shared_contract(
        label=policy_type,
        description=action,
        field_type="runtime_policy",
        metadata=metadata,
        condition_metadata=build_condition_metadata(
            rule=policy_type,
            validation=action,
        ),
        include_condition_metadata=True,
    )

    return {
        "node_type": NODE_TYPE_RUNTIME_POLICY,
        "node_id": normalize_text(node_id),
        "policy_type": normalize_text(policy_type),
        "source_node_id": normalize_text(source_node_id),
        "action": normalize_text(action),
        "condition_node_id": normalize_text(condition_node_id),
        "source": _normalize_node_source(source),
        **shared_contract,
    }


def build_link(
    link_type,
    from_node_id,
    to_node_id,
    label="",
    condition_node_id="",
    metadata=None,
):
    return {
        "link_type": normalize_text(link_type),
        "from_node_id": normalize_text(from_node_id),
        "to_node_id": normalize_text(to_node_id),
        "label": normalize_text(label),
        "condition_node_id": normalize_text(condition_node_id),
        "metadata": normalize_dict(metadata),
    }


def collect_all_nodes(model):
    if not isinstance(model, dict):
        return []

    nodes = model.get("nodes")
    if not isinstance(nodes, dict):
        return []

    collected = []
    for key in NODE_COLLECTION_KEYS:
        items = nodes.get(key)
        if not isinstance(items, list):
            continue
        collected.extend(node for node in items if isinstance(node, dict))
    return collected


def refresh_document_intelligence_summary(model):
    if not isinstance(model, dict):
        return model

    nodes = model.get("nodes")
    if not isinstance(nodes, dict):
        nodes = {}

    summary = normalize_dict(model.get("summary"))
    for key in NODE_COLLECTION_KEYS:
        value = nodes.get(key)
        summary[f"{key}_count"] = len(value) if isinstance(value, list) else 0

    links = model.get("links")
    summary["links_count"] = len(links) if isinstance(links, list) else 0
    model["summary"] = summary
    return model


def validate_document_intelligence_model(model):
    warnings = []
    errors = []

    if not isinstance(model, dict):
        return {
            "valid": False,
            "warnings": warnings,
            "errors": ["model must be a dict"],
        }

    if not normalize_text(model.get("schema_version")):
        errors.append("schema_version must not be empty")

    nodes = model.get("nodes")
    if not isinstance(nodes, dict):
        errors.append("nodes must be a dict")
        nodes = {}

    node_ids = set()
    for key in NODE_COLLECTION_KEYS:
        items = nodes.get(key)
        if not isinstance(items, list):
            errors.append(f"nodes.{key} must be a list")
            continue

        for index, node in enumerate(items):
            if not isinstance(node, dict):
                warnings.append(f"nodes.{key}[{index}] must be a dict")
                continue
            if not normalize_text(node.get("node_id")):
                warnings.append(f"nodes.{key}[{index}] missing node_id")
            else:
                node_id = normalize_text(node.get("node_id"))
                if node_id in node_ids:
                    errors.append(f"duplicate node_id: {node_id}")
                node_ids.add(node_id)
            if not normalize_text(node.get("node_type")):
                warnings.append(f"nodes.{key}[{index}] missing node_type")

    links = model.get("links")
    if isinstance(links, list):
        for index, link in enumerate(links):
            if not isinstance(link, dict):
                warnings.append(f"links[{index}] must be a dict")
                continue

            link_type = normalize_text(link.get("link_type"))
            from_node_id = normalize_text(link.get("from_node_id"))
            to_node_id = normalize_text(link.get("to_node_id"))
            condition_node_id = normalize_text(link.get("condition_node_id"))

            if not link_type:
                warnings.append(f"links[{index}] missing link_type")
            if not from_node_id:
                warnings.append(f"links[{index}] missing from_node_id")
            elif from_node_id not in node_ids:
                warnings.append(f"link from_node_id not found: {from_node_id}")
            if not to_node_id:
                warnings.append(f"links[{index}] missing to_node_id")
            elif to_node_id not in node_ids:
                warnings.append(f"link to_node_id not found: {to_node_id}")
            if condition_node_id and condition_node_id not in node_ids:
                warnings.append(
                    f"link condition_node_id not found: {condition_node_id}"
                )
    else:
        warnings.append("links must be a list")

    return {
        "valid": not errors,
        "warnings": warnings,
        "errors": errors,
    }


def normalize_document_intelligence_model(model):
    if not isinstance(model, dict):
        return build_empty_document_intelligence_model()

    normalized = build_empty_document_intelligence_model()
    normalized["schema_version"] = normalize_text(
        model.get("schema_version")
    ) or normalized["schema_version"]

    normalized["source"].update(normalize_dict(model.get("source")))

    source_nodes = normalize_dict(model.get("nodes"))
    for key in NODE_COLLECTION_KEYS:
        normalized["nodes"][key] = normalize_list(source_nodes.get(key))

    normalized["links"] = [
        link for link in normalize_list(model.get("links")) if isinstance(link, dict)
    ]
    normalized["warnings"] = normalize_list(model.get("warnings"))
    normalized["errors"] = normalize_list(model.get("errors"))

    return refresh_document_intelligence_summary(normalized)
