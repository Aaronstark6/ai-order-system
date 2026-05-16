import json
import shutil
from datetime import datetime
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_examples_dir():
    return get_base_dir() / "v4" / "examples"


def _get_example_path(example_name):
    safe_name = str(example_name or "").strip()
    if not safe_name:
        return None

    filename = safe_name if safe_name.endswith(".json") else f"{safe_name}.json"
    return _get_examples_dir() / filename


def load_example(example_name):
    example_path = _get_example_path(example_name)
    if example_path is None or not example_path.exists():
        return {}

    try:
        with example_path.open("r", encoding="utf-8") as f:
            example = json.load(f)
    except JSONDecodeError as exc:
        logger.error("V4 example JSON parse failed: path=%s error=%s", example_path, exc)
        return {}
    except OSError as exc:
        logger.error("V4 example read failed: path=%s error=%s", example_path, exc)
        return {}

    if not isinstance(example, dict):
        logger.error("V4 example root must be an object: path=%s", example_path)
        return {}

    return example


def save_example(example_name: str, data: dict):
    example_path = _get_example_path(example_name)
    if example_path is None:
        return {
            "success": False,
            "error": "example_name is required",
        }

    logger.info("V4 example save started: name=%s path=%s", example_name, example_path)
    try:
        if not isinstance(data, dict):
            raise ValueError("example data must be a dict")

        example_path.parent.mkdir(parents=True, exist_ok=True)
        backup_dir = example_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        if example_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"{example_path.stem}_{timestamp}.json"
            logger.info("V4 example backup path: path=%s", backup_path)
            shutil.copy2(example_path, backup_path)
        else:
            logger.info("V4 example backup path: no existing example to backup")

        with example_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("V4 example save succeeded: name=%s path=%s", example_name, example_path)
        return {
            "success": True,
        }
    except Exception as exc:
        logger.exception("V4 example save failed: name=%s path=%s", example_name, example_path)
        return {
            "success": False,
            "error": str(exc),
        }


def list_examples():
    examples_dir = _get_examples_dir()
    if not examples_dir.exists() or not examples_dir.is_dir():
        return []

    examples = []
    try:
        for path in sorted(examples_dir.glob("*.json")):
            examples.append({
                "name": path.stem,
                "filename": path.name,
            })
    except OSError as exc:
        logger.error("V4 examples list failed: path=%s error=%s", examples_dir, exc)
        return []

    return examples
