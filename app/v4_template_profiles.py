import json
from copy import deepcopy

from app.runtime_paths import get_base_dir


DEFAULT_PROFILE_ID = "default_profile"
REQUIRED_FIELDS = [
    "profile_id",
    "profile_name",
    "schema_version",
    "structured_mapping_file",
    "table_mapping_file",
    "block_rules_file",
]
FILE_FIELDS = [
    "structured_mapping_file",
    "table_mapping_file",
    "block_rules_file",
]


def _profiles_dir():
    return get_base_dir() / "v4" / "template_profiles"


def _default_profile_path():
    return _profiles_dir() / f"{DEFAULT_PROFILE_ID}.json"


def _load_profile_file(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def load_default_template_profile():
    return _load_profile_file(_default_profile_path())


def get_current_template_profile():
    return load_default_template_profile()


def list_template_profiles():
    profiles = []
    profiles_dir = _profiles_dir()
    if not profiles_dir.is_dir():
        return profiles

    for path in sorted(profiles_dir.glob("*.json")):
        profile = _load_profile_file(path)
        if profile:
            profiles.append(profile)

    return profiles


def _resolve_profile_file(path_value):
    text = str(path_value or "").strip()
    if not text:
        return None
    return get_base_dir() / text


def validate_template_profile(profile):
    profile = deepcopy(profile) if isinstance(profile, dict) else {}
    warnings = []
    errors = []
    file_status = {}

    for field in REQUIRED_FIELDS:
        if not str(profile.get(field) or "").strip():
            errors.append(f"{field} 不能为空")

    for field in FILE_FIELDS:
        path = _resolve_profile_file(profile.get(field))
        if path and path.is_file():
            file_status[field] = "ok"
        else:
            file_status[field] = "error"
            errors.append(f"{field} 文件不存在")

    render_config = profile.get("render_config")
    if render_config is not None and not isinstance(render_config, dict):
        warnings.append("render_config 应为 object")

    return {
        "valid": not errors,
        "warnings": warnings,
        "errors": errors,
        "file_status": file_status,
    }
