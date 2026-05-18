import json
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_schema_version import CURRENT_SCHEMA_VERSION


logger = get_logger(__name__)

PROFILES_DIR_NAME = "v4"
PROFILES_SUBDIR = "template_profiles"

_default_profile_id = "default_profile"


def _get_profiles_dir():
    base = get_base_dir()
    profiles_dir = base / PROFILES_DIR_NAME / PROFILES_SUBDIR
    profiles_dir.mkdir(parents=True, exist_ok=True)
    return profiles_dir


def _check_file_status(relative_path, base_dir=None):
    if not relative_path:
        return {"path": "", "exists": False, "status": "error", "message": "未设置文件路径"}
    if base_dir is None:
        base_dir = get_base_dir()
    full_path = (base_dir / relative_path).resolve()
    try:
        full_path.relative_to(base_dir.resolve())
    except ValueError:
        return {"path": relative_path, "exists": False, "status": "error", "message": "路径不合法"}
    if full_path.is_file():
        try:
            with full_path.open("r", encoding="utf-8") as f:
                json.load(f)
            return {"path": relative_path, "exists": True, "status": "ok", "message": "文件存在且有效"}
        except Exception:
            return {"path": relative_path, "exists": True, "status": "warning", "message": "文件存在但 JSON 无效"}
    return {"path": relative_path, "exists": False, "status": "error", "message": "文件不存在"}


def get_profile_file_checks(profile):
    if not isinstance(profile, dict):
        return {}
    base_dir = get_base_dir()
    return {
        "structured_mapping_file": _check_file_status(
            profile.get("structured_mapping_file", ""), base_dir
        ),
        "table_mapping_file": _check_file_status(
            profile.get("table_mapping_file", ""), base_dir
        ),
        "block_rules_file": _check_file_status(
            profile.get("block_rules_file", ""), base_dir
        ),
    }


def _ensure_default_profile():
    profiles_dir = _get_profiles_dir()
    default_path = profiles_dir / f"{_default_profile_id}.json"

    if default_path.exists():
        try:
            with default_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            if isinstance(existing, dict) and existing.get("profile_id") == _default_profile_id:
                return True
        except Exception:
            pass

    default_profile = {
        "profile_id": _default_profile_id,
        "profile_name": "默认模板档案",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "structured_mapping_file": "v4/rules/structured_excel_mapping.json",
        "table_mapping_file": "v4/rules/table_mapping.json",
        "block_rules_file": "v4/rules/block_merge_rules.json",
        "render_config": {
            "html_theme": "dark",
            "excel_mode": "standard",
        },
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    with default_path.open("w", encoding="utf-8") as f:
        json.dump(default_profile, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info("TemplateProfile default profile created: path=%s", default_path)
    return True


def list_template_profiles():
    profiles_dir = _get_profiles_dir()
    _ensure_default_profile()

    profiles = []
    for fpath in sorted(profiles_dir.glob("*.json")):
        try:
            with fpath.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and data.get("profile_id"):
                data.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
                data.setdefault("render_config", {"html_theme": "dark", "excel_mode": "standard"})
                data.setdefault("structured_mapping_file", "")
                data.setdefault("table_mapping_file", "")
                data.setdefault("block_rules_file", "")
                file_checks = get_profile_file_checks(data)
                data["_file_checks"] = file_checks
                profiles.append(data)
        except Exception as exc:
            logger.warning("TemplateProfile skip invalid profile: path=%s error=%s", fpath, exc)

    return profiles


def load_template_profile(profile_id=None):
    profiles_dir = _get_profiles_dir()
    _ensure_default_profile()

    pid = profile_id or _default_profile_id
    fpath = profiles_dir / f"{pid}.json"

    if not fpath.exists():
        logger.info("TemplateProfile not found: profile_id=%s", pid)
        return {"success": False, "error": f"模板档案 '{pid}' 不存在"}

    try:
        with fpath.open("r", encoding="utf-8") as f:
            profile = json.load(f)
    except JSONDecodeError:
        logger.error("TemplateProfile JSON parse failed: profile_id=%s", pid)
        return {"success": False, "error": f"模板档案 '{pid}' JSON 解析失败"}
    except OSError as exc:
        logger.error("TemplateProfile read failed: profile_id=%s error=%s", pid, exc)
        return {"success": False, "error": f"模板档案 '{pid}' 读取失败"}

    if not isinstance(profile, dict):
        return {"success": False, "error": f"模板档案 '{pid}' 数据非法"}

    profile.setdefault("schema_version", CURRENT_SCHEMA_VERSION)
    profile.setdefault("render_config", {"html_theme": "dark", "excel_mode": "standard"})
    profile.setdefault("structured_mapping_file", "")
    profile.setdefault("table_mapping_file", "")
    profile.setdefault("block_rules_file", "")

    return {"success": True, "data": profile}


def get_current_template_profile():
    result = load_template_profile(_default_profile_id)
    if result.get("success"):
        profile = result["data"]
        file_checks = get_profile_file_checks(profile)
        profile["_file_checks"] = file_checks
        return profile
    return {
        "profile_id": _default_profile_id,
        "profile_name": "默认模板档案",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "structured_mapping_file": "v4/rules/structured_excel_mapping.json",
        "table_mapping_file": "v4/rules/table_mapping.json",
        "block_rules_file": "v4/rules/block_merge_rules.json",
        "render_config": {"html_theme": "dark", "excel_mode": "standard"},
        "_file_checks": {},
    }


def get_current_template_profile_for_pipeline():
    result = load_template_profile(_default_profile_id)
    if result.get("success"):
        return result["data"]
    return {
        "profile_id": _default_profile_id,
        "profile_name": "默认模板档案",
        "schema_version": CURRENT_SCHEMA_VERSION,
        "structured_mapping_file": "v4/rules/structured_excel_mapping.json",
        "table_mapping_file": "v4/rules/table_mapping.json",
        "block_rules_file": "v4/rules/block_merge_rules.json",
        "render_config": {"html_theme": "dark", "excel_mode": "standard"},
    }


def save_template_profile(profile_data):
    if not isinstance(profile_data, dict):
        return {"success": False, "error": "profile_data 必须是字典"}

    profile_id = profile_data.get("profile_id", "").strip()
    if not profile_id:
        return {"success": False, "error": "profile_id 不能为空"}

    profile_name = profile_data.get("profile_name", "").strip()
    if not profile_name:
        return {"success": False, "error": "profile_name 不能为空"}

    schema_version = profile_data.get("schema_version", "").strip() or CURRENT_SCHEMA_VERSION

    profiles_dir = _get_profiles_dir()
    _ensure_default_profile()
    fpath = profiles_dir / f"{profile_id}.json"

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    profile = {
        "profile_id": profile_id,
        "profile_name": profile_name,
        "schema_version": schema_version,
        "structured_mapping_file": profile_data.get("structured_mapping_file", ""),
        "table_mapping_file": profile_data.get("table_mapping_file", ""),
        "block_rules_file": profile_data.get("block_rules_file", ""),
        "render_config": profile_data.get("render_config", {"html_theme": "dark", "excel_mode": "standard"}),
        "updated_at": now_text,
    }

    if fpath.exists():
        try:
            with fpath.open("r", encoding="utf-8") as f:
                existing = json.load(f)
            profile["created_at"] = existing.get("created_at", now_text)
        except Exception:
            profile["created_at"] = now_text
    else:
        profile["created_at"] = now_text

    with fpath.open("w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)
        f.write("\n")

    logger.info("TemplateProfile saved: profile_id=%s profile_name=%s", profile_id, profile_name)
    return {"success": True, "data": profile}


def delete_template_profile(profile_id):
    if profile_id == _default_profile_id:
        return {"success": False, "error": "不能删除默认模板档案"}

    profiles_dir = _get_profiles_dir()
    fpath = profiles_dir / f"{profile_id}.json"

    if not fpath.exists():
        return {"success": False, "error": f"模板档案 '{profile_id}' 不存在"}

    fpath.unlink()
    logger.info("TemplateProfile deleted: profile_id=%s", profile_id)
    return {"success": True, "message": f"模板档案 '{profile_id}' 已删除"}
