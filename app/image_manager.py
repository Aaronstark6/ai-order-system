import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_FIELDS_FILE = BASE_DIR / "data" / "image_fields.json"
IMAGE_UPLOAD_DIR = BASE_DIR / "uploads" / "images"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def normalize_image_library_field(field):
    if not isinstance(field, dict):
        field = {}

    return {
        "key": str(field.get("key") or "").strip(),
        "label": str(field.get("label") or "").strip(),
    }


def normalize_image_library_fields(fields, validate=False):
    normalized = []
    seen_keys = set()

    for field in fields or []:
        item = normalize_image_library_field(field)
        if not item["key"] and not validate:
            continue
        if not item["key"]:
            raise ValueError("图片字段 key 不能为空")
        if not item["label"]:
            raise ValueError("图片字段名称不能为空")
        if item["key"] in seen_keys:
            raise ValueError(f"图片字段 key 重复：{item['key']}")
        seen_keys.add(item["key"])
        normalized.append(item)

    return normalized


def load_image_fields():
    if not IMAGE_FIELDS_FILE.exists():
        save_image_fields([])
        return []

    with open(IMAGE_FIELDS_FILE, "r", encoding="utf-8") as f:
        fields = json.load(f)

    if not isinstance(fields, list):
        fields = []

    return normalize_image_library_fields(fields)


def save_image_fields(fields):
    normalized = normalize_image_library_fields(fields, validate=True)
    IMAGE_FIELDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(IMAGE_FIELDS_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    return normalized


def normalize_image_mapping(field):
    if not isinstance(field, dict):
        field = {}

    return {
        "key": str(field.get("key") or "").strip(),
        "enabled": field.get("enabled") is True,
        "cell": str(field.get("cell") or "").strip().upper(),
    }


def normalize_image_mappings(fields, validate=False):
    normalized = []
    seen_keys = set()

    for field in fields or []:
        item = normalize_image_mapping(field)
        if not item["key"] and not validate:
            continue
        if not item["key"]:
            raise ValueError("图片字段 key 不能为空")
        if item["enabled"] and not item["cell"]:
            raise ValueError(f"图片字段 {item['key']} 已启用但没有设置 Excel 单元格")
        if item["key"] in seen_keys:
            raise ValueError(f"图片字段 key 重复：{item['key']}")
        seen_keys.add(item["key"])
        normalized.append(item)

    return normalized


def ensure_image_upload_dir():
    IMAGE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    return IMAGE_UPLOAD_DIR


def is_allowed_image_filename(filename):
    return Path(str(filename or "")).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def safe_image_extension(filename):
    ext = Path(str(filename or "")).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("仅支持 JPG、JPEG、PNG 图片")
    return ext


def resolve_uploaded_image_path(image_path):
    text = str(image_path or "").strip()
    if not text:
        return None

    path = Path(text)
    if not path.is_absolute():
        path = BASE_DIR / path

    resolved = path.resolve()
    upload_root = IMAGE_UPLOAD_DIR.resolve()
    try:
        resolved.relative_to(upload_root)
    except ValueError:
        return None

    if not resolved.exists() or not resolved.is_file():
        return None

    if resolved.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        return None

    return resolved
