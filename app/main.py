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


@app.get("/api/health")
def health_check():
    return {
        "success": True,
        "message": "AI Order System V2 is running"
    }


@app.get("/api/fields")
def api_get_fields():
    return {
        "success": True,
        "fields": load_fields()
    }


@app.post("/api/fields")
def api_add_field(field: dict):
    try:
        saved_field = add_field(field)

        return {
            "success": True,
            "field": saved_field
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.put("/api/fields/{key}")
def api_update_field(key: str, field: dict):
    try:
        updated_field = update_field(key, field)

        return {
            "success": True,
            "field": updated_field
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/fields/{key}/toggle")
def api_toggle_field_enabled(key: str):
    try:
        field = toggle_field_enabled(key)

        return {
            "success": True,
            "field": field
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete("/api/fields/{key}")
def api_delete_field(key: str):
    try:
        result = delete_field(key)

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/template-profiles")
def api_get_template_profiles():
    return {
        "success": True,
        "profiles": load_profiles()
    }


@app.post("/api/template-profiles")
def api_create_template_profile(data: dict):
    try:
        name = data.get("name", "")
        profile = create_profile(name)

        return {
            "success": True,
            "profile": profile
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete("/api/template-profiles/{profile_id}")
def api_delete_template_profile(profile_id: str):
    try:
        result = delete_profile(profile_id)

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/template-profiles/{profile_id}/upload-template")
def api_upload_template(profile_id: str, file: UploadFile = File(...)):
    try:
        profile = upload_template_file(profile_id, file)

        return {
            "success": True,
            "profile": profile
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/template-profiles/{profile_id}/mappings")
def api_update_template_profile_mappings(profile_id: str, data: dict):
    try:
        mappings = data.get("mappings", {})
        composite_mappings = data.get("composite_mappings", [])

        if not isinstance(mappings, dict):
            return {
                "success": False,
                "error": "mappings 必须是对象格式"
            }

        if not isinstance(composite_mappings, list):
            return {
                "success": False,
                "error": "composite_mappings 必须是数组格式"
            }

        profile = update_profile_mappings(
            profile_id=profile_id,
            mappings=mappings,
            composite_mappings=composite_mappings
        )

        return {
            "success": True,
            "profile": profile
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
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
def api_generate_excel(data: dict):
    try:
        profile_id = data.get("profile_id", "")
        order_data = data.get("data", {})

        if not profile_id:
            return {
                "success": False,
                "error": "请选择模板映射"
            }

        if not isinstance(order_data, dict):
            return {
                "success": False,
                "error": "订单数据格式错误"
            }

        result = generate_excel(order_data, profile_id)
        return result

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.get("/api/download/{filename}")
def api_download_file(filename: str):
    file_path = OUTPUT_DIR / filename

    if not file_path.exists():
        return {
            "success": False,
            "error": "文件不存在"
        }

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
