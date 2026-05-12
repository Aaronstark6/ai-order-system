import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
EXPORT_SYNC_DIR = os.getenv("EXPORT_SYNC_DIR", "").strip()
AI_SETTINGS_PASSWORD = os.getenv("AI_SETTINGS_PASSWORD", "admin123")
