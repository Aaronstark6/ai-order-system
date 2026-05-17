import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_schema import get_product_types


logger = get_logger(__name__)


def _get_structured_excel_mapping_path():
    return get_base_dir() / "v4" / "rules" / "structured_excel_mapping.json"


def _normalize_target_direction(value):
    return "below" if str(value or "").strip() == "below" else "right"


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


def _normalize_mapping_item(item):
    if not isinstance(item, dict):
        return None

    source_path = str(item.get("source_path") or "").strip()
    target_cell = str(item.get("target_cell") or "").strip()
    label = str(item.get("label") or source_path).strip()
    target_direction = _normalize_target_direction(item.get("target_direction"))
    if not source_path and not target_cell and not label:
        return None

    return {
        "source_path": source_path,
        "target_cell": target_cell,
        "operation": "write_text",
        "label": label or source_path or target_cell,
        "target_direction": target_direction,
    }


def normalize_structured_excel_mapping(mapping):
    current = load_structured_excel_mapping()
    source = mapping if isinstance(mapping, dict) else {}
    raw_mappings = source.get("mappings", [])
    if not isinstance(raw_mappings, list):
        raw_mappings = []

    normalized_items = []
    for item in raw_mappings:
        normalized_item = _normalize_mapping_item(item)
        if normalized_item:
            normalized_items.append(normalized_item)

    return {
        "mapping_name": str(
            current.get("mapping_name")
            or source.get("mapping_name")
            or "结构化字段映射"
        ).strip() or "结构化字段映射",
        "version": "V4-Core.12",
        "target": str(source.get("target") or current.get("target") or "real_excel").strip() or "real_excel",
        "mappings": normalized_items,
    }


def save_structured_excel_mapping(mapping):
    mapping_path = _get_structured_excel_mapping_path()
    normalized = normalize_structured_excel_mapping(mapping)
    try:
        mapping_path.parent.mkdir(parents=True, exist_ok=True)
        with mapping_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        logger.exception("[StructuredExcelMapping] Mapping save failed: path=%s", mapping_path)
        return {
            "success": False,
            "error": str(exc) or "结构化映射保存失败",
        }

    logger.info(
        "[StructuredExcelMapping] Mapping saved: path=%s mappings=%s",
        mapping_path,
        len(normalized.get("mappings", [])),
    )
    return {
        "success": True,
        "data": normalized,
    }


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
            "target_direction": _normalize_target_direction(item.get("target_direction")),
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
