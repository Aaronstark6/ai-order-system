import json
from copy import deepcopy

from app.runtime_paths import get_base_dir


DEFAULT_STRUCTURED_MAPPING = {
    "version": "V4-Rebuild.4",
    "mappings": [
        {
            "label": "产品名称",
            "source_path": "product.product_name",
            "target_cell": "B1",
            "operation": "write_text",
        },
        {
            "label": "产品类型",
            "source_path": "product.product_type",
            "target_cell": "B2",
            "operation": "write_text",
        },
        {
            "label": "客户名称",
            "source_path": "customer.name",
            "target_cell": "B6",
            "operation": "write_text",
        },
    ],
}


def _mapping_path():
    return get_base_dir() / "v4" / "rules" / "structured_excel_mapping.json"


def _ensure_mapping_file():
    path = _mapping_path()
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_STRUCTURED_MAPPING, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return path


def load_structured_excel_mapping():
    path = _ensure_mapping_file()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = deepcopy(DEFAULT_STRUCTURED_MAPPING)
    return data if isinstance(data, dict) else deepcopy(DEFAULT_STRUCTURED_MAPPING)


def _get_nested(data, source_path):
    current = data
    for part in str(source_path or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current.get(part)
    return current, True


def _field_value_from_entry(entry):
    if isinstance(entry, dict):
        for key in ("value", "text", "name", "label"):
            if key in entry:
                return entry.get(key)
        return ""
    return entry


def _get_product_field(order_object, field_identifier):
    fields = order_object.get("product", {}).get("fields", {}) if isinstance(order_object, dict) else {}
    if not isinstance(fields, dict):
        return None, False

    if field_identifier in fields:
        return _field_value_from_entry(fields.get(field_identifier)), True

    for field_key, entry in fields.items():
        if field_key == field_identifier:
            return _field_value_from_entry(entry), True
        if isinstance(entry, dict):
            labels = {
                str(entry.get("label") or "").strip(),
                str(entry.get("name") or "").strip(),
                str(entry.get("field_name") or "").strip(),
                str(entry.get("field_id") or "").strip(),
                str(entry.get("key") or "").strip(),
            }
            if str(field_identifier or "").strip() in labels:
                return _field_value_from_entry(entry), True

    return None, False


def _resolve_value(order_object, source_path):
    source_path = str(source_path or "").strip()
    if source_path.startswith("product.fields."):
        return _get_product_field(order_object, source_path[len("product.fields."):])
    return _get_nested(order_object, source_path)


def build_structured_operations(order_object):
    mapping = load_structured_excel_mapping()
    warnings = []
    operations = []

    for item in mapping.get("mappings", []) if isinstance(mapping.get("mappings"), list) else []:
        if not isinstance(item, dict):
            continue

        source_path = item.get("source_path", "")
        value, found = _resolve_value(order_object, source_path)
        if not found:
            warnings.append(f"{source_path} 未找到，已使用空值。")
            value = ""

        operations.append(
            {
                "label": str(item.get("label") or ""),
                "source_path": str(source_path or ""),
                "target_cell": str(item.get("target_cell") or "").strip(),
                "operation": str(item.get("operation") or "write_text").strip() or "write_text",
                "value": "" if value is None else str(value),
            }
        )

    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
