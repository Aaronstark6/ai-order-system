import logging
import sys

from app.runtime_paths import get_base_dir


LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _get_log_file_path():
    logs_dir = get_base_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir / "app.log"


def get_logger(name="ai-order-system"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

        if getattr(sys, "stderr", None):
            stream_handler = logging.StreamHandler()
            stream_handler.setLevel(logging.INFO)
            stream_handler.setFormatter(formatter)
            logger.addHandler(stream_handler)

        log_file_path = _get_log_file_path()
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
