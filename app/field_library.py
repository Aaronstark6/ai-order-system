import json
from pathlib import Path


FIELDS_FILE = Path("data/fields.json")

BUILTIN_FIELDS = [
    {
        "key": "document_no",
        "label": "文档编号",
        "type": "text",
        "required": False,
        "description": "根据规则自动生成的文档编号，可作为Excel文件名",
    },
    {
        "key": "sales_name",
        "label": "业务员英文名",
        "type": "text",
        "required": False,
        "description": "示例: Anna",
    },
    {
        "key": "salesperson_code",
        "label": "业务员代号",
        "type": "text",
        "required": False,
        "description": "2个字母，示例: AN、MD、CR",
    },
    {
        "key": "company_code",
        "label": "公司/客户简称",
        "type": "text",
        "required": False,
        "description": "示例: GS",
    },
    {
        "key": "deal_date",
        "label": "成交日期",
        "type": "date",
        "required": False,
        "description": "示例: 2026-03-18，默认可为当天",
    },
    {
        "key": "sequence",
        "label": "序号",
        "type": "text",
        "required": False,
        "description": "示例: A01",
    },
    {
        "key": "product_index_or_day",
        "label": "中间数字",
        "type": "text",
        "required": False,
        "description": "1-2位，可为产品序号或成交日中的日等",
    },
    {
        "key": "product_abbr",
        "label": "产品代号",
        "type": "text",
        "required": False,
        "description": "2个字母，如 MV、PB、OG",
    },
    {
        "key": "ingredient_initials",
        "label": "产品成分缩写",
        "type": "text",
        "required": False,
        "description": "人工确认的产品成分英文首字母组合，示例: AOC",
    },
    {
        "key": "product_form",
        "label": "产品形式",
        "type": "text",
        "required": False,
        "description": "如：硬胶囊、软胶囊、粉末、滴剂等，用于生成剂型代号",
    },
    {
        "key": "dosage_form_code",
        "label": "剂型代号",
        "type": "text",
        "required": False,
        "description": "根据产品剂型自动映射生成",
    },
    {
        "key": "product_code",
        "label": "产品编码",
        "type": "text",
        "required": False,
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


def load_fields():
    if not FIELDS_FILE.exists():
        fields = []
        return _ensure_builtin_fields(fields)

    with open(FIELDS_FILE, "r", encoding="utf-8") as f:
        fields = json.load(f)

    if not isinstance(fields, list):
        fields = []

    return _ensure_builtin_fields(fields)


def save_fields(fields):
    FIELDS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(FIELDS_FILE, "w", encoding="utf-8") as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)


def add_field(new_field):
    fields = load_fields()

    key = new_field.get("key", "").strip()

    if not key:
        raise ValueError("字段 key 不能为空")

    for field in fields:
        if field.get("key") == key:
            raise ValueError("字段 key 已存在")

    normalized_field = {
        "key": key,
        "label": new_field.get("label", "").strip(),
        "type": new_field.get("type", "text"),
        "required": bool(new_field.get("required", False)),
        "description": new_field.get("description", "").strip()
    }

    if not normalized_field["label"]:
        raise ValueError("字段中文名不能为空")

    fields.append(normalized_field)
    save_fields(fields)

    return normalized_field


def update_field(key, updated_data):
    fields = load_fields()

    for field in fields:
        if field.get("key") == key:
            new_key = str(updated_data.get("key", key) or "").strip()
            label = updated_data.get("label", field.get("label", "")).strip()

            if not new_key:
                raise ValueError("字段 key 不能为空")

            if new_key != key and any(item.get("key") == new_key for item in fields):
                raise ValueError("字段 key 已存在")

            if not label:
                raise ValueError("字段中文名不能为空")

            field["key"] = new_key
            field["label"] = label
            field["type"] = updated_data.get("type", field.get("type", "text"))
            field["required"] = bool(updated_data.get("required", field.get("required", False)))
            field["description"] = updated_data.get("description", field.get("description", "")).strip()

            save_fields(fields)
            return field

    raise ValueError("字段不存在")


def delete_field(key):
    fields = load_fields()
    new_fields = [field for field in fields if field.get("key") != key]

    if len(new_fields) == len(fields):
        raise ValueError("字段不存在")

    save_fields(new_fields)

    return {
        "deleted": key
    }
