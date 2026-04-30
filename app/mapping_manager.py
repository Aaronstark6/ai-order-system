import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
MAPPINGS_FILE = BASE_DIR / "data" / "mappings.json"


def load_mappings():
    if not MAPPINGS_FILE.exists():
        return {}

    with open(MAPPINGS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_mappings(mappings: dict):
    MAPPINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(MAPPINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    return mappings


def update_mapping(field_key: str, cell: str):
    mappings = load_mappings()

    field_key = field_key.strip()
    cell = cell.strip().upper()

    if not field_key:
        raise ValueError("字段 key 不能为空")

    if not cell:
        mappings.pop(field_key, None)
    else:
        mappings[field_key] = cell

    save_mappings(mappings)

    return mappings
