from pathlib import Path

from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.field_library import (
    load_fields,
    add_field,
    update_field,
    toggle_field_enabled,
    delete_field
)
from app.ai_parser import parse_message
from app.excel_generator import generate_excel
from app.description_template_manager import (
    list_description_templates,
    get_description_template,
    save_description_template,
    render_description_template,
)
from app.template_manager import (
    load_profiles,
    get_profile,
    create_profile,
    delete_profile,
    update_profile_mappings,
    upload_template_file
)

# ✅ 关键：必须在最前面
app = FastAPI(title="AI Order System V2")

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/config")
def config_page():
    return FileResponse(STATIC_DIR / "config.html")


@app.get("/config/new-profile")
def new_profile_page():
    return FileResponse(STATIC_DIR / "new_profile.html")


@app.get("/config/fields")
def fields_page():
    return FileResponse(STATIC_DIR / "fields.html")


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


@app.post("/api/fields/{key}/toggle")
def api_toggle_field(key: str):
    try:
        return {"success": True, "field": toggle_field_enabled(key)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.delete("/api/fields/{key}")
def api_delete_field(key: str):
    try:
        return {"success": True, "result": delete_field(key)}
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
        return {"success": True, "profile": upload_template_file(profile_id, file)}
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
                composite_mappings=data.get("composite_mappings", []),
                document_no_settings=data.get("document_no_settings"),
                mapping_defaults=data.get("mapping_defaults"),
                description_settings=data.get("description_settings"),
            )
        }
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
        rendered = render_description_template(template, data.get("data", {}))

        return {
            "success": True,
            "template_name": template_name,
            "description_text": rendered,
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
    try:
        profile_id = data.get("profile_id", "")
        order_data = data.get("data", {})
        # 兼容新旧字段名：优先 composite_data，其次 composite_values
        composite_data = data.get("composite_data")
        if composite_data is None:
            composite_data = data.get("composite_values", [])

        return generate_excel(
            data=order_data,
            profile_id=profile_id,
            composite_data=composite_data,
            description_text=data.get("description_text")
        )

    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/download/{filename}")
def api_download(filename: str):
    return FileResponse(OUTPUT_DIR / filename)
