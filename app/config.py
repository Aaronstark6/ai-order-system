import os

from dotenv import load_dotenv

from app.runtime_paths import get_base_dir


load_dotenv()

BASE_DIR = get_base_dir()
EXPORT_SYNC_DIR = os.getenv("EXPORT_SYNC_DIR", "").strip()
AI_SETTINGS_PASSWORD = os.getenv("AI_SETTINGS_PASSWORD", "admin123")
