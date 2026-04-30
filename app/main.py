from pathlib import Path
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.field_library import load_fields, add_field, delete_field
from app.ai_parser import parse_message
from app.excel_generator import generate_excel
from app.template_manager import (
    load_profiles,
    create_profile,
    delete_profile,
    update_profile_mappings,
    upload_template_file
)

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


@app.get("/api/fields")
def api_get_fields():
    return {"success": True, "fields": load_fields()}


@app.post("/api/fields")
def api_add_field(field: dict):
    return {"success": True, "field": add_field(field)}


@app.delete("/api/fields/{key}")
def api_delete_field(key: str):
    return {"success": True, "result": delete_field(key)}


@app.get("/api/template-profiles")
def api_get_profiles():
    return {"success": True, "profiles": load_profiles()}


@app.post("/api/template-profiles")
def api_create_profile(data: dict):
    return {"success": True, "profile": create_profile(data.get("name", ""))}


@app.delete("/api/template-profiles/{profile_id}")
def api_delete_profile(profile_id: str):
    return {"success": True, "result": delete_profile(profile_id)}


@app.post("/api/template-profiles/{profile_id}/upload-template")
def api_upload_template(profile_id: str, file: UploadFile = File(...)):
    return {"success": True, "profile": upload_template_file(profile_id, file)}


@app.post("/api/template-profiles/{profile_id}/mappings")
def api_update_mappings(profile_id: str, data: dict):
    return {
        "success": True,
        "profile": update_profile_mappings(
            profile_id,
            data.get("mappings", {}),
            data.get("composite_mappings", [])
        )
    }


@app.post("/api/parse")
def api_parse(data: dict):
    try:
        message = data.get("message", "")

        if not isinstance(message, str):
            message = str(message)

        message = message.strip()

        if not message:
            return {
                "success": False,
                "error": "message不能为空"
            }

        result = parse_message(message)

        return {
            "success": True,
            "data": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/api/generate-excel")
def api_generate(data: dict):
    return generate_excel(data.get("data", {}), data.get("profile_id", ""))


@app.get("/api/download/{filename}")
def download(filename: str):
    return FileResponse(OUTPUT_DIR / filename)
