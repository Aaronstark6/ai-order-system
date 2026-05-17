import json
import hashlib
import re
import shutil
import unicodedata
from datetime import datetime
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_product_schema_path():
    return get_base_dir() / "v4" / "schemas" / "product_schema.json"


def _migrate_old_schema_to_product_types(schema):
    """Migrate old schema (with global fields) to new product_types structure."""
    if "product_types" in schema:
        return _normalize_product_types_schema(schema)

    old_fields = schema.get("fields", [])
    default_product_type = {
        "key": "default",
        "name": "默认产品类型",
        "description": "从旧版迁移的默认产品类型",
        "fields": old_fields if isinstance(old_fields, list) else [],
    }

    migrated_schema = dict(schema)
    migrated_schema["product_types"] = [default_product_type]

    logger.info("V4 schema migrated from old structure to product_types")
    return _normalize_product_types_schema(migrated_schema)


def _slugify_ascii(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def _generate_key_from_name(name, prefix):
    """Generate an internal ASCII key, falling back for Chinese-only names."""
    cleaned_name = str(name or "").strip()
    slug = _slugify_ascii(cleaned_name)
    if slug:
        return slug

    digest = hashlib.sha1(cleaned_name.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{digest}"


def _generate_field_key(field_name):
    return _generate_key_from_name(field_name, "field")


def _generate_product_type_key(name):
    return _generate_key_from_name(name, "product_type")


def _dedupe_key(base_key, used_keys):
    key = base_key
    suffix = 2
    while key in used_keys:
        key = f"{base_key}_{suffix}"
        suffix += 1
    used_keys.add(key)
    return key


def _normalize_field(field, index, used_keys):
    if not isinstance(field, dict):
        return None

    normalized = dict(field)
    name = str(
        normalized.get("name")
        or normalized.get("field_name")
        or normalized.get("label")
        or f"未命名字段{index}"
    ).strip()
    normalized["name"] = name

    raw_key = str(normalized.get("key") or normalized.get("field_key") or "").strip()
    key = _slugify_ascii(raw_key) if raw_key else ""
    if not key:
        key = _generate_field_key(name)
    normalized["key"] = _dedupe_key(key, used_keys)

    field_type = str(normalized.get("type") or normalized.get("field_type") or "string").strip()
    normalized["type"] = field_type or "string"
    normalized["required"] = bool(normalized.get("required", False))
    normalized["description"] = str(normalized.get("description") or "").strip()
    normalized["allowed_values"] = _normalize_value_list(normalized.get("allowed_values"))
    normalized["forbidden_values"] = _normalize_value_list(normalized.get("forbidden_values"))
    normalized.pop("field_key", None)
    normalized.pop("field_name", None)

    return normalized


def _normalize_value_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    return []


def _normalize_product_types_schema(schema):
    normalized_schema = dict(schema)
    product_types = normalized_schema.get("product_types", [])
    if not isinstance(product_types, list):
        normalized_schema["product_types"] = []
        return normalized_schema

    normalized_product_types = []
    used_type_keys = set()
    for index, product_type in enumerate(product_types, start=1):
        if not isinstance(product_type, dict):
            continue

        normalized_type = dict(product_type)
        type_name = str(
            normalized_type.get("name") or normalized_type.get("label") or f"产品类型{index}"
        ).strip()
        normalized_type["name"] = type_name

        raw_type_key = str(normalized_type.get("key") or "").strip()
        normalized_type["key"] = _dedupe_key(raw_type_key or _generate_product_type_key(type_name), used_type_keys)

        fields = normalized_type.get("fields", [])
        if not isinstance(fields, list):
            fields = []

        used_field_keys = set()
        normalized_fields = []
        for field_index, field in enumerate(fields, start=1):
            normalized_field = _normalize_field(field, field_index, used_field_keys)
            if normalized_field:
                normalized_fields.append(normalized_field)

        normalized_type["fields"] = normalized_fields
        normalized_product_types.append(normalized_type)

    normalized_schema["product_types"] = normalized_product_types
    return normalized_schema


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

    schema = _migrate_old_schema_to_product_types(schema)
    return schema


def save_product_schema(schema: dict) -> dict:
    schema_path = _get_product_schema_path()
    backup_dir = schema_path.parent / "backups"

    logger.info("V4 product schema save started: path=%s", schema_path)
    try:
        if not isinstance(schema, dict):
            raise ValueError("schema must be a dict")

        schema = _migrate_old_schema_to_product_types(schema)

        schema_path.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        if schema_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"product_schema_{timestamp}.json"
            logger.info("V4 product schema backup path: path=%s", backup_path)
            shutil.copy2(schema_path, backup_path)
        else:
            logger.info("V4 product schema backup path: no existing schema to backup")

        with schema_path.open("w", encoding="utf-8") as f:
            json.dump(schema, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("V4 product schema save succeeded: path=%s", schema_path)
        return {
            "success": True,
            "data": schema,
        }
    except Exception as exc:
        logger.exception("V4 product schema save failed: path=%s", schema_path)
        return {
            "success": False,
            "error": str(exc),
        }


def get_product_types():
    """Get all product types from schema."""
    schema = load_product_schema()
    product_types = schema.get("product_types", [])
    return product_types if isinstance(product_types, list) else []


def get_product_type(product_type_key):
    """Get a specific product type by key."""
    product_types = get_product_types()
    for pt in product_types:
        if pt.get("key") == product_type_key:
            return pt
    return {}


def get_product_type_fields(product_type_key):
    """Get fields for a specific product type."""
    product_type = get_product_type(product_type_key)
    fields = product_type.get("fields", [])
    if not isinstance(fields, list):
        return []
    
    fixed_fields = []
    for f in fields:
        if isinstance(f, dict):
            if "key" not in f:
                f["key"] = f"field_{len(fixed_fields) + 1}"
            if "name" not in f:
                f["name"] = f.get("field_name", "未命名字段")
            fixed_fields.append(f)
    
    return fixed_fields


def add_product_type(name, description=""):
    """Add a new product type."""
    if not name or not name.strip():
        return {"success": False, "error": "产品类型名称不能为空"}

    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    key = _generate_product_type_key(name)
    if not key:
        return {"success": False, "error": "无法从名称生成标识"}

    for pt in product_types:
        if pt.get("key") == key:
            return {"success": False, "error": f"产品类型 '{name}' 已存在"}

    new_product_type = {
        "key": key,
        "name": name.strip(),
        "description": description.strip() if description else "",
        "fields": [],
    }

    product_types.append(new_product_type)
    schema["product_types"] = product_types

    return save_product_schema(schema)


def update_product_type(product_type_key, name=None, description=None):
    """Update an existing product type."""
    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    for i, pt in enumerate(product_types):
        if pt.get("key") == product_type_key:
            if name is not None and name.strip():
                pt["name"] = name.strip()
            if description is not None:
                pt["description"] = description.strip() if description else ""
            product_types[i] = pt
            schema["product_types"] = product_types
            return save_product_schema(schema)

    return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}


def delete_product_type(product_type_key):
    """Delete a product type."""
    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    if len(product_types) <= 1:
        return {"success": False, "error": "不能删除最后一个产品类型"}

    original_count = len(product_types)
    product_types = [pt for pt in product_types if pt.get("key") != product_type_key]

    if len(product_types) == original_count:
        return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}

    schema["product_types"] = product_types
    return save_product_schema(schema)


def add_field_to_product_type(
    product_type_key,
    field_name,
    field_type="string",
    required=False,
    description="",
    allowed_values=None,
    forbidden_values=None,
):
    """Add a field to a specific product type."""
    if not field_name or not field_name.strip():
        return {"success": False, "error": "字段名称不能为空"}

    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}

    field_key = _generate_field_key(field_name)
    if not field_key:
        return {"success": False, "error": "无法从名称生成标识"}

    fields = product_type.get("fields", [])
    for f in fields:
        if f.get("key") == field_key:
            return {"success": False, "error": f"字段 '{field_name}' 已存在"}

    new_field = {
        "key": field_key,
        "name": field_name.strip(),
        "type": field_type if field_type else "string",
        "required": bool(required),
        "description": description.strip() if description else "",
        "allowed_values": _normalize_value_list(allowed_values),
        "forbidden_values": _normalize_value_list(forbidden_values),
    }

    fields.append(new_field)
    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    for i, pt in enumerate(product_types):
        if pt.get("key") == product_type_key:
            pt["fields"] = fields
            product_types[i] = pt
            schema["product_types"] = product_types
            return save_product_schema(schema)

    return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}


def update_field_in_product_type(
    product_type_key,
    field_key,
    field_name=None,
    field_type=None,
    required=None,
    description=None,
    allowed_values=None,
    forbidden_values=None,
):
    """Update a field in a product type."""
    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}

    fields = product_type.get("fields", [])
    for i, f in enumerate(fields):
        if f.get("key") == field_key:
            if field_name is not None and field_name.strip():
                f["name"] = field_name.strip()
            if field_type is not None:
                f["type"] = field_type
            if required is not None:
                f["required"] = bool(required)
            if description is not None:
                f["description"] = description.strip() if description else ""
            if allowed_values is not None:
                f["allowed_values"] = _normalize_value_list(allowed_values)
            if forbidden_values is not None:
                f["forbidden_values"] = _normalize_value_list(forbidden_values)
            fields[i] = f
            schema = load_product_schema()
            product_types = schema.get("product_types", [])
            for j, pt in enumerate(product_types):
                if pt.get("key") == product_type_key:
                    pt["fields"] = fields
                    product_types[j] = pt
                    schema["product_types"] = product_types
                    return save_product_schema(schema)

    return {"success": False, "error": f"字段 '{field_key}' 不存在"}


def delete_field_from_product_type(product_type_key, field_key):
    """Delete a field from a product type."""
    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}

    fields = product_type.get("fields", [])
    original_count = len(fields)
    fields = [f for f in fields if f.get("key") != field_key]

    if len(fields) == original_count:
        return {"success": False, "error": f"字段 '{field_key}' 不存在"}

    schema = load_product_schema()
    product_types = schema.get("product_types", [])
    for i, pt in enumerate(product_types):
        if pt.get("key") == product_type_key:
            pt["fields"] = fields
            product_types[i] = pt
            schema["product_types"] = product_types
            return save_product_schema(schema)

    return {"success": False, "error": f"产品类型 '{product_type_key}' 不存在"}


def get_product_forms():
    product_forms = load_product_schema().get("product_forms", {})
    return product_forms if isinstance(product_forms, dict) else {}


def get_product_form(form_key):
    form = get_product_forms().get(form_key, {})
    return form if isinstance(form, dict) else {}
