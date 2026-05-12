import json
import os
from typing import Dict, Any

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, "config")
EXPORT_SYNC_DIR = os.getenv("EXPORT_SYNC_DIR", "").strip()
AI_SETTINGS_PASSWORD = os.getenv("AI_SETTINGS_PASSWORD", "admin123")

FIELDS_FILE = os.path.join(CONFIG_DIR, "fields.json")
TEMPLATE_MAPPINGS_FILE = os.path.join(CONFIG_DIR, "template_mappings.json")


def ensure_config_dir():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_json_file(file_path: str, default_data):
    ensure_config_dir()

    if not os.path.exists(file_path):
        save_json_file(file_path, default_data)
        return default_data

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_data


def save_json_file(file_path: str, data):
    ensure_config_dir()

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# 字段库
# =========================

DEFAULT_FIELDS = {
    "customer_name": {
        "label": "客户名称",
        "description": "客户公司名称或客户联系人名称",
        "type": "text",
        "required": False,
        "enabled": True
    },
    "product_name": {
        "label": "产品名称",
        "description": "客户需要订购的产品名称",
        "type": "text",
        "required": True,
        "enabled": True
    },
    "quantity": {
        "label": "数量",
        "description": "订单数量",
        "type": "number",
        "required": False,
        "enabled": True
    },
    "unit": {
        "label": "单位",
        "description": "数量单位，例如箱、件、kg、袋",
        "type": "text",
        "required": False,
        "enabled": True
    },
    "delivery_date": {
        "label": "交货日期",
        "description": "客户要求的交货日期",
        "type": "date",
        "required": False,
        "enabled": True
    },
    "remark": {
        "label": "备注",
        "description": "客户的其他补充要求",
        "type": "text",
        "required": False,
        "enabled": True
    }
}


def normalize_field(field_key: str, field_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    兼容旧版字段结构，统一补齐 V2.1 字段属性。
    """
    if not isinstance(field_data, dict):
        field_data = {}

    return {
        "label": field_data.get("label") or field_key,
        "description": field_data.get("description") or "",
        "type": field_data.get("type") or "text",
        "required": bool(field_data.get("required", False)),
        "enabled": bool(field_data.get("enabled", True))
    }


def normalize_fields(fields: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {}

    for field_key, field_data in fields.items():
        normalized[field_key] = normalize_field(field_key, field_data)

    return normalized


def get_fields() -> Dict[str, Any]:
    fields = load_json_file(FIELDS_FILE, DEFAULT_FIELDS)
    fields = normalize_fields(fields)

    # 自动保存一次，方便旧结构升级到新结构
    save_json_file(FIELDS_FILE, fields)

    return fields


def save_fields(fields: Dict[str, Any]):
    fields = normalize_fields(fields)
    save_json_file(FIELDS_FILE, fields)


def get_enabled_fields() -> Dict[str, Any]:
    fields = get_fields()

    return {
        field_key: field_data
        for field_key, field_data in fields.items()
        if field_data.get("enabled", True)
    }


def add_field(field_key: str, field_data: Dict[str, Any]):
    fields = get_fields()

    if field_key in fields:
        raise ValueError(f"字段已存在：{field_key}")

    fields[field_key] = normalize_field(field_key, field_data)
    save_fields(fields)

    return fields[field_key]


def update_field(field_key: str, field_data: Dict[str, Any]):
    fields = get_fields()

    if field_key not in fields:
        raise ValueError(f"字段不存在：{field_key}")

    old_data = fields[field_key]

    updated_data = {
        "label": field_data.get("label", old_data.get("label", field_key)),
        "description": field_data.get("description", old_data.get("description", "")),
        "type": field_data.get("type", old_data.get("type", "text")),
        "required": field_data.get("required", old_data.get("required", False)),
        "enabled": field_data.get("enabled", old_data.get("enabled", True))
    }

    fields[field_key] = normalize_field(field_key, updated_data)
    save_fields(fields)

    return fields[field_key]


def delete_field(field_key: str):
    fields = get_fields()

    if field_key not in fields:
        raise ValueError(f"字段不存在：{field_key}")

    deleted = fields.pop(field_key)
    save_fields(fields)

    return deleted


def set_field_enabled(field_key: str, enabled: bool):
    fields = get_fields()

    if field_key not in fields:
        raise ValueError(f"字段不存在：{field_key}")

    fields[field_key]["enabled"] = bool(enabled)
    save_fields(fields)

    return fields[field_key]


# =========================
# 模板映射
# =========================

def get_template_mappings() -> Dict[str, Any]:
    return load_json_file(TEMPLATE_MAPPINGS_FILE, {})


def save_template_mappings(mappings: Dict[str, Any]):
    save_json_file(TEMPLATE_MAPPINGS_FILE, mappings)


def get_template_mapping(template_id: str) -> Dict[str, Any]:
    mappings = get_template_mappings()
    return mappings.get(template_id, {})


def save_template_mapping(template_id: str, mapping_data: Dict[str, Any]):
    mappings = get_template_mappings()
    mappings[template_id] = mapping_data
    save_template_mappings(mappings)
    return mapping_data


def delete_template_mapping(template_id: str):
    mappings = get_template_mappings()

    if template_id in mappings:
        deleted = mappings.pop(template_id)
        save_template_mappings(mappings)
        return deleted

    return None
