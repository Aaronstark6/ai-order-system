import json
from pathlib import Path


FIELDS_FILE = Path("data/fields.json")

SYSTEM_FIELD_KEYS = {
    "document_no",
    "sales_name",
    "salesperson_code",
    "company_code",
    "deal_date",
    "sequence",
    "ingredient_initials",
    "product_index_or_day",
    "product_abbr",
    "product_form",
    "dosage_form_code",
    "product_code",
}

BUILTIN_FIELDS = [
    {
        "key": "document_no",
        "label": "文档编号",
        "type": "text",
        "description": "根据规则自动生成的文档编号，可作为Excel文件名",
    },
    {
        "key": "sales_name",
        "label": "业务员英文名",
        "type": "text",
        "description": "示例: Anna",
    },
    {
        "key": "salesperson_code",
        "label": "业务员代号",
        "type": "text",
        "description": "2个字母，示例: AN、MD、CR",
    },
    {
        "key": "company_code",
        "label": "公司/客户简称",
        "type": "text",
        "description": "示例: GS",
    },
    {
        "key": "deal_date",
        "label": "成交日期",
        "type": "date",
        "description": "示例: 2026-03-18，默认可为当天",
    },
    {
        "key": "sequence",
        "label": "序号",
        "type": "text",
        "description": "示例: A01",
    },
    {
        "key": "product_index_or_day",
        "label": "中间数字",
        "type": "text",
        "description": "1-2位，可为产品序号或成交日中的日等",
    },
    {
        "key": "product_abbr",
        "label": "产品代号",
        "type": "text",
        "description": "2个字母，如 MV、PB、OG",
    },
    {
        "key": "ingredient_initials",
        "label": "产品成分缩写",
        "type": "text",
        "description": "人工确认的产品成分英文首字母组合，示例: AOC",
    },
    {
        "key": "product_form",
        "label": "产品形式",
        "type": "text",
        "description": "如：硬胶囊、软胶囊、粉末、滴剂等，用于生成剂型代号",
    },
    {
        "key": "dosage_form_code",
        "label": "剂型代号",
        "type": "text",
        "description": "根据产品剂型自动映射生成",
    },
    {
        "key": "product_code",
        "label": "产品编码",
        "type": "text",
        "description": "由业务员代号、成交日期月日、产品成分缩写、剂型代号按规则拼接",
    },
]


def _ensure_builtin_fields(fields: list):
    existing_keys = {str(f.get("key") or "").strip() for f in (fields or []) if isinstance(f, dict)}

    changed = False
    for field in BUILTIN_FIELDS:
        if field["key"] not in existing_keys:
            fields.append(field)
            changed = True

    if changed:
        save_fields(fields)

    return fields


def _normalize_field_for_current_ui(field):
    if not isinstance(field, dict):
        field = {}

    return {
        "key": str(field.get("key") or "").strip(),
        "label": str(field.get("label") or "").strip(),
        "type": str(field.get("type") or "text").strip() or "text",
        "description": str(field.get("description") or "").strip(),
    }


def _normalize_fields_for_current_ui(fields: list):
    normalized = []
    for field in fields or []:
        item = _normalize_field_for_current_ui(field)
        if item["key"]:
            normalized.append(item)
    return normalized


def _load_raw_fields():
    if not FIELDS_FILE.exists():
        return _ensure_builtin_fields([])

    with open(FIELDS_FILE, "r", encoding="utf-8") as f:
        fields = json.load(f)

    if not isinstance(fields, list):
        fields = []

    return _ensure_builtin_fields(fields)


def load_fields():
    return _normalize_fields_for_current_ui(_load_raw_fields())


def save_fields(fields):
    FIELDS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(FIELDS_FILE, "w", encoding="utf-8") as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)


def add_field(new_field):
    fields = _load_raw_fields()

    key = new_field.get("key", "").strip()

    if not key:
        raise ValueError("字段 key 不能为空")

    if key in SYSTEM_FIELD_KEYS:
        raise ValueError("该 key 是系统规则字段，不能作为普通字段新增")

    for field in fields:
        if field.get("key") == key:
            raise ValueError("字段 key 已存在")

    normalized_field = {
        "key": key,
        "label": new_field.get("label", "").strip(),
        "type": new_field.get("type", "text"),
        "description": new_field.get("description", "").strip()
    }

    if not normalized_field["label"]:
        raise ValueError("字段中文名不能为空")

    fields.append(normalized_field)
    save_fields(fields)

    return _normalize_field_for_current_ui(normalized_field)


def update_field(key, updated_data):
    fields = _load_raw_fields()

    for field in fields:
        if field.get("key") == key:
            new_key = str(updated_data.get("key", key) or "").strip()
            label = updated_data.get("label", field.get("label", "")).strip()

            if not new_key:
                raise ValueError("字段 key 不能为空")

            if key in SYSTEM_FIELD_KEYS and new_key != key:
                raise ValueError("系统规则字段 key 不能修改")

            if key not in SYSTEM_FIELD_KEYS and new_key in SYSTEM_FIELD_KEYS:
                raise ValueError("该 key 是系统规则字段，不能作为普通字段新增")

            if new_key != key and any(item.get("key") == new_key for item in fields):
                raise ValueError("字段 key 已存在")

            if not label:
                raise ValueError("字段中文名不能为空")

            field["key"] = new_key
            field["label"] = label
            field["type"] = updated_data.get("type", field.get("type", "text"))
            field["description"] = updated_data.get("description", field.get("description", "")).strip()

            save_fields(fields)
            return _normalize_field_for_current_ui(field)

    raise ValueError("字段不存在")


def delete_field(key):
    if key in SYSTEM_FIELD_KEYS:
        raise ValueError("系统规则字段不能删除，它被文档编号/产品编码等功能使用")

    fields = _load_raw_fields()
    new_fields = [field for field in fields if field.get("key") != key]

    if len(new_fields) == len(fields):
        raise ValueError("字段不存在")

    save_fields(new_fields)

    return {
        "deleted": key
    }
