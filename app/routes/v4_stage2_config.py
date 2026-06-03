from __future__ import annotations

import json
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
