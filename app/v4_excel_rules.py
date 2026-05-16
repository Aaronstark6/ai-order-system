import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_excel_render_rules_path():
    return get_base_dir() / "v4" / "schemas" / "excel_render_rules.json"


def load_excel_render_rules() -> dict:
    rules_path = _get_excel_render_rules_path()
    if not rules_path.exists():
        logger.info("V4 Excel render rules not found: path=%s", rules_path)
        return {}

    try:
        with rules_path.open("r", encoding="utf-8") as f:
            rules = json.load(f)
    except JSONDecodeError as exc:
        logger.error("V4 Excel render rules JSON parse failed: path=%s error=%s", rules_path, exc)
        return {}
    except OSError as exc:
        logger.error("V4 Excel render rules read failed: path=%s error=%s", rules_path, exc)
        return {}

    if not isinstance(rules, dict):
        logger.error("V4 Excel render rules root must be an object: path=%s", rules_path)
        return {}

    return rules


def get_template_rules(template_key: str) -> dict:
    templates = load_excel_render_rules().get("templates", {})
    if not isinstance(templates, dict):
        return {}

    template_rules = templates.get(template_key, {})
    return template_rules if isinstance(template_rules, dict) else {}
