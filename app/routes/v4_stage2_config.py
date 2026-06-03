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
    for key in ("label", "field_label", "name", "title", "field_key"):
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
