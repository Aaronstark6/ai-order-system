import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_schema import get_product_types


logger = get_logger(__name__)


def _get_structured_excel_mapping_path():
    return get_base_dir() / "v4" / "rules" / "structured_excel_mapping.json"


def load_structured_excel_mapping():
    mapping_path = _get_structured_excel_mapping_path()
    try:
        with mapping_path.open("r", encoding="utf-8") as f:
            mapping = json.load(f)
    except JSONDecodeError as exc:
        logger.error("[StructuredExcelMapping] Mapping JSON parse failed: path=%s error=%s", mapping_path, exc)
        return {}
    except OSError as exc:
        logger.error("[StructuredExcelMapping] Mapping read failed: path=%s error=%s", mapping_path, exc)
        return {}

    return mapping if isinstance(mapping, dict) else {}


def _find_product_type(product_type_value):
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


def _build_field_lookup(product_type):
    lookup = {}
    fields = product_type.get("fields", []) if isinstance(product_type, dict) else []
    if not isinstance(fields, list):
        return lookup

    for field in fields:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or "").strip()
        name = str(field.get("name") or "").strip()
        if key:
            lookup[key] = key
        if key and name:
            lookup[name] = key

    return lookup


def _resolve_product_field(order_object, field_identifier):
    product = order_object.get("product", {}) if isinstance(order_object, dict) else {}
    if not isinstance(product, dict):
        return None, False

    fields = product.get("fields", {})
    if not isinstance(fields, dict):
        return None, False

    identifier = str(field_identifier or "").strip()
    if not identifier:
        return None, False

    if identifier in fields:
        return fields.get(identifier), True

    product_type = _find_product_type(product.get("product_type"))
    field_lookup = _build_field_lookup(product_type)
    mapped_key = field_lookup.get(identifier)
    if mapped_key and mapped_key in fields:
        return fields.get(mapped_key), True

    # Compatibility for old Order Object data that stored the Chinese field name directly.
    for source_key, value in fields.items():
        if str(source_key).strip() == identifier:
            return value, True

    return None, False


def _resolve_source_path(order_object, source_path):
    source_path = str(source_path or "").strip()
    if source_path.startswith("product.fields."):
        field_identifier = source_path[len("product.fields."):]
        return _resolve_product_field(order_object, field_identifier)

    current = order_object
    for part in source_path.split("."):
        if not isinstance(current, dict):
            return None, False
        if part not in current:
            return None, False
        current = current.get(part)

    return current, True


def order_object_to_structured_operations(order_object, mapping):
    warnings = []
    operations = []

    if not isinstance(order_object, dict):
        return {
            "success": False,
            "operations": [],
            "warnings": ["Order Object 必须是对象"],
        }

    mappings = mapping.get("mappings", []) if isinstance(mapping, dict) else []
    if not isinstance(mappings, list):
        return {
            "success": False,
            "operations": [],
            "warnings": ["mapping.mappings 必须是数组"],
        }

    for item in mappings:
        if not isinstance(item, dict):
            warnings.append("发现无效映射项，已跳过。")
            continue

        source_path = str(item.get("source_path") or "").strip()
        target_cell = str(item.get("target_cell") or "").strip()
        operation = str(item.get("operation") or "write_text").strip()
        label = str(item.get("label") or source_path).strip()
        if not source_path:
            warnings.append("映射项缺少 source_path，已跳过。")
            continue
        if not target_cell:
            warnings.append(f"字段 {source_path} 缺少 target_cell，已跳过。")
            continue

        value, found = _resolve_source_path(order_object, source_path)
        if not found:
            warnings.append(f"未找到字段：{source_path}")
            value = ""

        operations.append({
            "operation": operation,
            "source_path": source_path,
            "target_cell": target_cell,
            "label": label,
            "value": "" if value is None else str(value),
        })

    logger.info(
        "[StructuredExcelMapping] Operations generated: operations=%s warnings=%s",
        len(operations),
        len(warnings),
    )
    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
