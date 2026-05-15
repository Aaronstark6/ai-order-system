import json
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
