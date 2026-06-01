"""
Build an AI extraction contract from a V4 Document Intelligence Model.

This module only maps the in-memory document model into the extraction
contract shape consumed by the existing AI parser. It does not call AI or
connect to routes, Workspace, Export, or Pipeline logic.
"""

from app.v4_document_intelligence import (
    LINK_TYPE_BELONGS_TO,
    LINK_TYPE_USES_POLICY,
    NODE_TYPE_CHOICE_GROUP,
    NODE_TYPE_FIELD,
    NODE_TYPE_RUNTIME_POLICY,
    NODE_TYPE_SECTION,
    NODE_TYPE_TABLE,
    collect_all_nodes,
    normalize_dict,
    normalize_list,
    normalize_text,
)


def _empty_contract():
    return {
        "fields": [],
        "option_groups": [],
    }


def _safe_bool(value):
    return bool(value)


def _node_type(node):
    if isinstance(node, dict):
        return normalize_text(node.get("node_type"))
    return ""


def _node_id(node):
    if isinstance(node, dict):
        return normalize_text(node.get("node_id"))
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


def _confidence(node):
    if not isinstance(node, dict):
        return 0

    try:
        return float(node.get("confidence"))
    except (TypeError, ValueError):
        return 0


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


def resolve_section_label_for_node(model, node):
    if not isinstance(node, dict):
        return ""

    section_id = normalize_text(node.get("section_id"))
    if section_id:
        section = _nodes_by_id(model).get(section_id, {})
        if isinstance(section, dict) and _node_type(section) == NODE_TYPE_SECTION:
            return normalize_text(section.get("label")) or section_id
        return section_id

    section = _find_linked_node(
        model, _node_id(node), LINK_TYPE_BELONGS_TO, NODE_TYPE_SECTION
    )
    if not isinstance(section, dict):
        return ""
    return (
        normalize_text(section.get("label"))
        or normalize_text(section.get("section_key"))
        or normalize_text(section.get("node_id"))
    )


def resolve_runtime_policy_for_node(model, node):
    if not isinstance(node, dict):
        return {}
    return _find_linked_node(
        model, _node_id(node), LINK_TYPE_USES_POLICY, NODE_TYPE_RUNTIME_POLICY
    )


def should_include_field_in_contract(node):
    if not isinstance(node, dict):
        return False
    if _node_type(node) != NODE_TYPE_FIELD:
        return False
    if not normalize_text(node.get("field_key")):
        return False

    field_type = normalize_text(node.get("field_type")).lower()
    extra = _metadata_extra(node)
    intent_type = normalize_text(extra.get("intent_type")).lower()
    write_mode = normalize_text(extra.get("write_mode")).lower()
    role = normalize_text(extra.get("role")).lower()

    if field_type in {"note", "instruction", "readonly", "visual"}:
        return False
    if intent_type in {
        "section_header",
        "note_instruction",
        "readonly_example",
        "title",
    }:
        return False
    if write_mode in {"skip", "none", "readonly"}:
        return False
    if role == "table_header":
        return False
    return True


def resolve_extract_priority(node, runtime_policy=None):
    if not isinstance(node, dict):
        return "normal"

    required = bool(node.get("required"))
    confidence = _confidence(node)
    extra = _metadata_extra(node)
    write_mode = ""
    if isinstance(runtime_policy, dict):
        write_mode = normalize_text(runtime_policy.get("action"))
    if not write_mode:
        write_mode = normalize_text(extra.get("write_mode"))
    intent_type = normalize_text(extra.get("intent_type"))

    if required:
        return "high"
    if confidence >= 0.85:
        return "high"
    if write_mode in {"check_option", "select_option_text"}:
        return "high"
    if 0 < confidence <= 0.45:
        return "low"
    if intent_type in {"note_instruction", "readonly_example", "title"}:
        return "low"
    return "normal"


def _table_columns_from_table_node(node):
    if not isinstance(node, dict):
        return []

    columns = node.get("columns")
    if not isinstance(columns, list):
        return []

    table_columns = []
    for column in columns:
        if not isinstance(column, dict):
            continue

        table_column = {
            "label": normalize_text(column.get("label")),
            "field": normalize_text(column.get("field")),
            "target_col": column.get("target_col"),
            "header_cell": normalize_text(column.get("header_cell")),
        }
        if not table_column["label"] and not table_column["field"]:
            continue
        table_columns.append(table_column)
    return table_columns


def collect_table_fields_from_document_model(model):
    if not isinstance(model, dict):
        return []

    table_fields = []
    seen_field_keys = set()
    for node in collect_all_nodes(model):
        if _node_type(node) != NODE_TYPE_TABLE:
            continue

        table_columns = _table_columns_from_table_node(node)
        if not table_columns:
            continue

        table_label = normalize_text(node.get("label")) or _node_id(node)
        field_key = normalize_text(node.get("field_key")) or _node_id(node)
        if not field_key or field_key in seen_field_keys:
            continue

        seen_field_keys.add(field_key)
        table_fields.append(
            {
                "field_key": field_key,
                "key": field_key,
                "label": table_label,
                "type": "table",
                "required": False,
                "ai_extract_hint": table_label,
                "description": table_label,
                "section": "",
                "intent_type": "table_region",
                "write_mode": "write_table_column",
                "target_cell": "",
                "source_cell": "",
                "cell": "",
                "source": "document_intelligence",
                "extract_priority": "normal",
                "table_columns": table_columns,
            }
        )
    return table_fields


def _normalize_option_value(option):
    if isinstance(option, str):
        return option.strip()
    if isinstance(option, dict):
        value = normalize_text(option.get("value"))
        if value:
            return value
        return normalize_text(option.get("label"))
    return ""


def build_ai_field_from_field_node(node, model=None):
    if not isinstance(node, dict):
        return {}

    field_key = normalize_text(node.get("field_key"))
    if not field_key:
        return {}

    summary = _semantic_summary(node)
    label = normalize_text(summary.get("label")) or normalize_text(node.get("label")) or field_key
    field_type = normalize_text(summary.get("field_type")) or normalize_text(node.get("field_type")) or "text"
    required = _safe_bool(node.get("required"))
    ai_extract_hint = (
        normalize_text(summary.get("description"))
        or normalize_text(node.get("ai_extract_hint"))
        or label
    )
    if isinstance(model, dict):
        section = resolve_section_label_for_node(model, node)
        runtime_policy = resolve_runtime_policy_for_node(model, node)
    else:
        section = normalize_text(node.get("section_id"))
        runtime_policy = {}

    metadata_extra = _metadata_extra(node)
    intent_type = normalize_text(summary.get("intent_type")) or normalize_text(metadata_extra.get("intent_type"))
    write_mode = ""
    runtime_policy_id = ""
    if isinstance(runtime_policy, dict) and runtime_policy:
        runtime_policy_id = normalize_text(runtime_policy.get("node_id"))
        write_mode = normalize_text(runtime_policy.get("action")) or normalize_text(
            runtime_policy.get("policy_type")
        )
    if not write_mode:
        write_mode = normalize_text(summary.get("write_mode")) or normalize_text(metadata_extra.get("write_mode"))

    target_cell = normalize_text(node.get("target_cell"))
    source_cell = normalize_text(node.get("source_cell"))
    cell = target_cell or source_cell

    return {
        "field_key": field_key,
        "key": field_key,
        "label": label,
        "type": field_type,
        "required": required,
        "ai_extract_hint": ai_extract_hint,
        "description": ai_extract_hint,
        "section": section,
        "intent_type": intent_type,
        "write_mode": write_mode,
        "target_cell": target_cell,
        "source_cell": source_cell,
        "cell": cell,
        "source": "document_intelligence",
        "runtime_policy_id": runtime_policy_id,
        "extract_priority": resolve_extract_priority(
            node, runtime_policy=runtime_policy
        ),
    }


def build_option_metadata(option):
    if not isinstance(option, dict):
        return {}

    return {
        "label": normalize_text(option.get("label")),
        "value": normalize_text(option.get("value")),
        "source_cell": normalize_text(option.get("source_cell")),
        "target_cell": normalize_text(option.get("target_cell")),
        "write_mode": normalize_text(option.get("write_mode")),
        "intent_type": normalize_text(option.get("intent_type")),
        "confidence": option.get("confidence"),
    }


def build_option_group_from_choice_group_node(node):
    if not isinstance(node, dict):
        return {}

    field_key = normalize_text(node.get("field_key"))
    if not field_key:
        return {}

    summary = _semantic_summary(node)
    label = normalize_text(summary.get("label")) or normalize_text(node.get("label")) or field_key
    options = []
    option_metadata = []
    seen_options = set()
    for option in normalize_list(node.get("options")):
        metadata = build_option_metadata(option)
        if metadata:
            option_metadata.append(metadata)

        option_value = _normalize_option_value(option)
        if not option_value or option_value in seen_options:
            continue
        seen_options.add(option_value)
        options.append(option_value)

    return {
        "field_key": field_key,
        "label": label,
        "options": options,
        "option_metadata": option_metadata,
    }


def _append_unique_by_field_key(items, item, seen_keys):
    if not isinstance(item, dict):
        return

    field_key = normalize_text(item.get("field_key"))
    if not field_key or field_key in seen_keys:
        return

    seen_keys.add(field_key)
    items.append(item)


def build_ai_extraction_contract_from_document_model(model):
    if not isinstance(model, dict):
        return _empty_contract()

    fields = []
    option_groups = []
    seen_field_keys = set()
    seen_option_group_keys = set()

    for node in collect_all_nodes(model):
        node_type = _node_type(node)
        if node_type == NODE_TYPE_FIELD:
            if not should_include_field_in_contract(node):
                continue
            _append_unique_by_field_key(
                fields,
                build_ai_field_from_field_node(node, model=model),
                seen_field_keys,
            )
        elif node_type == NODE_TYPE_CHOICE_GROUP:
            _append_unique_by_field_key(
                option_groups,
                build_option_group_from_choice_group_node(node),
                seen_option_group_keys,
            )

    for table_field in collect_table_fields_from_document_model(model):
        _append_unique_by_field_key(fields, table_field, seen_field_keys)

    options_by_field_key = {
        option_group["field_key"]: option_group.get("options", [])
        for option_group in option_groups
        if isinstance(option_group, dict)
    }
    for field in fields:
        field_key = normalize_text(field.get("field_key"))
        if field_key in options_by_field_key:
            field["options"] = normalize_list(options_by_field_key.get(field_key))

    return {
        "fields": fields,
        "option_groups": option_groups,
    }
