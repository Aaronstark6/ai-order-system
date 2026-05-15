from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, UploadFile

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

from app.excel_geometry import get_template_geometry
from app.template_manager import (
    create_profile,
    delete_profile,
    delete_template_file,
    get_profile,
    load_profiles,
    update_profile_mappings,
    upload_template_file,
)


router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "static"
LAYOUT_PREVIEW_DIR = STATIC_DIR / "layout_previews"


@router.get("/api/template-profiles")
def api_get_profiles():
    return {"success": True, "profiles": load_profiles()}


@router.post("/api/template-profiles")
def api_create_profile(data: dict):
    try:
        return {"success": True, "profile": create_profile(data.get("name", ""))}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.delete("/api/template-profiles/{profile_id}")
def api_delete_profile(profile_id: str):
    try:
        return {"success": True, "result": delete_profile(profile_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/template-profiles/{profile_id}/upload-template")
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


@router.post("/api/template-profiles/{profile_id}/layout-preview")
def api_upload_layout_preview(profile_id: str, file: UploadFile = File(...)):
    try:
        if PILImage is None:
            return {"success": False, "error": "图片预览需要安装 pillow"}

        profile = get_profile(profile_id)
        if not profile:
            return {"success": False, "error": "映射不存在"}

        original_name = file.filename or "preview.png"
        suffix = Path(original_name).suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            return {"success": False, "error": "只支持上传 png、jpg、jpeg 图片"}

        LAYOUT_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"preview_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
        target_path = LAYOUT_PREVIEW_DIR / filename

        with PILImage.open(file.file) as image:
            width, height = image.size
            image.convert("RGBA").save(target_path, format="PNG")

        image_path = str(Path("static") / "layout_previews" / filename).replace("\\", "/")
        layout_preview = {
            "enabled": True,
            "image_path": image_path,
            "image_width": width,
            "image_height": height,
        }
        profile = update_profile_mappings(
            profile_id=profile_id,
            mappings=None,
            layout_preview=layout_preview,
        )
        return {
            "success": True,
            "image_path": image_path,
            "image_width": width,
            "image_height": height,
            "profile": profile,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/api/template-profiles/{profile_id}/geometry")
def api_get_template_geometry(profile_id: str):
    return get_template_geometry(profile_id)


@router.delete("/api/template-profiles/{profile_id}/template")
def api_delete_template_file(profile_id: str):
    try:
        return {"success": True, "profile": delete_template_file(profile_id)}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/template-profiles/{profile_id}/mappings")
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
                layout_preview=data.get("layout_preview"),
                mapping_order=data.get("mapping_order"),
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/template-profiles/{profile_id}/layout-config")
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
                layout_preview=data.get("layout_preview"),
            )
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
