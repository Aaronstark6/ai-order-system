import os
import shutil
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.ai_parser import parse_customer_text
from app.excel_generator import generate_excel
from app.config import (
    get_fields,
    add_field,
    update_field,
    delete_field,
    set_field_enabled,
    get_template_mappings,
    get_template_mapping,
    save_template_mapping,
    delete_template_mapping,
)


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

os.makedirs(TEMPLATE_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="AI Order System")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# =========================
# 页面
# =========================

@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# =========================
# 字段库 V2.1
# =========================

class FieldCreateRequest(BaseModel):
    field_key: str
    label: str
    description: Optional[str] = ""
    type: Optional[str] = "text"
    required: Optional[bool] = False
    enabled: Optional[bool] = True


class FieldUpdateRequest(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    required: Optional[bool] = None
    enabled: Optional[bool] = None


class FieldEnableRequest(BaseModel):
    enabled: bool


@app.get("/api/fields")
def api_get_fields():
    return {
        "success": True,
        "fields": get_fields()
    }


@app.post("/api/fields")
def api_add_field(req: FieldCreateRequest):
    try:
        field = add_field(
            req.field_key,
            {
                "label": req.label,
                "description": req.description,
                "type": req.type,
                "required": req.required,
                "enabled": req.enabled,
            }
        )

        return {
            "success": True,
            "field": field
        }

    except ValueError as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.put("/api/fields/{field_key}")
def api_update_field(field_key: str, req: FieldUpdateRequest):
    try:
        field = update_field(
            field_key,
            {
                "label": req.label,
                "description": req.description,
                "type": req.type,
                "required": req.required,
                "enabled": req.enabled,
            }
        )

        return {
            "success": True,
            "field": field
        }

    except ValueError as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.delete("/api/fields/{field_key}")
def api_delete_field(field_key: str):
    try:
        deleted = delete_field(field_key)

        return {
            "success": True,
            "deleted": deleted
        }

    except ValueError as e:
        return {
            "success": False,
            "message": str(e)
        }


@app.patch("/api/fields/{field_key}/enable")
def api_set_field_enabled(field_key: str, req: FieldEnableRequest):
    try:
        field = set_field_enabled(field_key, req.enabled)

        return {
            "success": True,
            "field": field
        }

    except ValueError as e:
        return {
            "success": False,
            "message": str(e)
        }


# =========================
# 模板上传
# =========================

@app.post("/api/upload-template")
async def upload_template(file: UploadFile = File(...)):
    filename = file.filename

    if not filename:
        return {
            "success": False,
            "message": "文件名不能为空"
        }

    if not filename.endswith(".xlsx"):
        return {
            "success": False,
            "message": "只支持 .xlsx 文件"
        }

    save_path = os.path.join(TEMPLATE_DIR, filename)

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "success": True,
        "message": "模板上传成功",
        "filename": filename
    }


@app.get("/api/templates")
def list_templates():
    files = []

    for filename in os.listdir(TEMPLATE_DIR):
        if filename.endswith(".xlsx"):
            files.append(filename)

    return {
        "success": True,
        "templates": files
    }


# =========================
# 多模板映射
# =========================

class TemplateMappingRequest(BaseModel):
    template_id: str
    template_file: Optional[str] = ""
    mappings: dict = {}
    combined_mappings: dict = {}


@app.get("/api/template-mappings")
def api_get_template_mappings():
    return {
        "success": True,
        "template_mappings": get_template_mappings()
    }


@app.get("/api/template-mappings/{template_id}")
def api_get_template_mapping(template_id: str):
    return {
        "success": True,
        "template_id": template_id,
        "mapping": get_template_mapping(template_id)
    }


@app.post("/api/template-mappings")
def api_save_template_mapping(req: TemplateMappingRequest):
    data = {
        "template_file": req.template_file,
        "mappings": req.mappings,
        "combined_mappings": req.combined_mappings,
    }

    save_template_mapping(req.template_id, data)

    return {
        "success": True,
        "message": "模板映射保存成功",
        "template_id": req.template_id,
        "mapping": data
    }


@app.delete("/api/template-mappings/{template_id}")
def api_delete_template_mapping(template_id: str):
    deleted = delete_template_mapping(template_id)

    return {
        "success": True,
        "deleted": deleted
    }


# =========================
# AI 解析
# =========================

class ParseRequest(BaseModel):
    text: str


@app.post("/api/parse")
def api_parse(req: ParseRequest):
    try:
        data = parse_customer_text(req.text)

        return {
            "success": True,
            "data": data
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"AI解析失败：{str(e)}"
        }


# =========================
# 生成 Excel
# =========================

class GenerateExcelRequest(BaseModel):
    template_id: str
    data: dict


@app.post("/api/generate-excel")
def api_generate_excel(req: GenerateExcelRequest):
    try:
        mapping = get_template_mapping(req.template_id)

        if not mapping:
            return {
                "success": False,
                "message": "未找到模板映射"
            }

        template_file = mapping.get("template_file")

        if not template_file:
            return {
                "success": False,
                "message": "模板映射中没有绑定 Excel 模板文件"
            }

        template_path = os.path.join(TEMPLATE_DIR, template_file)

        if not os.path.exists(template_path):
            return {
                "success": False,
                "message": f"Excel模板文件不存在：{template_file}"
            }

        output_filename = f"order_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        output_path = os.path.join(OUTPUT_DIR, output_filename)

        generate_excel(
            template_path=template_path,
            output_path=output_path,
            data=req.data,
            mappings=mapping.get("mappings", {}),
            combined_mappings=mapping.get("combined_mappings", {}),
        )

        return {
            "success": True,
            "message": "Excel生成成功",
            "download_url": f"/api/download/{output_filename}"
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"Excel生成失败：{str(e)}"
        }


@app.get("/api/download/{filename}")
def download_file(filename: str):
    file_path = os.path.join(OUTPUT_DIR, filename)

    if not os.path.exists(file_path):
        return {
            "success": False,
            "message": "文件不存在"
        }

    return FileResponse(
        file_path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
