import re
from pathlib import Path

from app.runtime_paths import get_base_dir


BASE_DIR = get_base_dir()
DESCRIPTION_TEMPLATE_DIR = BASE_DIR / "data" / "description_templates"
DEFAULT_DESCRIPTION_TEMPLATE_CONTENT = """产品名称：{product_name}
产品形式：{product_form}
规格：{specification}
数量：{quantity}
配方要求：{formula_requirement}
备注：
"""


def ensure_description_template_dir():
    DESCRIPTION_TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)


def _safe_template_name(template_name):
    name = Path(str(template_name or "").strip()).name
    if not name:
        raise ValueError("template_name cannot be empty")
    if Path(name).suffix.lower() != ".txt":
        raise ValueError("description template must be a .txt file")
    return name


def _template_path(template_name):
    ensure_description_template_dir()
    return DESCRIPTION_TEMPLATE_DIR / _safe_template_name(template_name)


def list_description_templates():
    ensure_description_template_dir()
    return sorted(path.name for path in DESCRIPTION_TEMPLATE_DIR.glob("*.txt") if path.is_file())


def get_description_template(template_name):
    path = _template_path(template_name)
    if not path.exists():
        raise FileNotFoundError(f"description template not found: {path.name}")
    return path.read_text(encoding="utf-8")


def save_description_template(template_name, content):
    path = _template_path(template_name)
    text = "" if content is None else str(content)
    path.write_text(text, encoding="utf-8")
    return {
        "template_name": path.name,
        "content": text,
    }


def restore_default_description_template(template_name):
    return save_description_template(template_name, DEFAULT_DESCRIPTION_TEMPLATE_CONTENT)


def render_description_template(template, data):
    source = "" if template is None else str(template)
    values = data if isinstance(data, dict) else {}

    def replace_placeholder(match):
        key = match.group(1).strip()
        value = values.get(key)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{([^{}]+)\}", replace_placeholder, source)
