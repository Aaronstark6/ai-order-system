import json
import shutil
from datetime import datetime
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


def save_excel_render_rules(rules_config: dict) -> dict:
    rules_path = _get_excel_render_rules_path()
    backup_dir = rules_path.parent / "backups"

    logger.info("V4 Excel render rules save started: path=%s", rules_path)
    try:
        if not isinstance(rules_config, dict):
            raise ValueError("rules_config must be a dict")

        rules_path.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        if rules_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = backup_dir / f"excel_render_rules_{timestamp}.json"
            logger.info("V4 Excel render rules backup path: path=%s", backup_path)
            shutil.copy2(rules_path, backup_path)
        else:
            logger.info("V4 Excel render rules backup path: no existing rules to backup")

        with rules_path.open("w", encoding="utf-8") as f:
            json.dump(rules_config, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("V4 Excel render rules save succeeded: path=%s", rules_path)
        return {
            "success": True,
            "data": rules_config,
        }
    except Exception as exc:
        logger.exception("V4 Excel render rules save failed: path=%s", rules_path)
        return {
            "success": False,
            "error": str(exc),
        }
