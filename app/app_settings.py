import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SETTINGS_FILE = BASE_DIR / "data" / "app_settings.json"
DEFAULT_APP_SETTINGS = {
    "default_sales_name": "Anna",
    "default_salesperson_code": "AN",
    "default_company_code": "GS",
    "default_sequence": "A01",
    "export_sync_dir": ""
}


def load_app_settings():
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        save_app_settings(DEFAULT_APP_SETTINGS)
        return dict(DEFAULT_APP_SETTINGS)

    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except Exception:
        raw = {}

    settings = dict(DEFAULT_APP_SETTINGS)
    if isinstance(raw, dict):
        for key, fallback in DEFAULT_APP_SETTINGS.items():
            value = str(raw.get(key) or "").strip()
            settings[key] = value or fallback

    return settings


def save_app_settings(data):
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)

    settings = dict(DEFAULT_APP_SETTINGS)
    if isinstance(data, dict):
        for key, fallback in DEFAULT_APP_SETTINGS.items():
            value = str(data.get(key) or "").strip()
            settings[key] = value or ("" if key == "export_sync_dir" else fallback)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)

    return settings


def get_export_sync_dir():
    settings = load_app_settings()
    configured = str(settings.get("export_sync_dir") or "").strip()
    if configured:
        return configured

    return os.getenv("EXPORT_SYNC_DIR", "").strip()
