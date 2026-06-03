from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from app.runtime_paths import get_base_dir
from app.v4_stage2_config_schema import create_empty_stage2_config_profile


STAGE2_CONFIG_PROFILE_PATH = get_base_dir() / "data" / "stage2_config_profiles.json"


def _normalize_profiles(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        profiles = data.get("profiles")
        if isinstance(profiles, list):
            return [item for item in profiles if isinstance(item, dict)]
    return []


def load_stage2_config_profiles() -> list[dict[str, Any]]:
    if not STAGE2_CONFIG_PROFILE_PATH.is_file():
        return []
    try:
        with STAGE2_CONFIG_PROFILE_PATH.open("r", encoding="utf-8") as f:
            return _normalize_profiles(json.load(f))
    except Exception:
        return []


def save_stage2_config_profiles(profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = _normalize_profiles(profiles)
    STAGE2_CONFIG_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with STAGE2_CONFIG_PROFILE_PATH.open("w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return normalized


def get_stage2_config_profile(profile_id: str) -> dict[str, Any] | None:
    requested_id = str(profile_id or "").strip()
    if not requested_id:
        return None
    for profile in load_stage2_config_profiles():
        if str(profile.get("profile_id") or "").strip() == requested_id:
            return deepcopy(profile)
    return None


def upsert_stage2_config_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict):
        raise ValueError("profile must be an object")
    profile_id = str(profile.get("profile_id") or "").strip()
    if not profile_id:
        raise ValueError("profile_id is required")

    profiles = load_stage2_config_profiles()
    saved_profile = deepcopy(profile)
    replaced = False
    for index, existing in enumerate(profiles):
        if str(existing.get("profile_id") or "").strip() == profile_id:
            profiles[index] = saved_profile
            replaced = True
            break
    if not replaced:
        profiles.append(saved_profile)
    save_stage2_config_profiles(profiles)
    return deepcopy(saved_profile)


def create_stage2_config_profile(profile_id: str, profile_name: str) -> dict[str, Any]:
    requested_id = str(profile_id or "").strip()
    requested_name = str(profile_name or "").strip()
    if not requested_id:
        raise ValueError("profile_id is required")
    if not requested_name:
        raise ValueError("profile_name is required")

    existing = get_stage2_config_profile(requested_id)
    if existing:
        return existing

    profile = create_empty_stage2_config_profile(requested_id, requested_name)
    return upsert_stage2_config_profile(profile)
