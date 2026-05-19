import json
import re
from copy import deepcopy
from datetime import datetime

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
    path = get_base_dir() / "v4" / "template_profiles"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _rules_dir():
    path = get_base_dir() / "v4" / "rules"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _default_profile_path():
    return _profiles_dir() / f"{DEFAULT_PROFILE_ID}.json"


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _safe_profile_id(value):
    text = str(value or "").strip().lower()
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^\w.-]+", "_", text, flags=re.UNICODE)
    text = text.strip("._")
    return text or DEFAULT_PROFILE_ID


def _profile_path(profile_id):
    safe_id = _safe_profile_id(profile_id)
    return _profiles_dir() / f"{safe_id}.json"


def _load_profile_file(path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}

    return data if isinstance(data, dict) else {}


def _write_profile_file(path, profile):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
        f.write("\n")


def load_default_template_profile():
    return _load_profile_file(_default_profile_path())


def get_current_template_profile():
    return load_default_template_profile()


def load_template_profile(profile_id):
    profile_id = _safe_profile_id(profile_id)
    return _load_profile_file(_profile_path(profile_id))


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


def _default_rule_paths_for_profile(profile_id):
    profile_id = _safe_profile_id(profile_id)
    if profile_id == DEFAULT_PROFILE_ID:
        return {
            "structured_mapping_file": "v4/rules/structured_excel_mapping.json",
            "table_mapping_file": "v4/rules/table_mapping.json",
            "block_rules_file": "v4/rules/block_merge_rules.json",
        }

    return {
        "structured_mapping_file": f"v4/rules/profiles/{profile_id}/structured_excel_mapping.json",
        "table_mapping_file": f"v4/rules/profiles/{profile_id}/table_mapping.json",
        "block_rules_file": f"v4/rules/profiles/{profile_id}/block_merge_rules.json",
    }


def build_template_profile(
    profile_id,
    profile_name="",
    schema_version="v4.1",
    layout_hash="",
    template_name="",
    template_filename="",
    template_note="",
):
    profile_id = _safe_profile_id(profile_id)
    rule_paths = _default_rule_paths_for_profile(profile_id)
    now_text = _now_text()

    return {
        "profile_id": profile_id,
        "profile_name": str(profile_name or "").strip() or profile_id,
        "schema_version": str(schema_version or "v4.1").strip() or "v4.1",
        "layout_hash": str(layout_hash or "").strip(),
        "template_name": str(template_name or "").strip(),
        "template_filename": str(template_filename or "").strip(),
        "template_note": str(template_note or "").strip(),
        "structured_mapping_file": rule_paths["structured_mapping_file"],
        "table_mapping_file": rule_paths["table_mapping_file"],
        "block_rules_file": rule_paths["block_rules_file"],
        "created_at": now_text,
        "updated_at": now_text,
        "render_config": {
            "html_theme": "dark",
            "excel_mode": "standard",
        },
    }


def save_template_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError("profile 必须是 object")

    profile_id = _safe_profile_id(profile.get("profile_id"))
    existing = load_template_profile(profile_id)
    now_text = _now_text()

    merged = {}
    if existing:
        merged.update(existing)
    merged.update(deepcopy(profile))

    merged["profile_id"] = profile_id
    merged["profile_name"] = str(merged.get("profile_name") or profile_id).strip()
    merged["schema_version"] = str(merged.get("schema_version") or "v4.1").strip() or "v4.1"
    merged["created_at"] = str(merged.get("created_at") or now_text)
    merged["updated_at"] = now_text

    default_paths = _default_rule_paths_for_profile(profile_id)
    for key, value in default_paths.items():
        if not str(merged.get(key) or "").strip():
            merged[key] = value

    render_config = merged.get("render_config")
    if not isinstance(render_config, dict):
        merged["render_config"] = {
            "html_theme": "dark",
            "excel_mode": "standard",
        }

    _write_profile_file(_profile_path(profile_id), merged)
    return merged


def create_template_profile(payload):
    payload = payload if isinstance(payload, dict) else {}
    profile_id = _safe_profile_id(
        payload.get("profile_id")
        or payload.get("layout_hash")
        or payload.get("template_name")
        or payload.get("template_filename")
    )

    profile = build_template_profile(
        profile_id=profile_id,
        profile_name=payload.get("profile_name") or payload.get("template_name") or profile_id,
        schema_version=payload.get("schema_version") or "v4.1",
        layout_hash=payload.get("layout_hash") or "",
        template_name=payload.get("template_name") or "",
        template_filename=payload.get("template_filename") or "",
        template_note=payload.get("template_note") or "",
    )

    return save_template_profile(profile)


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
            file_status[field] = "missing"
            warnings.append(f"{field} 文件暂不存在")

    render_config = profile.get("render_config")
    if render_config is not None and not isinstance(render_config, dict):
        warnings.append("render_config 应为 object")

    return {
        "valid": not errors,
        "warnings": warnings,
        "errors": errors,
        "file_status": file_status,
    }
