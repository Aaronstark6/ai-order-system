import json
from pathlib import Path

FILE = Path("data/fields.json")


def load_fields():
    if not FILE.exists():
        return []
    return json.loads(FILE.read_text("utf-8"))


def save(fields):
    FILE.write_text(json.dumps(fields, ensure_ascii=False, indent=2), "utf-8")


def add_field(field):
    fields = load_fields()
    fields.append(field)
    save(fields)
    return field


def delete_field(key):
    fields = [f for f in load_fields() if f["key"] != key]
    save(fields)
    return key
