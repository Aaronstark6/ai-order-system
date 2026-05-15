import os
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn


def get_launcher_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def open_browser():
    webbrowser.open("http://127.0.0.1:8000")


def main():
    base_dir = get_launcher_base_dir()
    os.environ.setdefault("AI_ORDER_SYSTEM_BASE_DIR", str(base_dir))
    os.chdir(base_dir)

    from app.main import app

    threading.Timer(1.0, open_browser).start()
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()
