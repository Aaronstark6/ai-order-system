from pathlib import Path
import os
import shutil
import subprocess

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.app_settings import (
    get_deepseek_api_key,
    get_export_sync_dir,
    public_app_settings,
    save_app_settings,
    save_deepseek_api_key,
)
from app.config import AI_SETTINGS_PASSWORD
from app.description_template_manager import (
    get_description_template,
    list_description_templates,
    restore_default_description_template,
    save_description_template,
)
from app.excel_generator import generate_excel
from app.field_library import add_field, delete_field, load_fields, update_field
from app.image_manager import LAYOUT_CACHE_DIR
from app.ingredient_parser import analyze_ingredient_initials_source
from app.routes.images import router as images_router
from app.routes.parse import router as parse_router
from app.routes.templates import router as templates_router


core_router = APIRouter()

__all__ = [
    "core_router",
    "images_router",
    "parse_router",
    "templates_router",
]

BASE_DIR = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_UPLOAD_DIR = BASE_DIR / "uploads" / "images"
LAST_GENERATED_FILE_PATH = ""


def _is_path_under(path: Path, root: Path):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _export_sync_exclude_roots():
    export_sync_dir = str(get_export_sync_dir() or "").strip()
    if not export_sync_dir:
        return []

    try:
        target = Path(export_sync_dir).expanduser()
        if not target.is_absolute():
            target = BASE_DIR / target
        return [target.resolve()]
    except Exception:
        return []


def _clear_files_under_dir_safe(target_dir: Path, exclude_roots=None, skip_dirs=None):
    deleted_files = 0
    failed_files = 0
    errors = []
    exclude_roots = [root.resolve() for root in (exclude_roots or [])]
    skip_dirs = [root.resolve() for root in (skip_dirs or [])]

    root = target_dir.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    if not _is_path_under(root, BASE_DIR):
        return deleted_files, 1, [f"{root} is outside the project directory"]
    if not root.is_dir():
        return deleted_files, failed_files, [f"{root} is not a directory"]

    for path in root.rglob("*"):
        try:
            resolved = path.resolve()
            resolved.relative_to(root)
        except ValueError:
            failed_files += 1
            errors.append(f"跳过非法路径：{path}")
            continue

        if not path.is_file():
            continue
        if any(_is_path_under(resolved, skip_root) for skip_root in skip_dirs):
            continue
        if any(_is_path_under(resolved, exclude_root) for exclude_root in exclude_roots):
            continue

        try:
            path.unlink()
            deleted_files += 1
        except Exception as e:
            failed_files += 1
            errors.append(f"{path}: {e}")

    return deleted_files, failed_files, errors


def _clear_cache_target(name: str, target_dir: Path, exclude_roots=None, skip_dirs=None):
    deleted, failed, errors = _clear_files_under_dir_safe(
        target_dir,
        exclude_roots=exclude_roots,
        skip_dirs=skip_dirs,
    )
    return {
        "name": name,
        "path": str(target_dir.resolve()),
        "deleted_files": deleted,
        "failed_files": failed,
        "errors": errors,
    }


def _clear_cache_payload():
    exclude_roots = _export_sync_exclude_roots()
    targets = [
        ("输出文件", OUTPUT_DIR, [LAYOUT_CACHE_DIR]),
        ("上传图片", IMAGE_UPLOAD_DIR, []),
        ("Layout临时图片", LAYOUT_CACHE_DIR, []),
    ]
    details = [
        _clear_cache_target(
            name,
            target_dir,
            exclude_roots=exclude_roots,
            skip_dirs=skip_dirs,
        )
        for name, target_dir, skip_dirs in targets
    ]
    deleted_files = sum(item["deleted_files"] for item in details)
    failed_files = sum(item["failed_files"] for item in details)
    errors = []
    for item in details:
        errors.extend(item.get("errors") or [])

    return {
        "success": failed_files == 0,
        "deleted_files": deleted_files,
        "failed_files": failed_files,
        "details": details,
        "errors": errors,
        "message": "缓存已清空" if failed_files == 0 else "缓存部分清理失败",
    }


@core_router.get("/api/fields")
def api_get_fields():
    return {"success": True, "fields": load_fields()}


@core_router.post("/api/fields")
def api_add_field(field: dict):
    try:
        return {"success": True, "field": add_field(field)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.put("/api/fields/{key}")
def api_update_field(key: str, field: dict):
    try:
        return {"success": True, "field": update_field(key, field)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.delete("/api/fields/{key}")
def api_delete_field(key: str):
    try:
        return {"success": True, "result": delete_field(key)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.get("/api/app-settings")
def api_get_app_settings():
    return {"success": True, "settings": public_app_settings()}


@core_router.post("/api/app-settings")
def api_save_app_settings(data: dict):
    try:
        save_app_settings(data)
        return {"success": True, "settings": public_app_settings()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/test-export-sync-dir")
def api_test_export_sync_dir(data: dict):
    try:
        export_sync_dir = str(data.get("export_sync_dir") or "").strip()
        if not export_sync_dir:
            return {"success": False, "error": "请先输入 Excel 同步文件夹路径"}

        target_dir = Path(export_sync_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        if not target_dir.is_dir():
            return {"success": False, "error": "路径不是有效文件夹"}

        test_file = target_dir / ".ai_order_write_test.tmp"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
        return {"success": True, "message": "路径可用"}
    except Exception as e:
        return {"success": False, "error": f"路径不可用：{e}"}


@core_router.post("/api/clear-cache")
def api_clear_cache():
    try:
        return _clear_cache_payload()
    except Exception as e:
        return {
            "success": False,
            "deleted_files": 0,
            "failed_files": 1,
            "details": [],
            "errors": [str(e)],
            "message": "缓存清理失败",
        }


@core_router.get("/api/ai-settings/status")
def api_ai_settings_status():
    return {"success": True, "has_api_key": bool(get_deepseek_api_key())}


@core_router.post("/api/ai-settings/unlock")
def api_ai_settings_unlock(data: dict):
    password = str(data.get("password") or "")
    if password != AI_SETTINGS_PASSWORD:
        return {"success": False, "error": "密码错误"}

    return {"success": True, "api_key": get_deepseek_api_key()}


@core_router.post("/api/ai-settings")
def api_save_ai_settings(data: dict):
    try:
        password = str(data.get("password") or "")
        if password != AI_SETTINGS_PASSWORD:
            return {"success": False, "error": "密码错误"}

        save_deepseek_api_key(data.get("api_key", ""))
        return {"success": True, "has_api_key": bool(str(data.get("api_key") or "").strip())}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.get("/api/description-templates")
def api_list_description_templates():
    try:
        return {"success": True, "templates": list_description_templates()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.get("/api/description-templates/{template_name}")
def api_get_description_template(template_name: str):
    try:
        return {
            "success": True,
            "template_name": template_name,
            "content": get_description_template(template_name),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/description-templates/{template_name}")
def api_save_description_template(template_name: str, data: dict):
    try:
        saved = save_description_template(template_name, data.get("content", ""))
        return {"success": True, "template": saved}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/description-templates/{template_name}/restore-default")
def api_restore_description_template(template_name: str):
    try:
        restored = restore_default_description_template(template_name)
        return {"success": True, "template": restored}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/generate-excel")
def api_generate_excel(data: dict):
    global LAST_GENERATED_FILE_PATH
    try:
        profile_id = data.get("profile_id", "")
        order_data = data.get("data", {})
        description_fields = data.get("description_fields", {})
        if isinstance(order_data, dict) and not str(order_data.get("ingredient_initials") or "").strip():
            ingredient_analysis = analyze_ingredient_initials_source(
                description_fields=description_fields,
                text=data.get("description_text"),
            )
            ingredient_initials = str(ingredient_analysis.get("initials") or "").strip().upper()
            if ingredient_initials:
                order_data["ingredient_initials"] = ingredient_initials
                order_data.pop("document_no", None)
                order_data.pop("product_code", None)
        # legacy composite mapping compatibility
        composite_data = data.get("composite_data")
        if composite_data is None:
            composite_data = data.get("composite_values", [])

        result = generate_excel(
            data=order_data,
            profile_id=profile_id,
            composite_data=composite_data,
            description_text=data.get("description_text"),
            image_data=data.get("image_data") or {},
            image_pool=data.get("image_pool") or [],
            description_fields=description_fields,
        )
        if result.get("success") and str(result.get("lastGeneratedFilePath") or result.get("output_path") or "").strip():
            LAST_GENERATED_FILE_PATH = str(result.get("lastGeneratedFilePath") or result.get("output_path") or "").strip()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/sync-output")
def api_sync_output(data: dict):
    global LAST_GENERATED_FILE_PATH
    try:
        last_generated_file_path = str(
            data.get("lastGeneratedFilePath") or data.get("last_generated_file_path") or LAST_GENERATED_FILE_PATH
        ).strip()
        if not last_generated_file_path:
            return {"success": False, "error": "lastGeneratedFilePath不能为空，请先生成 Excel"}

        source_file = Path(last_generated_file_path).expanduser()
        if not source_file.is_absolute():
            source_file = (BASE_DIR / source_file).resolve()
        else:
            source_file = source_file.resolve()

        if not source_file.exists():
            return {"success": False, "error": "输出文件不存在，请先生成 Excel"}

        filename = source_file.name

        export_sync_dir = str(get_export_sync_dir() or "").strip()
        if not export_sync_dir:
            return {"success": False, "error": "请先在配置中心设置 Excel 同步文件夹路径"}

        target_dir = Path(export_sync_dir).expanduser()
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / filename
        shutil.copy2(source_file, target_file)
        LAST_GENERATED_FILE_PATH = str(target_file)

        return {
            "success": True,
            "synced": True,
            "sync_path": str(target_file),
            "lastGeneratedFilePath": str(target_file),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.post("/api/open-output-folder")
def api_open_output_folder(data: dict):
    try:
        last_generated_file_path = str(
            data.get("lastGeneratedFilePath") or data.get("last_generated_file_path") or LAST_GENERATED_FILE_PATH
        ).strip()
        if not last_generated_file_path:
            return {"success": False, "error": "lastGeneratedFilePath不能为空，请先生成 Excel"}

        target_file = Path(last_generated_file_path).expanduser()
        if not target_file.is_absolute():
            target_file = (BASE_DIR / target_file).resolve()
        else:
            target_file = target_file.resolve()

        if not target_file.exists() or not target_file.is_file():
            return {"success": False, "error": "找不到实际生成的订单文件，请重新生成 Excel"}

        if os.name != "nt":
            return {"success": False, "error": "当前系统暂不支持自动打开文件夹，请手动打开输出目录"}

        target_dir = os.path.dirname(str(target_file))
        subprocess.Popen(["explorer", f"/select,{str(target_file)}"])
        return {"success": True, "path": str(target_dir), "filename": target_file.name}
    except Exception as e:
        return {"success": False, "error": str(e)}


@core_router.get("/api/download/{filename}")
def api_download(filename: str):
    safe_filename = Path(str(filename or "")).name
    return FileResponse(OUTPUT_DIR / safe_filename)
