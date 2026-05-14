from pathlib import Path
from datetime import datetime
import os
import re
import shutil
import subprocess

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.app_settings import (
    load_app_settings,
    save_app_settings,
    get_export_sync_dir,
    get_deepseek_api_key,
    public_app_settings,
    save_deepseek_api_key,
)
from app.config import AI_SETTINGS_PASSWORD
from app.field_library import (
    load_fields,
    add_field,
    update_field,
    delete_field
)
from app.ai_parser import parse_message, generate_description_from_message
from app.ingredient_parser import extract_ingredient_initials_from_description_fields
from app.excel_generator import generate_excel
from app.image_manager import (
    ensure_image_upload_dir,
    load_image_fields,
    safe_image_extension,
    save_image_fields,
)
from app.description_template_manager import (
    list_description_templates,
    get_description_template,
    save_description_template,
    restore_default_description_template,
)
from app.template_manager import (
    load_profiles,
    get_profile,
    create_profile,
    delete_profile,
    update_profile_mappings,
    upload_template_file,
    delete_template_file,
)

# ✅ 关键：必须在最前面
app = FastAPI(title="AI Order System V2")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
IMAGE_UPLOAD_DIR = BASE_DIR / "uploads" / "images"
LAST_GENERATED_FILE_PATH = ""

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
def config_page():
    return FileResponse(STATIC_DIR / "config.html")


def _clear_files_under_dir(target_dir: Path):
    deleted_files = 0
    failed_files = 0
    errors = []

    root = target_dir.resolve()
    if not root.exists():
        return deleted_files, failed_files, errors

    if not root.is_dir():
        return deleted_files, failed_files, [f"{root} 不是目录"]

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

        try:
            path.unlink()
            deleted_files += 1
        except Exception as e:
            failed_files += 1
            errors.append(f"{path}: {e}")

    return deleted_files, failed_files, errors


# ================= 字段库 =================

@app.get("/api/fields")
def api_get_fields():
    return {"success": True, "fields": load_fields()}


@app.post("/api/fields")
def api_add_field(field: dict):
    try:
        return {"success": True, "field": add_field(field)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.put("/api/fields/{key}")
def api_update_field(key: str, field: dict):
    try:
        return {"success": True, "field": update_field(key, field)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/fields/{key}")
def api_delete_field(key: str):
    try:
        return {"success": True, "result": delete_field(key)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================= 图片字段库 =================

@app.get("/api/image-fields")
def api_get_image_fields():
    try:
        return {"success": True, "fields": load_image_fields()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/image-fields")
def api_save_image_fields(data: dict):
    try:
        fields = data.get("fields", data)
        if not isinstance(fields, list):
            return {"success": False, "error": "图片字段配置必须是数组"}
        return {"success": True, "fields": save_image_fields(fields)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/upload-image")
def api_upload_image(field_key: str = Form(...), file: UploadFile = File(...)):
    try:
        original_key = str(field_key or "").strip()
        safe_key = re.sub(r"[^A-Za-z0-9_-]+", "_", original_key).strip("_")
        if not original_key or not safe_key:
            return {"success": False, "error": "field_key 不能为空"}

        ext = safe_image_extension(file.filename)
        upload_dir = ensure_image_upload_dir()
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_key}{ext}"
        image_file = upload_dir / filename

        with open(image_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return {
            "success": True,
            "field_key": original_key,
            "image_path": str(Path("uploads") / "images" / filename),
            "filename": filename,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================= 模板映射 =================

@app.get("/api/template-profiles")
def api_get_profiles():
    return {"success": True, "profiles": load_profiles()}


@app.post("/api/template-profiles")
def api_create_profile(data: dict):
    try:
        return {"success": True, "profile": create_profile(data.get("name", ""))}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/template-profiles/{profile_id}")
def api_delete_profile(profile_id: str):
    try:
        return {"success": True, "result": delete_profile(profile_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/template-profiles/{profile_id}/upload-template")
def api_upload_template(profile_id: str, file: UploadFile = File(...)):
    try:
        profile = upload_template_file(profile_id, file)
        return {
            "success": True,
            "template_file": profile.get("template_file", ""),
            "template_display_name": profile.get("template_display_name", ""),
            "profile": profile,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/template-profiles/{profile_id}/template")
def api_delete_template_file(profile_id: str):
    try:
        return {"success": True, "profile": delete_template_file(profile_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/template-profiles/{profile_id}/mappings")
def api_update_mappings(profile_id: str, data: dict):
    try:
        return {
            "success": True,
            "profile": update_profile_mappings(
                profile_id=profile_id,
                mappings=data.get("mappings", {}),
                # legacy composite mapping compatibility
                composite_mappings=data.get("composite_mappings"),
                document_no_settings=data.get("document_no_settings"),
                mapping_defaults=data.get("mapping_defaults"),
                description_settings=data.get("description_settings"),
                image_fields=data.get("image_fields"),
                layout_config=data.get("layout_config"),
                mapping_order=data.get("mapping_order"),
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/template-profiles/{profile_id}/layout-config")
def api_update_layout_config(profile_id: str, data: dict):
    try:
        profile = get_profile(profile_id)
        if not profile:
            return {"success": False, "error": "映射不存在"}

        return {
            "success": True,
            "profile": update_profile_mappings(
                profile_id=profile_id,
                mappings=None,
                layout_config=data.get("layout_config"),
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/app-settings")
def api_get_app_settings():
    return {"success": True, "settings": public_app_settings()}


@app.post("/api/app-settings")
def api_save_app_settings(data: dict):
    try:
        save_app_settings(data)
        return {"success": True, "settings": public_app_settings()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/test-export-sync-dir")
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


@app.post("/api/clear-cache")
def api_clear_cache():
    try:
        deleted_files = 0
        failed_files = 0
        errors = []

        for target_dir in [OUTPUT_DIR, IMAGE_UPLOAD_DIR]:
            deleted, failed, dir_errors = _clear_files_under_dir(target_dir)
            deleted_files += deleted
            failed_files += failed
            errors.extend(dir_errors)
            target_dir.mkdir(parents=True, exist_ok=True)

        return {
            "success": failed_files == 0,
            "deleted_files": deleted_files,
            "failed_files": failed_files,
            "errors": errors,
            "message": "缓存已清空" if failed_files == 0 else "缓存部分清理失败",
        }
    except Exception as e:
        return {
            "success": False,
            "deleted_files": 0,
            "failed_files": 1,
            "errors": [str(e)],
            "message": "缓存清理失败",
        }


@app.get("/api/ai-settings/status")
def api_ai_settings_status():
    return {"success": True, "has_api_key": bool(get_deepseek_api_key())}


@app.post("/api/ai-settings/unlock")
def api_ai_settings_unlock(data: dict):
    password = str(data.get("password") or "")
    if password != AI_SETTINGS_PASSWORD:
        return {"success": False, "error": "密码错误"}

    return {"success": True, "api_key": get_deepseek_api_key()}


@app.post("/api/ai-settings")
def api_save_ai_settings(data: dict):
    try:
        password = str(data.get("password") or "")
        if password != AI_SETTINGS_PASSWORD:
            return {"success": False, "error": "密码错误"}

        save_deepseek_api_key(data.get("api_key", ""))
        return {"success": True, "has_api_key": bool(str(data.get("api_key") or "").strip())}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================= 产品描述模板 =================

@app.get("/api/description-templates")
def api_list_description_templates():
    try:
        return {"success": True, "templates": list_description_templates()}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/description-templates/{template_name}")
def api_get_description_template(template_name: str):
    try:
        return {
            "success": True,
            "template_name": template_name,
            "content": get_description_template(template_name),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/description-templates/{template_name}")
def api_save_description_template(template_name: str, data: dict):
    try:
        saved = save_description_template(template_name, data.get("content", ""))
        return {"success": True, "template": saved}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/description-templates/{template_name}/restore-default")
def api_restore_description_template(template_name: str):
    try:
        restored = restore_default_description_template(template_name)
        return {"success": True, "template": restored}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/generate-description")
def api_generate_description(data: dict):
    try:
        template_name = str(data.get("template_name") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()

        if not template_name and profile_id:
            profile = get_profile(profile_id)
            settings = profile.get("description_settings", {}) if profile else {}
            template_name = str(settings.get("template_name") or "").strip()

        if not template_name:
            return {"success": False, "error": "template_name cannot be empty"}

        template = get_description_template(template_name)
        order_data = data.get("data", {})
        message = str(data.get("message") or "").strip()

        if not message:
            return {"success": False, "error": "message不能为空，产品描述需要客户聊天内容才能 AI 生成"}

        description_result = generate_description_from_message(message, template, order_data)

        return {
            "success": True,
            "template_name": template_name,
            "used_ai": True,
            "description_text": description_result.get("description_text", ""),
            "description_fields": description_result.get("description_fields", {}),
            "ingredient_initials": description_result.get("ingredient_initials", ""),
            "debug_message_length": len(message),
            "debug_template_length": len(template),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ================= AI解析 =================

@app.post("/api/parse")
def api_parse(data: dict):
    try:
        message = data.get("message", "").strip()

        if not message:
            return {"success": False, "error": "message不能为空"}

        return {"success": True, "data": parse_message(message)}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ================= Excel生成 =================

@app.post("/api/generate-excel")
def api_generate_excel(data: dict):
    global LAST_GENERATED_FILE_PATH
    try:
        profile_id = data.get("profile_id", "")
        order_data = data.get("data", {})
        description_fields = data.get("description_fields", {})
        if isinstance(order_data, dict) and not str(order_data.get("ingredient_initials") or "").strip():
            ingredient_initials = extract_ingredient_initials_from_description_fields(description_fields)
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
            description_fields=description_fields,
        )
        if result.get("success") and str(result.get("lastGeneratedFilePath") or result.get("output_path") or "").strip():
            LAST_GENERATED_FILE_PATH = str(result.get("lastGeneratedFilePath") or result.get("output_path") or "").strip()
        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/sync-output")
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


@app.post("/api/open-output-folder")
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


@app.get("/api/download/{filename}")
def api_download(filename: str):
    safe_filename = Path(str(filename or "")).name
    return FileResponse(OUTPUT_DIR / safe_filename)
