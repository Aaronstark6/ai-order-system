"""Resolve the application root in development and packaged releases."""

import os
import sys
from pathlib import Path


def get_base_dir():
    override = os.getenv("AI_ORDER_SYSTEM_BASE_DIR")
    if override:
        return Path(override).resolve()

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        if (exe_dir / "static").exists() or (exe_dir / "data").exists():
            return exe_dir

        bundle_dir = Path(getattr(sys, "_MEIPASS", exe_dir)).resolve()
        return bundle_dir

    return Path(__file__).resolve().parent.parent
