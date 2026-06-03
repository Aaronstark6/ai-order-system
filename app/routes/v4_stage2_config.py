from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app.runtime_paths import get_base_dir
from app.v4_stage2_config_schema import STAGE2_CONFIG_SCHEMA_VERSION
from app.v4_stage2_config_store import (
    create_stage2_config_profile,
    get_stage2_config_profile,
    load_stage2_config_profiles,
    upsert_stage2_config_profile,
)


router = APIRouter(prefix="/api/v4/stage2-config")


def _read_json_file(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _count_profile_data(data: Any) -> int:
    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        profiles = data.get("profiles")
        if isinstance(profiles, list):
            return len(profiles)
        return len(data)
    return 0


def _profile_source_summary(relative_path: str, note: str | None = None) -> dict[str, Any]:
    path = get_base_dir() / relative_path
    summary: dict[str, Any] = {
        "exists": path.is_file(),
        "count": 0,
        "path": relative_path,
    }
    if note:
        summary["note"] = note
    if not path.is_file():
        return summary
    try:
        summary["count"] = _count_profile_data(_read_json_file(path))
    except Exception as exc:
        summary["error"] = str(exc)
    return summary


def _rule_items_from_data(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        rules = data.get("rules")
        if isinstance(rules, list):
            return rules
    return []


def _rule_label(rule: Any) -> str:
    if not isinstance(rule, dict):
        return ""
    source = rule.get("source")
    if isinstance(source, dict):
        source_label = str(source.get("description_field") or "").strip()
        if source_label:
            return source_label
    for key in ("label", "field_label", "name", "title", "field_key"):
        value = str(rule.get(key) or "").strip()
        if value:
            return value
    return ""


def _rule_target_cell(rule: Any) -> str:
    if not isinstance(rule, dict):
        return ""
    target = rule.get("target")
    if isinstance(target, dict):
        for key in ("cell", "target_cell", "range"):
            value = str(target.get(key) or "").strip()
            if value:
                return value
    for key in ("target_cell", "cell", "range"):
        value = str(rule.get(key) or "").strip()
        if value:
            return value
    return ""


def _cache_item_summary(cache_dir: Path) -> dict[str, Any]:
    item: dict[str, Any] = {
        "cache_id": cache_dir.name,
        "has_meta": False,
        "has_rules": False,
        "meta_keys": [],
        "rules_count": 0,
        "rule_labels": [],
    }
    errors = []

    meta_path = cache_dir / "meta.json"
    item["has_meta"] = meta_path.is_file()
    if meta_path.is_file():
        try:
            meta_data = _read_json_file(meta_path)
            if isinstance(meta_data, dict):
                item["meta_keys"] = sorted(str(key) for key in meta_data.keys())
        except Exception as exc:
            errors.append(f"meta.json: {exc}")

    rules_path = cache_dir / "rules.json"
    item["has_rules"] = rules_path.is_file()
    if rules_path.is_file():
        try:
            rules_data = _read_json_file(rules_path)
            rules = _rule_items_from_data(rules_data)
            item["rules_count"] = len(rules)
            item["rule_labels"] = [
                label for label in (_rule_label(rule) for rule in rules)
                if label
            ][:30]
        except Exception as exc:
            errors.append(f"rules.json: {exc}")

    if errors:
        item["error"] = "; ".join(errors)
    return item


def _template_cache_summary() -> dict[str, Any]:
    cache_root = get_base_dir() / "data" / "v4_template_cache"
    summary: dict[str, Any] = {
        "exists": cache_root.is_dir(),
        "template_count": 0,
        "items": [],
    }
    if not cache_root.is_dir():
        return summary
    try:
        cache_dirs = sorted(
            (path for path in cache_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )
        summary["template_count"] = len(cache_dirs)
        summary["items"] = [_cache_item_summary(path) for path in cache_dirs]
    except Exception as exc:
        summary["error"] = str(exc)
    return summary


def _load_legacy_profile_items() -> tuple[list[dict[str, Any]], str | None]:
    path = get_base_dir() / "data" / "template_profiles.json"
    if not path.is_file():
        return [], None
    try:
        data = _read_json_file(path)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)], None
        if isinstance(data, dict):
            profiles = data.get("profiles")
            if isinstance(profiles, list):
                return [item for item in profiles if isinstance(item, dict)], None
            return [item for item in data.values() if isinstance(item, dict)], None
        return [], "template_profiles.json root is not list or dict"
    except Exception as exc:
        return [], str(exc)


def _semantic_field_count(schema: Any) -> int:
    if isinstance(schema, list):
        return len(schema)
    if isinstance(schema, dict):
        fields = schema.get("fields")
        if isinstance(fields, list):
            return len(fields)
    return 0


def _legacy_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    semantic_schema = profile.get("semantic_workspace_schema")
    workspace_fields = profile.get("workspace_fields")
    field_bound_operations = profile.get("field_bound_operations")
    return {
        "profile_id": str(profile.get("profile_id") or profile.get("id") or "").strip(),
        "profile_name": str(profile.get("profile_name") or profile.get("name") or "").strip(),
        "template_filename": str(
            profile.get("template_filename")
            or profile.get("template_file")
            or profile.get("filename")
            or profile.get("template_display_name")
            or ""
        ).strip(),
        "template_path": str(
            profile.get("template_file_path")
            or profile.get("template_path")
            or profile.get("template_file")
            or ""
        ).strip(),
        "has_semantic_workspace_schema": semantic_schema is not None,
        "semantic_workspace_schema_type": type(semantic_schema).__name__ if semantic_schema is not None else "missing",
        "semantic_workspace_schema_field_count": _semantic_field_count(semantic_schema),
        "has_workspace_fields": isinstance(workspace_fields, list),
        "workspace_fields_count": len(workspace_fields) if isinstance(workspace_fields, list) else 0,
        "has_field_bound_operations": isinstance(field_bound_operations, list),
        "field_bound_operations_count": len(field_bound_operations) if isinstance(field_bound_operations, list) else 0,
        "top_level_keys": sorted(str(key) for key in profile.keys()),
    }


def _possible_template_path(meta_data: Any) -> str:
    if not isinstance(meta_data, dict):
        return ""
    for key in ("template_path", "template_file_path", "source_path", "template_file"):
        value = str(meta_data.get(key) or "").strip()
        if value:
            return value
    return ""


def _possible_template_filename(meta_data: Any) -> str:
    if not isinstance(meta_data, dict):
        return ""
    for key in ("template_filename", "template_file", "filename", "template_name"):
        value = str(meta_data.get(key) or "").strip()
        if value:
            return value
    return ""


def _rules_summary(cache_dir: Path) -> dict[str, Any]:
    rules_path = cache_dir / "rules.json"
    if not rules_path.is_file():
        return {
            "rules_type": "missing",
            "rules_count": 0,
            "rule_labels": [],
            "rule_target_cells": [],
        }
    try:
        rules_data = _read_json_file(rules_path)
        if isinstance(rules_data, list):
            rules_type = "list"
        elif isinstance(rules_data, dict):
            rules_type = "dict"
        else:
            rules_type = type(rules_data).__name__
        rules = _rule_items_from_data(rules_data)
        return {
            "rules_type": rules_type,
            "rules_count": len(rules),
            "rule_labels": [
                label for label in (_rule_label(rule) for rule in rules)
                if label
            ][:30],
            "rule_target_cells": [
                cell for cell in (_rule_target_cell(rule) for rule in rules)
                if cell
            ][:30],
        }
    except Exception as exc:
        return {
            "rules_type": "error",
            "rules_count": 0,
            "rule_labels": [],
            "rule_target_cells": [],
            "error": str(exc),
        }


def _template_analysis_cache_summary() -> list[dict[str, Any]]:
    cache_root = get_base_dir() / "data" / "v4_template_cache"
    if not cache_root.is_dir():
        return []
    items = []
    try:
        cache_dirs = sorted(
            (path for path in cache_root.iterdir() if path.is_dir()),
            key=lambda path: path.name,
        )
    except Exception as exc:
        return [{
            "cache_id": "",
            "has_meta": False,
            "has_rules": False,
            "meta_summary": {
                "top_level_keys": [],
                "possible_template_path": "",
                "possible_template_filename": "",
            },
            "rules_summary": {
                "rules_type": "error",
                "rules_count": 0,
                "rule_labels": [],
                "rule_target_cells": [],
                "error": str(exc),
            },
        }]

    for cache_dir in cache_dirs:
        meta_path = cache_dir / "meta.json"
        has_meta = meta_path.is_file()
        meta_summary = {
            "top_level_keys": [],
            "possible_template_path": "",
            "possible_template_filename": "",
        }
        item_error = ""
        if has_meta:
            try:
                meta_data = _read_json_file(meta_path)
                if isinstance(meta_data, dict):
                    meta_summary = {
                        "top_level_keys": sorted(str(key) for key in meta_data.keys()),
                        "possible_template_path": _possible_template_path(meta_data),
                        "possible_template_filename": _possible_template_filename(meta_data),
                    }
            except Exception as exc:
                item_error = f"meta.json: {exc}"
        item = {
            "cache_id": cache_dir.name,
            "has_meta": has_meta,
            "has_rules": (cache_dir / "rules.json").is_file(),
            "meta_summary": meta_summary,
            "rules_summary": _rules_summary(cache_dir),
        }
        if item_error:
            item["error"] = item_error
        items.append(item)
    return items


def _template_analysis_diagnosis(legacy_profiles: list[dict[str, Any]], template_cache: list[dict[str, Any]]) -> dict[str, Any]:
    profiles_with_semantic_schema = sum(
        1 for profile in legacy_profiles
        if int(profile.get("semantic_workspace_schema_field_count") or 0) > 0
    )
    profiles_with_workspace_fields = sum(
        1 for profile in legacy_profiles
        if int(profile.get("workspace_fields_count") or 0) > 0
    )
    profiles_with_field_bound_operations = sum(
        1 for profile in legacy_profiles
        if int(profile.get("field_bound_operations_count") or 0) > 0
    )
    total_cache_rules = sum(
        int((item.get("rules_summary") or {}).get("rules_count") or 0)
        for item in template_cache
    )
    if profiles_with_semantic_schema == 0 and total_cache_rules <= 10:
        likely_issue = "semantic_workspace_schema_missing_and_cache_rules_too_few"
    elif profiles_with_semantic_schema > 0 and profiles_with_workspace_fields == 0:
        likely_issue = "semantic_schema_exists_but_workspace_fields_missing"
    elif profiles_with_workspace_fields > 0 and profiles_with_field_bound_operations == 0:
        likely_issue = "workspace_fields_exist_but_field_bound_operations_missing"
    else:
        likely_issue = "needs_manual_review"
    return {
        "legacy_profile_count": len(legacy_profiles),
        "cache_count": len(template_cache),
        "profiles_with_semantic_schema": profiles_with_semantic_schema,
        "profiles_with_workspace_fields": profiles_with_workspace_fields,
        "profiles_with_field_bound_operations": profiles_with_field_bound_operations,
        "total_cache_rules": total_cache_rules,
        "likely_issue": likely_issue,
    }


DOCUMENTMODEL_VIEWER_MAX_NODES = 200


def _string_value(value: Any) -> str:
    return str(value or "").strip()


def _mapping_value(data: Any, keys: tuple[str, ...]) -> Any:
    if not isinstance(data, dict):
        return None
    for key in keys:
        if key in data and data.get(key) not in (None, ""):
            return data.get(key)
    return None


def _nested_mapping_value(data: Any, path: tuple[str, ...]) -> Any:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _documentmodel_nodes_from_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if not isinstance(value, dict):
        return []
    for key in ("nodes", "semantic_nodes", "fields", "document_nodes"):
        nodes = value.get(key)
        if isinstance(nodes, list):
            return nodes
    return []


def _legacy_profile_documentmodel_candidates() -> list[dict[str, Any]]:
    profiles, _ = _load_legacy_profile_items()
    candidates = []
    for profile in profiles:
        profile_id = _string_value(profile.get("profile_id") or profile.get("id"))
        source_id = profile_id or _string_value(profile.get("profile_name") or profile.get("name"))
        template_path = _string_value(
            profile.get("template_file_path")
            or profile.get("template_path")
            or profile.get("template_file")
        )
        template_filename = _string_value(
            profile.get("template_filename")
            or profile.get("template_file")
            or profile.get("filename")
            or profile.get("template_display_name")
        )
        for key in ("document_model", "DocumentModel", "documentModel"):
            if key in profile:
                candidates.append({
                    "status": "available",
                    "source_type": f"legacy_profile_{key}",
                    "source_id": source_id,
                    "template_path": template_path,
                    "template_filename": template_filename,
                    "nodes": _documentmodel_nodes_from_value(profile.get(key)),
                    "diagnostics": [],
                })
        for key in ("nodes", "semantic_nodes"):
            nodes = profile.get(key)
            if isinstance(nodes, list):
                candidates.append({
                    "status": "partial",
                    "source_type": f"legacy_profile_{key}",
                    "source_id": source_id,
                    "template_path": template_path,
                    "template_filename": template_filename,
                    "nodes": nodes,
                    "diagnostics": ["document_model_wrapper_not_found"],
                })
    return candidates


def _cache_documentmodel_candidates() -> list[dict[str, Any]]:
    cache_root = get_base_dir() / "data" / "v4_template_cache"
    if not cache_root.is_dir():
        return []
    candidates = []
    for cache_dir in sorted((path for path in cache_root.iterdir() if path.is_dir()), key=lambda path: path.name):
        for filename in ("meta.json", "rules.json"):
            path = cache_dir / filename
            if not path.is_file():
                continue
            try:
                data = _read_json_file(path)
            except Exception as exc:
                candidates.append({
                    "status": "unavailable",
                    "source_type": f"cache_{filename}_error",
                    "source_id": cache_dir.name,
                    "template_path": "",
                    "template_filename": "",
                    "nodes": [],
                    "diagnostics": [str(exc)],
                })
                continue
            template_path = _possible_template_path(data)
            template_filename = _possible_template_filename(data)
            for key in ("document_model", "DocumentModel", "documentModel"):
                if isinstance(data, dict) and key in data:
                    candidates.append({
                        "status": "available",
                        "source_type": f"cache_{filename}_{key}",
                        "source_id": cache_dir.name,
                        "template_path": template_path,
                        "template_filename": template_filename,
                        "nodes": _documentmodel_nodes_from_value(data.get(key)),
                        "diagnostics": [],
                    })
            for key in ("nodes", "semantic_nodes"):
                nodes = data.get(key) if isinstance(data, dict) else None
                if isinstance(nodes, list):
                    candidates.append({
                        "status": "partial",
                        "source_type": f"cache_{filename}_{key}",
                        "source_id": cache_dir.name,
                        "template_path": template_path,
                        "template_filename": template_filename,
                        "nodes": nodes,
                        "diagnostics": ["document_model_wrapper_not_found"],
                    })
    return candidates


def _diagnostic_rule_nodes_from_cache() -> tuple[list[dict[str, Any]], dict[str, str]]:
    cache_root = get_base_dir() / "data" / "v4_template_cache"
    if not cache_root.is_dir():
        return [], {"source_id": "", "template_path": "", "template_filename": ""}
    nodes = []
    source_info = {"source_id": "", "template_path": "", "template_filename": ""}
    for cache_dir in sorted((path for path in cache_root.iterdir() if path.is_dir()), key=lambda path: path.name):
        meta_path = cache_dir / "meta.json"
        if meta_path.is_file():
            try:
                meta_data = _read_json_file(meta_path)
                if not source_info["template_path"]:
                    source_info["template_path"] = _possible_template_path(meta_data)
                if not source_info["template_filename"]:
                    source_info["template_filename"] = _possible_template_filename(meta_data)
            except Exception:
                pass
        rules_path = cache_dir / "rules.json"
        if not rules_path.is_file():
            continue
        try:
            rules = _rule_items_from_data(_read_json_file(rules_path))
        except Exception:
            continue
        if rules and not source_info["source_id"]:
            source_info["source_id"] = cache_dir.name
        for index, rule in enumerate(rules, start=1):
            rule_id = _string_value(rule.get("id") if isinstance(rule, dict) else "")
            label = _rule_label(rule)
            source = rule.get("source") if isinstance(rule, dict) else {}
            target = rule.get("target") if isinstance(rule, dict) else {}
            field_key = _string_value(rule.get("field_key") if isinstance(rule, dict) else "")
            if not field_key and isinstance(source, dict):
                field_key = _string_value(source.get("field_key") or source.get("description_field"))
            nodes.append({
                "node_id": rule_id or f"{cache_dir.name}.rule.{index}",
                "node_type": "cache_rule_diagnostic",
                "label": label or field_key or rule_id or f"Rule {index}",
                "field_key": field_key,
                "intent_type": _string_value(rule.get("type") if isinstance(rule, dict) else ""),
                "write_mode": "diagnostic_read_only",
                "target": target if isinstance(target, dict) else {},
                "coordinates": {},
                "semantic_summary": {
                    "source_type": "cache_rules_diagnostic_only",
                    "source": source if isinstance(source, dict) else {},
                },
            })
    return nodes, source_info


def _normalize_documentmodel_node(node: Any, index: int) -> dict[str, Any]:
    node_data = node if isinstance(node, dict) else {"value": node}
    visual_logic = node_data.get("visual_logic") if isinstance(node_data.get("visual_logic"), dict) else {}
    target = (
        _mapping_value(node_data, ("target",))
        or _nested_mapping_value(node_data, ("visual_logic", "target"))
        or _nested_mapping_value(node_data, ("visual_logic", "coordinates"))
        or _mapping_value(node_data, ("coordinates",))
        or _mapping_value(node_data, ("target_cell", "cell"))
        or {}
    )
    coordinates = (
        _mapping_value(node_data, ("coordinates",))
        or _nested_mapping_value(node_data, ("visual_logic", "coordinates"))
        or _nested_mapping_value(node_data, ("target", "coordinates"))
        or {}
    )
    semantic_summary = (
        _mapping_value(node_data, ("semantic_summary", "summary", "semantic"))
        or {}
    )
    normalized = {
        "node_id": _string_value(_mapping_value(node_data, ("node_id", "id", "key", "field_key")) or f"node_{index}"),
        "node_type": _string_value(_mapping_value(node_data, ("node_type", "type", "intent_type"))),
        "label": _string_value(_mapping_value(node_data, ("label", "field_label", "title", "name", "text", "field_key"))),
        "field_key": _string_value(_mapping_value(node_data, ("field_key", "key"))),
        "intent_type": _string_value(_mapping_value(node_data, ("intent_type", "intent"))),
        "write_mode": _string_value(_mapping_value(node_data, ("write_mode", "mode"))),
        "target": target if isinstance(target, dict) else {"value": target},
        "coordinates": coordinates if isinstance(coordinates, dict) else {"value": coordinates},
        "semantic_summary": semantic_summary if isinstance(semantic_summary, dict) else {"value": semantic_summary},
        "has_visual_logic": bool(visual_logic or coordinates or target),
        "has_condition_logic": bool(node_data.get("condition_logic")),
        "has_choice_logic": bool(node_data.get("choice_logic")),
        "has_table_logic": bool(node_data.get("table_logic")),
        "has_runtime_policy": bool(node_data.get("runtime_policy")),
    }
    if not normalized["label"]:
        normalized["label"] = normalized["field_key"] or normalized["node_id"]
    return normalized


def _documentmodel_viewer_stats(nodes: list[dict[str, Any]]) -> dict[str, int]:
    stats = {
        "node_count": len(nodes),
        "field_node_count": 0,
        "choice_node_count": 0,
        "table_node_count": 0,
        "section_node_count": 0,
        "visual_node_count": 0,
        "unknown_node_count": 0,
    }
    for node in nodes:
        node_type = _string_value(node.get("node_type")).lower()
        is_field = "field" in node_type or bool(node.get("field_key"))
        is_choice = "choice" in node_type
        is_table = "table" in node_type
        is_section = any(token in node_type for token in ("section", "header", "title"))
        is_visual = bool(node.get("has_visual_logic") or node.get("coordinates") or node.get("target"))
        stats["field_node_count"] += int(is_field)
        stats["choice_node_count"] += int(is_choice)
        stats["table_node_count"] += int(is_table)
        stats["section_node_count"] += int(is_section)
        stats["visual_node_count"] += int(is_visual)
        if not any((is_field, is_choice, is_table, is_section, is_visual)):
            stats["unknown_node_count"] += 1
    return stats


def _build_documentmodel_viewer() -> dict[str, Any]:
    candidates = _legacy_profile_documentmodel_candidates() + _cache_documentmodel_candidates()
    selected = next((candidate for candidate in candidates if candidate.get("nodes")), None)
    selected = selected or next((candidate for candidate in candidates if candidate.get("status") != "unavailable"), None)
    if selected:
        raw_nodes = list(selected.get("nodes") or [])[:DOCUMENTMODEL_VIEWER_MAX_NODES]
        nodes = [_normalize_documentmodel_node(node, index) for index, node in enumerate(raw_nodes, start=1)]
        diagnostics = list(selected.get("diagnostics") or [])
        if not nodes:
            diagnostics.append("document_model_found_but_nodes_missing")
        if len(selected.get("nodes") or []) > DOCUMENTMODEL_VIEWER_MAX_NODES:
            diagnostics.append("node_list_truncated_to_200")
        viewer = {
            "status": selected.get("status") or "partial",
            "source_type": selected.get("source_type") or "",
            "source_id": selected.get("source_id") or "",
            "template_path": selected.get("template_path") or "",
            "template_filename": selected.get("template_filename") or "",
            "nodes": nodes,
            "diagnostics": diagnostics,
        }
        viewer.update(_documentmodel_viewer_stats(nodes))
        return viewer

    diagnostic_nodes, source_info = _diagnostic_rule_nodes_from_cache()
    if diagnostic_nodes:
        nodes = [
            _normalize_documentmodel_node(node, index)
            for index, node in enumerate(diagnostic_nodes[:DOCUMENTMODEL_VIEWER_MAX_NODES], start=1)
        ]
        diagnostics = ["document_model_not_found", "rules_json_is_not_document_model"]
        if len(diagnostic_nodes) > DOCUMENTMODEL_VIEWER_MAX_NODES:
            diagnostics.append("node_list_truncated_to_200")
        viewer = {
            "status": "partial",
            "source_type": "cache_rules_diagnostic_only",
            "source_id": source_info.get("source_id") or "",
            "template_path": source_info.get("template_path") or "",
            "template_filename": source_info.get("template_filename") or "",
            "nodes": nodes,
            "diagnostics": diagnostics,
        }
        viewer.update(_documentmodel_viewer_stats(nodes))
        return viewer

    viewer = {
        "status": "unavailable",
        "source_type": "",
        "source_id": "",
        "template_path": "",
        "template_filename": "",
        "nodes": [],
        "diagnostics": [
            "document_model_not_found",
            "stage2_config_not_yet_connected_to_template_analysis",
        ],
    }
    viewer.update(_documentmodel_viewer_stats([]))
    return viewer


def _empty_documentmodel_runtime(
    status: str,
    diagnostics: list[str] | None = None,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source = source if isinstance(source, dict) else {}
    runtime = {
        "status": status,
        "source_type": source.get("source_type") or "",
        "source_id": source.get("source_id") or "",
        "template_filename": source.get("template_filename") or "",
        "template_path": source.get("template_path") or "",
        "template_analysis_source": source.get("template_analysis_source") or "",
        "template_analysis_keys": source.get("template_analysis_keys") or [],
        "semantic_regions_count": int(source.get("semantic_regions_count") or 0),
        "document_model_type": "",
        "summary": {},
        "nodes": [],
        "diagnostics": diagnostics or [],
    }
    runtime.update(_documentmodel_viewer_stats([]))
    return runtime


def _pipeline_state_template_analysis_source() -> dict[str, Any]:
    diagnostics = []
    try:
        from app.v4_pipeline_state import get_pipeline_state
    except Exception as exc:
        return {
            "template_analysis": {},
            "source": {
                "source_type": "pipeline_state",
                "source_id": "",
                "template_filename": "",
                "template_path": "",
                "template_analysis_source": "pipeline_state.template_analysis",
                "template_analysis_keys": [],
                "semantic_regions_count": 0,
            },
            "diagnostics": [f"pipeline_state_import_failed: {exc}"],
        }

    try:
        state = get_pipeline_state()
    except Exception as exc:
        return {
            "template_analysis": {},
            "source": {
                "source_type": "pipeline_state",
                "source_id": "",
                "template_filename": "",
                "template_path": "",
                "template_analysis_source": "pipeline_state.template_analysis",
                "template_analysis_keys": [],
                "semantic_regions_count": 0,
            },
            "diagnostics": [f"pipeline_state_read_failed: {exc}"],
        }

    state = state if isinstance(state, dict) else {}
    profile = state.get("current_profile") if isinstance(state.get("current_profile"), dict) else {}
    template_analysis = state.get("template_analysis") if isinstance(state.get("template_analysis"), dict) else {}
    semantic_regions = template_analysis.get("semantic_regions") if isinstance(template_analysis, dict) else None
    source = {
        "source_type": "pipeline_state",
        "source_id": _string_value(profile.get("profile_id") or profile.get("id")),
        "template_filename": _string_value(
            profile.get("template_filename")
            or profile.get("template_file")
            or profile.get("template_name")
        ),
        "template_path": _string_value(
            state.get("current_template_path")
            or profile.get("template_file_path")
            or profile.get("template_path")
            or profile.get("template_file")
        ),
        "template_analysis_source": "pipeline_state.template_analysis",
        "template_analysis_keys": sorted(str(key) for key in template_analysis.keys()) if isinstance(template_analysis, dict) else [],
        "semantic_regions_count": len(semantic_regions) if isinstance(semantic_regions, list) else 0,
    }
    if not template_analysis:
        diagnostics.append("pipeline_state_template_analysis_empty")
    elif not isinstance(semantic_regions, list):
        diagnostics.append("template_analysis_semantic_regions_missing")
    elif not semantic_regions:
        diagnostics.append("template_analysis_semantic_regions_empty")
    return {
        "template_analysis": template_analysis,
        "source": source,
        "diagnostics": diagnostics,
    }


def _legacy_template_analysis_sources() -> list[dict[str, Any]]:
    profiles, profile_error = _load_legacy_profile_items()
    sources = []
    if profile_error:
        sources.append({
            "template_analysis": {},
            "source": {
                "source_type": "legacy_template_profiles",
                "source_id": "",
                "template_filename": "",
                "template_path": "",
                "template_analysis_source": "legacy_template_profiles_error",
                "template_analysis_keys": [],
                "semantic_regions_count": 0,
            },
            "diagnostics": [f"legacy_template_profiles_read_failed: {profile_error}"],
        })
    for profile in profiles:
        template_analysis = profile.get("template_analysis") if isinstance(profile.get("template_analysis"), dict) else {}
        semantic_regions = template_analysis.get("semantic_regions") if isinstance(template_analysis, dict) else None
        if not template_analysis:
            continue
        sources.append({
            "template_analysis": template_analysis,
            "source": {
                "source_type": "legacy_template_profiles",
                "source_id": _string_value(profile.get("profile_id") or profile.get("id")),
                "template_filename": _string_value(
                    profile.get("template_filename")
                    or profile.get("template_file")
                    or profile.get("filename")
                    or profile.get("template_display_name")
                ),
                "template_path": _string_value(
                    profile.get("template_file_path")
                    or profile.get("template_path")
                    or profile.get("template_file")
                ),
                "template_analysis_source": "legacy_template_profiles.template_analysis",
                "template_analysis_keys": sorted(str(key) for key in template_analysis.keys()),
                "semantic_regions_count": len(semantic_regions) if isinstance(semantic_regions, list) else 0,
            },
            "diagnostics": [] if isinstance(semantic_regions, list) and semantic_regions else ["template_analysis_semantic_regions_missing_or_empty"],
        })
    return sources


def _cache_runtime_source_hint() -> dict[str, Any]:
    cache_root = get_base_dir() / "data" / "v4_template_cache"
    if not cache_root.is_dir():
        return {}
    for cache_dir in sorted((path for path in cache_root.iterdir() if path.is_dir()), key=lambda path: path.name):
        meta_path = cache_dir / "meta.json"
        meta_data = {}
        if meta_path.is_file():
            try:
                loaded_meta = _read_json_file(meta_path)
                meta_data = loaded_meta if isinstance(loaded_meta, dict) else {}
            except Exception:
                meta_data = {}
        return {
            "source_type": "cache_rules_diagnostic_only",
            "source_id": cache_dir.name,
            "template_filename": _possible_template_filename(meta_data),
            "template_path": _possible_template_path(meta_data),
            "template_analysis_source": "",
            "template_analysis_keys": [],
            "semantic_regions_count": 0,
        }
    return {}


def _select_template_analysis_for_runtime() -> dict[str, Any]:
    candidates = [_pipeline_state_template_analysis_source()]
    candidates.extend(_legacy_template_analysis_sources())
    diagnostics = []
    source_hint: dict[str, Any] = {}
    for candidate in candidates:
        source = candidate.get("source") if isinstance(candidate.get("source"), dict) else {}
        if not source_hint and source:
            source_hint = source
        diagnostics.extend(candidate.get("diagnostics") or [])
        analysis = candidate.get("template_analysis") if isinstance(candidate.get("template_analysis"), dict) else {}
        semantic_regions = analysis.get("semantic_regions") if isinstance(analysis, dict) else None
        if isinstance(semantic_regions, list) and semantic_regions:
            return {
                "template_analysis": analysis,
                "source": source,
                "diagnostics": diagnostics,
            }
    if not source_hint:
        source_hint = _cache_runtime_source_hint()
    diagnostics.append("template_analysis_not_available_for_document_model_builder")
    return {
        "template_analysis": {},
        "source": source_hint,
        "diagnostics": diagnostics,
    }


def _model_to_dict(document_model: Any) -> dict[str, Any]:
    if isinstance(document_model, dict):
        return document_model
    if is_dataclass(document_model):
        try:
            value = asdict(document_model)
            return value if isinstance(value, dict) else {}
        except Exception:
            return {}
    attrs = {}
    for key in ("nodes", "summary", "warnings", "errors", "source", "schema_version"):
        if hasattr(document_model, key):
            attrs[key] = getattr(document_model, key)
    return attrs


def _document_model_nodes(document_model: Any) -> list[Any]:
    try:
        from app.v4_document_intelligence import collect_all_nodes
        collected = collect_all_nodes(document_model)
        if collected:
            return collected
    except Exception:
        pass
    model = _model_to_dict(document_model)
    nodes = model.get("nodes")
    if isinstance(nodes, list):
        return nodes
    if isinstance(nodes, dict):
        collected = []
        for value in nodes.values():
            if isinstance(value, list):
                collected.extend(item for item in value if isinstance(item, dict))
        return collected
    nodes_attr = getattr(document_model, "nodes", None)
    return nodes_attr if isinstance(nodes_attr, list) else []


def _document_model_summary(document_model: Any) -> dict[str, Any]:
    model = _model_to_dict(document_model)
    summary = model.get("summary")
    if isinstance(summary, dict):
        return summary
    summary_attr = getattr(document_model, "summary", None)
    return summary_attr if isinstance(summary_attr, dict) else {}


def _build_documentmodel_runtime() -> dict[str, Any]:
    selected = _select_template_analysis_for_runtime()
    template_analysis = selected.get("template_analysis") if isinstance(selected.get("template_analysis"), dict) else {}
    source = selected.get("source") if isinstance(selected.get("source"), dict) else {}
    diagnostics = list(selected.get("diagnostics") or [])
    semantic_regions = template_analysis.get("semantic_regions") if isinstance(template_analysis, dict) else None
    if not isinstance(semantic_regions, list) or not semantic_regions:
        diagnostics.append("formal_template_analysis_required")
        diagnostics.append("cache_rules_are_not_document_model")
        return _empty_documentmodel_runtime("unavailable", diagnostics, source)

    try:
        from app.v4_document_intelligence_builder import build_document_intelligence_model
        document_model = build_document_intelligence_model(template_analysis)
    except Exception as exc:
        diagnostics.append(f"build_document_intelligence_model_failed: {exc}")
        return _empty_documentmodel_runtime("error", diagnostics, source)

    document_model_dict = _model_to_dict(document_model)
    raw_nodes = _document_model_nodes(document_model)
    nodes = [
        _normalize_documentmodel_node(node, index)
        for index, node in enumerate(raw_nodes[:DOCUMENTMODEL_VIEWER_MAX_NODES], start=1)
    ]
    if len(raw_nodes) > DOCUMENTMODEL_VIEWER_MAX_NODES:
        diagnostics.append("node_list_truncated_to_200")
    warnings = document_model_dict.get("warnings")
    errors = document_model_dict.get("errors")
    if isinstance(warnings, list):
        diagnostics.extend(f"builder_warning: {warning}" for warning in warnings if warning)
    if isinstance(errors, list):
        diagnostics.extend(f"builder_error: {error}" for error in errors if error)
    status = "built" if nodes else "partial"
    if not nodes:
        diagnostics.append("document_model_built_but_nodes_empty")
    runtime = {
        "status": status,
        "source_type": source.get("source_type") or "",
        "source_id": source.get("source_id") or "",
        "template_filename": source.get("template_filename") or "",
        "template_path": source.get("template_path") or "",
        "template_analysis_source": source.get("template_analysis_source") or "",
        "template_analysis_keys": source.get("template_analysis_keys") or [],
        "semantic_regions_count": len(semantic_regions),
        "document_model_type": type(document_model).__name__,
        "summary": _document_model_summary(document_model),
        "nodes": nodes,
        "diagnostics": diagnostics,
    }
    runtime.update(_documentmodel_viewer_stats(nodes))
    return runtime


@router.get("/health")
def api_v4_stage2_config_health():
    return {
        "ok": True,
        "module": "stage2_config",
        "schema_version": STAGE2_CONFIG_SCHEMA_VERSION,
    }


@router.get("/source-summary")
def api_v4_stage2_config_source_summary():
    return {
        "ok": True,
        "module": "stage2_config",
        "schema_version": STAGE2_CONFIG_SCHEMA_VERSION,
        "sources": {
            "stage2_config_profiles": _profile_source_summary("data/stage2_config_profiles.json"),
            "legacy_template_profiles": _profile_source_summary(
                "data/template_profiles.json",
                note="read_only_legacy_source",
            ),
            "v4_template_cache": _template_cache_summary(),
        },
    }


@router.get("/template-analysis-summary")
def api_v4_stage2_config_template_analysis_summary():
    raw_profiles, profile_error = _load_legacy_profile_items()
    legacy_profiles = [_legacy_profile_summary(profile) for profile in raw_profiles]
    template_cache = _template_analysis_cache_summary()
    summary = {
        "legacy_profiles": legacy_profiles,
        "template_cache": template_cache,
        "diagnosis": _template_analysis_diagnosis(legacy_profiles, template_cache),
    }
    if profile_error:
        summary["legacy_profiles_error"] = profile_error
    return {
        "ok": True,
        "module": "stage2_config",
        "schema_version": STAGE2_CONFIG_SCHEMA_VERSION,
        "summary": summary,
    }


@router.get("/documentmodel-viewer")
def api_v4_stage2_config_documentmodel_viewer():
    return {
        "ok": True,
        "module": "stage2_config",
        "schema_version": STAGE2_CONFIG_SCHEMA_VERSION,
        "viewer": _build_documentmodel_viewer(),
    }


@router.get("/documentmodel-runtime")
def api_v4_stage2_config_documentmodel_runtime():
    runtime = _build_documentmodel_runtime()
    return {
        "ok": runtime.get("status") != "error",
        "module": "stage2_config",
        "schema_version": STAGE2_CONFIG_SCHEMA_VERSION,
        "runtime": runtime,
    }


@router.get("/profiles")
def api_v4_stage2_config_profiles():
    return {
        "success": True,
        "profiles": load_stage2_config_profiles(),
    }


@router.post("/profiles")
def api_v4_stage2_config_profile_create(payload: Any = Body(None)):
    payload = payload if isinstance(payload, dict) else {}
    profile_id = str(payload.get("profile_id") or "").strip()
    profile_name = str(payload.get("profile_name") or "").strip()
    if not profile_id:
        raise HTTPException(status_code=400, detail="profile_id is required")
    if not profile_name:
        raise HTTPException(status_code=400, detail="profile_name is required")
    return {
        "success": True,
        "profile": create_stage2_config_profile(profile_id, profile_name),
    }


@router.get("/profiles/{profile_id}")
def api_v4_stage2_config_profile_detail(profile_id: str):
    profile = get_stage2_config_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Stage2 config profile not found")
    return {
        "success": True,
        "profile": profile,
    }


@router.put("/profiles/{profile_id}")
def api_v4_stage2_config_profile_save(profile_id: str, payload: Any = Body(None)):
    profile = payload if isinstance(payload, dict) else {}
    path_profile_id = str(profile_id or "").strip()
    body_profile_id = str(profile.get("profile_id") or "").strip()
    if not path_profile_id:
        raise HTTPException(status_code=400, detail="profile_id is required")
    if body_profile_id != path_profile_id:
        raise HTTPException(status_code=400, detail="profile_id must match path")
    if str(profile.get("schema_version") or "").strip() != STAGE2_CONFIG_SCHEMA_VERSION:
        profile["schema_version"] = STAGE2_CONFIG_SCHEMA_VERSION
    return {
        "success": True,
        "profile": upsert_stage2_config_profile(profile),
    }
