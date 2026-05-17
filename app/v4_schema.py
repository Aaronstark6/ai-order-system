"""V4 Product Type System - Product schema management with product types."""

import json
import shutil
from datetime import datetime
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_product_schema_path():
    return get_base_dir() / "v4" / "schemas" / "product_schema.json"


def _migrate_old_schema(schema):
    """Migrate old schema (with global fields) to new product_types structure."""
    if "product_types" in schema:
        return schema

    old_fields = schema.get("fields", [])
    default_product_type = {
        "key": "default",
        "name": "默认产品类型",
        "description": "从旧版迁移的默认产品类型",
        "fields": old_fields if isinstance(old_fields, list) else [],
    }

    migrated_schema = {
        "product_types": [default_product_type],
        "version": "v4-core.1",
        "migrated_from": "old_fields_structure",
    }

    if "product_forms" in schema:
        migrated_schema["product_forms"] = schema["product_forms"]
    if "description_template" in schema:
        migrated_schema["description_template"] = schema["description_template"]

    logger.info("V4 schema migrated from old structure to product_types")
    return migrated_schema


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

    schema = _migrate_old_schema(schema)
    return schema


def save_product_schema(schema: dict) -> dict:
    schema_path = _get_product_schema_path()
    backup_dir = schema_path.parent / "backups"

    logger.info("V4 product schema save started: path=%s", schema_path)
    try:
        if not isinstance(schema, dict):
            raise ValueError("schema must be a dict")

        schema = _migrate_old_schema(schema)

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
    return fields if isinstance(fields, list) else []


def get_all_fields():
    """Get all fields from all product types (for backward compatibility)."""
    product_types = get_product_types()
    all_fields = []
    for pt in product_types:
        fields = pt.get("fields", [])
        if isinstance(fields, list):
            all_fields.extend(fields)
    return all_fields


def get_default_product_type():
    """Get the first product type or create a default one."""
    product_types = get_product_types()
    if product_types:
        return product_types[0]
    return {
        "key": "default",
        "name": "默认产品类型",
        "description": "默认产品类型",
        "fields": [],
    }


def add_product_type(product_type):
    """Add a new product type to the schema."""
    if not isinstance(product_type, dict):
        return {"success": False, "error": "product_type must be a dict"}

    key = product_type.get("key", "").strip()
    if not key:
        return {"success": False, "error": "product_type key cannot be empty"}

    name = product_type.get("name", "").strip()
    if not name:
        return {"success": False, "error": "product_type name cannot be empty"}

    existing = get_product_type(key)
    if existing:
        return {"success": False, "error": f"product_type with key '{key}' already exists"}

    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    new_product_type = {
        "key": key,
        "name": name,
        "description": product_type.get("description", ""),
        "fields": product_type.get("fields", []),
    }

    product_types.append(new_product_type)
    schema["product_types"] = product_types

    return save_product_schema(schema)


def update_product_type(product_type_key, updates):
    """Update an existing product type."""
    if not isinstance(updates, dict):
        return {"success": False, "error": "updates must be a dict"}

    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    for i, pt in enumerate(product_types):
        if pt.get("key") == product_type_key:
            if "name" in updates:
                pt["name"] = updates["name"].strip()
            if "description" in updates:
                pt["description"] = updates["description"]
            if "fields" in updates and isinstance(updates["fields"], list):
                pt["fields"] = updates["fields"]
            product_types[i] = pt
            schema["product_types"] = product_types
            return save_product_schema(schema)

    return {"success": False, "error": f"product_type with key '{product_type_key}' not found"}


def delete_product_type(product_type_key):
    """Delete a product type from the schema."""
    schema = load_product_schema()
    product_types = schema.get("product_types", [])

    if len(product_types) <= 1:
        return {"success": False, "error": "cannot delete the last product type"}

    original_count = len(product_types)
    product_types = [pt for pt in product_types if pt.get("key") != product_type_key]

    if len(product_types) == original_count:
        return {"success": False, "error": f"product_type with key '{product_type_key}' not found"}

    schema["product_types"] = product_types
    return save_product_schema(schema)


def add_field_to_product_type(product_type_key, field):
    """Add a field to a specific product type."""
    if not isinstance(field, dict):
        return {"success": False, "error": "field must be a dict"}

    field_key = field.get("key", "").strip()
    if not field_key:
        return {"success": False, "error": "field key cannot be empty"}

    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"product_type '{product_type_key}' not found"}

    fields = product_type.get("fields", [])
    for f in fields:
        if f.get("key") == field_key:
            return {"success": False, "error": f"field with key '{field_key}' already exists in product type"}

    fields.append(field)
    return update_product_type(product_type_key, {"fields": fields})


def update_field_in_product_type(product_type_key, field_key, updates):
    """Update a field in a specific product type."""
    if not isinstance(updates, dict):
        return {"success": False, "error": "updates must be a dict"}

    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"product_type '{product_type_key}' not found"}

    fields = product_type.get("fields", [])
    for i, f in enumerate(fields):
        if f.get("key") == field_key:
            if "key" in updates:
                f["key"] = updates["key"].strip()
            if "name" in updates:
                f["name"] = updates["name"]
            if "type" in updates:
                f["type"] = updates["type"]
            if "required" in updates:
                f["required"] = bool(updates["required"])
            if "default" in updates:
                f["default"] = updates["default"]
            fields[i] = f
            return update_product_type(product_type_key, {"fields": fields})

    return {"success": False, "error": f"field '{field_key}' not found in product type '{product_type_key}'"}


def delete_field_from_product_type(product_type_key, field_key):
    """Delete a field from a specific product type."""
    product_type = get_product_type(product_type_key)
    if not product_type:
        return {"success": False, "error": f"product_type '{product_type_key}' not found"}

    fields = product_type.get("fields", [])
    original_count = len(fields)
    fields = [f for f in fields if f.get("key") != field_key]

    if len(fields) == original_count:
        return {"success": False, "error": f"field '{field_key}' not found in product type '{product_type_key}'"}

    return update_product_type(product_type_key, {"fields": fields})


def get_product_forms():
    product_forms = load_product_schema().get("product_forms", {})
    return product_forms if isinstance(product_forms, dict) else {}


def get_product_form(form_key):
    form = get_product_forms().get(form_key, {})
    return form if isinstance(form, dict) else {}
