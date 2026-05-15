import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_product_schema_path():
    return get_base_dir() / "v4" / "schemas" / "product_schema.json"


def load_product_schema():
    schema_path = _get_product_schema_path()
    if not schema_path.exists():
        return {}

    try:
        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
    except JSONDecodeError as exc:
        logger.error("V4 product schema JSON parse failed: path=%s error=%s", schema_path, exc)
        return {}
    except OSError as exc:
        logger.error("V4 product schema read failed: path=%s error=%s", schema_path, exc)
        return {}

    if not isinstance(schema, dict):
        logger.error("V4 product schema root must be an object: path=%s", schema_path)
        return {}

    return schema


def get_product_forms():
    product_forms = load_product_schema().get("product_forms", {})
    return product_forms if isinstance(product_forms, dict) else {}


def get_product_form(form_key):
    form = get_product_forms().get(form_key, {})
    return form if isinstance(form, dict) else {}
