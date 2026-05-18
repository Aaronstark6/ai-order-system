import json
import shutil
from copy import deepcopy
from datetime import datetime
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_schema_version import get_current_schema_version


logger = get_logger(__name__)


DEFAULT_ORDER_OBJECT = {
    "schema_version": get_current_schema_version(),
    "customer": {
        "name": "",
        "country": "",
        "type": "",
    },
    "order": {
        "order_no": "",
        "quantity": "",
        "order_date": "",
        "sales_owner": "",
    },
    "product": {
        "product_type": "",
        "product_name": "",
        "fields": {},
        "tables": {},
    },
    "document": {
        "salesperson_code": "",
        "company_code": "",
        "sequence": "",
        "ingredient_initials": "",
    },
}


def _get_order_object_path():
    return get_base_dir() / "v4" / "examples" / "order_object.json"


def _find_product_type(product_type_value):
    from app.v4_schema import get_product_types

    product_type_value = str(product_type_value or "").strip()
    if not product_type_value:
        return {}

    for product_type in get_product_types():
        if not isinstance(product_type, dict):
            continue
        key = str(product_type.get("key") or "").strip()
        name = str(product_type.get("name") or "").strip()
        if product_type_value in {key, name}:
            return product_type

    return {}


def _normalize_product_fields(product_type, source_fields):
    if not isinstance(source_fields, dict):
        return {}

    fields = product_type.get("fields", []) if isinstance(product_type, dict) else []
    field_key_by_identifier = {}
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict):
                continue
            key = str(field.get("key") or "").strip()
            name = str(field.get("name") or "").strip()
            if key:
                field_key_by_identifier[key] = key
            if name and key:
                field_key_by_identifier[name] = key

    normalized_fields = {}
    for source_key, value in source_fields.items():
        normalized_key = field_key_by_identifier.get(str(source_key).strip(), str(source_key).strip())
        if normalized_key:
            normalized_fields[normalized_key] = "" if value is None else str(value)

    return normalized_fields


def _normalize_order_object(data):
    normalized = deepcopy(DEFAULT_ORDER_OBJECT)
    if not isinstance(data, dict):
        return normalized

    normalized["schema_version"] = str(data.get("schema_version") or get_current_schema_version()).strip() or get_current_schema_version()

    for section, defaults in DEFAULT_ORDER_OBJECT.items():
        if section == "schema_version":
            continue
        source_section = data.get(section, {})
        if not isinstance(source_section, dict):
            continue

        for key, default_value in defaults.items():
            value = source_section.get(key, default_value)
            if section == "product" and key in {"fields", "tables"}:
                normalized[section][key] = value if isinstance(value, dict) else {}
            else:
                normalized[section][key] = "" if value is None else str(value)

    product_type = _find_product_type(normalized["product"]["product_type"])
    if product_type:
        normalized["product"]["product_type"] = str(product_type.get("key") or normalized["product"]["product_type"])
    normalized["product"]["fields"] = _normalize_product_fields(
        product_type,
        normalized["product"]["fields"],
    )

    return normalized


def load_order_object():
    order_object_path = _get_order_object_path()
    if not order_object_path.exists():
        logger.info("V4 order object not found, creating default: path=%s", order_object_path)
        save_result = save_order_object(DEFAULT_ORDER_OBJECT, create_backup=False)
        if not save_result.get("success"):
            return deepcopy(DEFAULT_ORDER_OBJECT)
        return save_result["data"]

    try:
        with order_object_path.open("r", encoding="utf-8") as f:
            raw_data = json.load(f)
    except JSONDecodeError as exc:
        logger.error("V4 order object JSON parse failed: path=%s error=%s", order_object_path, exc)
        return deepcopy(DEFAULT_ORDER_OBJECT)
    except OSError as exc:
        logger.error("V4 order object read failed: path=%s error=%s", order_object_path, exc)
        return deepcopy(DEFAULT_ORDER_OBJECT)

    return _normalize_order_object(raw_data)


def save_order_object(order_object, create_backup=True):
    order_object_path = _get_order_object_path()
    backup_dir = order_object_path.parent / "backups"
    normalized = _normalize_order_object(order_object)

    logger.info("V4 order object save started: path=%s", order_object_path)
    try:
        order_object_path.parent.mkdir(parents=True, exist_ok=True)
        if create_backup and order_object_path.exists():
            backup_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"order_object_{timestamp}.json"
            shutil.copy2(order_object_path, backup_path)
            logger.info("V4 order object backup created: path=%s", backup_path)

        with order_object_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("V4 order object save succeeded: path=%s", order_object_path)
        return {
            "success": True,
            "data": normalized,
        }
    except Exception as exc:
        logger.exception("V4 order object save failed: path=%s", order_object_path)
        return {
            "success": False,
            "error": str(exc),
        }
