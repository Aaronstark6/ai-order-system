from fastapi import APIRouter

from app.logger import get_logger
from app.v4_schema import get_product_form, get_product_forms, load_product_schema


router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/v4/product-schema")
def api_v4_product_schema():
    logger.info("V4 product schema requested")
    return {
        "success": True,
        "data": load_product_schema(),
    }


@router.get("/api/v4/product-forms")
def api_v4_product_forms():
    logger.info("V4 product forms requested")
    return {
        "success": True,
        "data": get_product_forms(),
    }


@router.get("/api/v4/product-forms/{form_key}")
def api_v4_product_form(form_key: str):
    product_forms = get_product_forms()
    if form_key not in product_forms:
        logger.info("V4 product form not found: form_key=%s", form_key)
        return {
            "success": False,
            "error": "产品形式不存在",
        }

    logger.info("V4 product form requested: form_key=%s", form_key)
    return {
        "success": True,
        "data": get_product_form(form_key),
    }
