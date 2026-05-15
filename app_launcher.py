import os
import sys
import threading
import webbrowser
from pathlib import Path


def get_launcher_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def ensure_standard_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def get_port():
    raw = os.getenv("AI_ORDER_SYSTEM_PORT", "8000")
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return 8000
    return port if 1 <= port <= 65535 else 8000


def open_browser(port):
    webbrowser.open(f"http://127.0.0.1:{port}")


def main():
    ensure_standard_streams()

    base_dir = get_launcher_base_dir()
    os.environ.setdefault("AI_ORDER_SYSTEM_BASE_DIR", str(base_dir))
    os.chdir(base_dir)

    import uvicorn
    from app.main import app

    port = get_port()
    threading.Timer(1.0, open_browser, args=(port,)).start()
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        reload=False,
        log_config=None,
        access_log=False,
    )


if __name__ == "__main__":
    main()
