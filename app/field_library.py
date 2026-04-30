import json
from pathlib import Path

FIELDS_FILE = Path("data/fields.json")


def load_fields():
    if not FIELDS_FILE.exists():
        return []

    with open(FIELDS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_fields(fields):
    FIELDS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(FIELDS_FILE, "w", encoding="utf-8") as f:
        json.dump(fields, f, ensure_ascii=False, indent=2)


def get_enabled_fields():
    fields = load_fields()
    return [field for field in fields if field.get("enabled", True)]


def add_field(new_field):
    fields = load_fields()

    for field in fields:
        if field["key"] == new_field["key"]:
            raise ValueError("字段key已存在")

    fields.append(new_field)
    save_fields(fields)

    return new_field


def delete_field(key):
    fields = load_fields()
    new_fields = [field for field in fields if field["key"] != key]

    if len(new_fields) == len(fields):
        raise ValueError("字段不存在")

    save_fields(new_fields)
    return {"deleted": key}
