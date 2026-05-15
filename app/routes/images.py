import re
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, UploadFile

from app.logger import get_logger
from app.image_manager import (
    ensure_image_upload_dir,
    load_image_fields,
    safe_image_extension,
    save_image_fields,
    save_pool_image,
)


router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/image-fields")
def api_get_image_fields():
    try:
        return {"success": True, "fields": load_image_fields()}
    except Exception as e:
        logger.exception("Load image fields failed")
        return {"success": False, "error": str(e)}


@router.post("/api/image-fields")
def api_save_image_fields(data: dict):
    try:
        fields = data.get("fields", data)
        if not isinstance(fields, list):
            logger.warning("Save image fields rejected: fields is not a list")
            return {"success": False, "error": "图片字段配置必须是数组"}
        return {"success": True, "fields": save_image_fields(fields)}
    except Exception as e:
        logger.exception("Save image fields failed")
        return {"success": False, "error": str(e)}


@router.post("/api/upload-image")
def api_upload_image(field_key: str = Form(...), file: UploadFile = File(...)):
    try:
        original_key = str(field_key or "").strip()
        safe_key = re.sub(r"[^A-Za-z0-9_-]+", "_", original_key).strip("_")
        if not original_key or not safe_key:
            logger.warning("Fixed image upload rejected: empty field_key")
            return {"success": False, "error": "field_key 不能为空"}

        logger.info("Fixed image upload started: field_key=%s filename=%s", original_key, file.filename)
        ext = safe_image_extension(file.filename)
        upload_dir = ensure_image_upload_dir()
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{safe_key}{ext}"
        image_file = upload_dir / filename

        with open(image_file, "wb") as f:
            shutil.copyfileobj(file.file, f)

        logger.info("Fixed image upload succeeded: field_key=%s path=%s", original_key, image_file)
        return {
            "success": True,
            "field_key": original_key,
            "image_path": str(Path("uploads") / "images" / filename),
            "filename": filename,
        }
    except Exception as e:
        logger.exception("Fixed image upload failed")
        return {"success": False, "error": str(e)}


@router.post("/api/image-pool/upload")
def api_upload_image_pool(file: UploadFile = File(...)):
    try:
        logger.info("Image Pool upload started: filename=%s", file.filename)
        saved = save_pool_image(file)
        filename = saved.get("filename") or ""
        key = Path(filename).stem
        logger.info("Image Pool upload succeeded: key=%s path=%s", key, saved.get("image_path") or "")
        return {
            "success": True,
            "item": {
                "key": key,
                "label": saved.get("original_name") or filename,
                "image_path": saved.get("image_path") or "",
                "filename": filename,
            }
        }
    except Exception as e:
        logger.exception("Image Pool upload failed")
        return {"success": False, "error": str(e)}
