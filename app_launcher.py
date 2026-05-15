import logging
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path


HOST = "127.0.0.1"
RELEASE_PORT = 8001
HEALTH_WAIT_SECONDS = 10
SERVER_JOIN_TIMEOUT_SECONDS = 10


def get_launcher_base_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = get_launcher_base_dir()


def ensure_standard_streams():
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def prepare_import_path(base_dir):
    base_dir_text = str(base_dir)
    if base_dir_text not in sys.path:
        sys.path.insert(0, base_dir_text)


def configure_logging(base_dir):
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=logs_dir / "app.log",
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        encoding="utf-8",
        force=True,
    )


def get_port():
    raw = os.getenv("AI_ORDER_SYSTEM_PORT", str(RELEASE_PORT))
    try:
        port = int(raw)
    except (TypeError, ValueError):
        return RELEASE_PORT
    return port if 1 <= port <= 65535 else RELEASE_PORT


def make_home_url(port):
    return f"http://{HOST}:{port}"


def make_health_url(port):
    return f"{make_home_url(port)}/api/health"


def open_browser(port):
    url = make_home_url(port)
    webbrowser.open(url)
    logging.info("browser opened: %s", url)


def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((HOST, port)) == 0


def wait_for_health(port, timeout_seconds=HEALTH_WAIT_SECONDS):
    deadline = time.monotonic() + timeout_seconds
    health_url = make_health_url(port)
    last_error = None

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=1) as response:
                if 200 <= response.status < 300:
                    logging.info("health check result: success status=%s", response.status)
                    return True
                last_error = f"unexpected status {response.status}"
        except (OSError, urllib.error.URLError) as exc:
            last_error = str(exc)
        time.sleep(0.25)

    logging.warning("health check result: failed url=%s error=%s", health_url, last_error)
    return False


def create_tray_image():
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=(37, 99, 235))
    draw.ellipse((24, 24, 40, 40), fill="white")
    return image


def import_fastapi_app():
    try:
        from app.main import app
    except Exception:
        logging.exception("import app.main failed")
        raise

    logging.info("import app.main result: success")
    return app


class AppLauncher:
    def __init__(self, port):
        self.port = port
        self.server = None
        self.server_thread = None
        self.started_server = False
        self.shutdown_lock = threading.Lock()
        self.shutdown_complete = False

    def start_server_if_available(self):
        port_in_use = is_port_in_use(self.port)
        logging.info("port check result: %s:%s in_use=%s", HOST, self.port, port_in_use)

        if port_in_use:
            logging.warning("port already in use: %s:%s", HOST, self.port)
            return False

        import uvicorn
        fastapi_app = import_fastapi_app()

        config = uvicorn.Config(
            fastapi_app,
            host=HOST,
            port=self.port,
            reload=False,
            log_config=None,
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.server_thread = threading.Thread(
            target=self._run_server,
            name="uvicorn-server",
            daemon=True,
        )
        self.server_thread.start()
        self.started_server = True
        logging.info("server thread started")
        return True

    def _run_server(self):
        try:
            self.server.run()
        except Exception:
            logging.exception("server thread failed")
        finally:
            logging.info("server stopped")

    def open_home(self, icon=None, item=None):
        open_browser(self.port)

    def request_shutdown(self, icon=None, item=None):
        logging.info("shutdown requested")
        self.cleanup(icon)

    def cleanup(self, icon=None):
        with self.shutdown_lock:
            if self.shutdown_complete:
                if icon is not None:
                    icon.stop()
                return

            if self.started_server and self.server is not None:
                self.server.should_exit = True
                if self.server_thread is not None:
                    self.server_thread.join(timeout=SERVER_JOIN_TIMEOUT_SECONDS)
                    if self.server_thread.is_alive():
                        logging.warning("server thread did not stop within timeout")
                    else:
                        logging.info("server thread joined")
            else:
                logging.info("no owned server to stop")

            self.shutdown_complete = True
            logging.info("launcher exited")

            if icon is not None:
                icon.stop()

    def run_tray(self):
        import pystray

        icon = pystray.Icon(
            "ai-order-system",
            create_tray_image(),
            "\u5916\u8d38\u8ba2\u5355\u89e3\u6790\u7cfb\u7edf",
            menu=pystray.Menu(
                pystray.MenuItem("\u6253\u5f00\u9996\u9875", self.open_home, default=True),
                pystray.MenuItem("\u9000\u51fa\u7cfb\u7edf", self.request_shutdown),
            ),
        )
        logging.info("tray started")
        try:
            icon.run()
        finally:
            self.cleanup()


def main():
    ensure_standard_streams()

    base_dir = BASE_DIR
    prepare_import_path(base_dir)
    os.environ.setdefault("AI_ORDER_SYSTEM_BASE_DIR", str(base_dir))
    os.chdir(base_dir)
    configure_logging(base_dir)
    logging.info("launcher started")
    logging.info("frozen: %s", getattr(sys, "frozen", False))
    logging.info("BASE_DIR: %s", base_dir)
    logging.info("sys.path head: %s", sys.path[:5])

    port = get_port()
    logging.info("RELEASE_PORT: %s", port)
    launcher = AppLauncher(port)

    try:
        server_started = launcher.start_server_if_available()
        if server_started:
            wait_for_health(port)
        else:
            logging.info("health check result: skipped because port already in use")

        open_browser(port)
        launcher.run_tray()
        sys.exit(0)
    except SystemExit:
        raise
    except Exception:
        logging.exception("launcher failed")
        launcher.cleanup()
        raise
    finally:
        logging.shutdown()


if __name__ == "__main__":
    main()
