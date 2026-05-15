import json
import os

from dotenv import load_dotenv

from app.runtime_paths import get_base_dir


load_dotenv()

BASE_DIR = get_base_dir()
SETTINGS_FILE = BASE_DIR / "data" / "app_settings.json"
DEFAULT_APP_SETTINGS = {
    "default_sales_name": "Anna",
    "default_salesperson_code": "AN",
    "default_company_code": "GS",
    "default_sequence": "A01",
    "export_sync_dir": "",
    "deepseek_api_key": ""
}

PUBLIC_APP_SETTING_KEYS = {
    "default_sales_name",
    "default_salesperson_code",
    "default_company_code",
    "default_sequence",
    "export_sync_dir",
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

    current = load_app_settings() if SETTINGS_FILE.exists() else dict(DEFAULT_APP_SETTINGS)
    settings = dict(DEFAULT_APP_SETTINGS)
    if isinstance(data, dict):
        for key, fallback in DEFAULT_APP_SETTINGS.items():
            if key not in data and key == "deepseek_api_key":
                settings[key] = str(current.get(key) or "").strip()
                continue
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


def public_app_settings():
    settings = load_app_settings()
    return {
        key: settings.get(key, DEFAULT_APP_SETTINGS.get(key, ""))
        for key in PUBLIC_APP_SETTING_KEYS
    }


def get_deepseek_api_key():
    settings = load_app_settings()
    configured = str(settings.get("deepseek_api_key") or "").strip()
    if configured:
        return configured

    return os.getenv("DEEPSEEK_API_KEY", "").strip()


def save_deepseek_api_key(api_key):
    settings = load_app_settings()
    settings["deepseek_api_key"] = str(api_key or "").strip()
    return save_app_settings(settings)
