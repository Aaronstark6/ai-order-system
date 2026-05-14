from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
IMAGE_UPLOAD_DIR = BASE_DIR / "uploads" / "images"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def normalize_image_field(field):
    if not isinstance(field, dict):
        field = {}

    return {
        "key": str(field.get("key") or "").strip(),
        "label": str(field.get("label") or "").strip(),
        "cell": str(field.get("cell") or "").strip().upper(),
        "enabled": field.get("enabled") is not False,
    }


def normalize_image_fields(fields, validate=False):
    normalized = []
    seen_keys = set()

    for field in fields or []:
        item = normalize_image_field(field)
        if not item["key"] and not validate:
            continue
        if not item["key"]:
            raise ValueError("图片字段 key 不能为空")
        if not item["label"]:
            raise ValueError("图片字段名称不能为空")
        if not item["cell"]:
            raise ValueError(f"图片字段 {item['key']} 的 Excel 单元格不能为空")
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
