import json
import shutil
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from app.app_settings import DEFAULT_APP_SETTINGS, load_app_settings
from app.image_manager import normalize_image_mappings
from app.layout_schema import default_layout_config, normalize_layout_config


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_UPLOAD_DIR = BASE_DIR / "templates" / "uploads"
PROFILES_FILE = DATA_DIR / "template_profiles.json"

# 归入文档编号体系，不应出现在「普通字段单元格映射」中的字段 key
RESERVED_DOCUMENT_MAPPING_KEYS = frozenset({
    "document_no",
    "sales_name",
    "salesperson_code",
    "company_code",
    "deal_date",
    "sequence",
    "ingredient_initials",
    "product_index_or_day",
    "product_abbr",
    "product_form",
    "product_code",
    "dosage_form_code",
})

DEFAULT_DOCUMENT_NO_SETTINGS = {
    "enabled": True,
    "document_no_cell": "",
    "use_document_no_as_filename": True,
    "default_sales_name": DEFAULT_APP_SETTINGS["default_sales_name"],
    "default_salesperson_code": DEFAULT_APP_SETTINGS["default_salesperson_code"],
    "default_company_code": DEFAULT_APP_SETTINGS["default_company_code"],
    "default_sequence": DEFAULT_APP_SETTINGS["default_sequence"],
    "document_no_rule": "{sales_name}-{company_code}{deal_date_yyyymmdd}{sequence}-{product_code}",
    "product_code_rule": "{salesperson_code}{deal_date_mmdd_no_leading_zero}{ingredient_initials}{dosage_form_code}",
}

DEFAULT_DESCRIPTION_SETTINGS = {
    "enabled": False,
    "template_name": "",
    "target_cell": "",
}

DEFAULT_LAYOUT_PREVIEW = {
    "enabled": False,
    "image_path": "",
    "image_width": 0,
    "image_height": 0,
}

PRODUCT_DESCRIPTION_TEMPLATE_MAP = {
    "片剂": "片剂.txt",
    "泡腾片": "泡腾片.txt",
    "果冻和凝胶": "果冻和凝胶.txt",
}


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def normalize_document_no_settings(raw, legacy_document_no_rule=None):
    merged = deepcopy(DEFAULT_DOCUMENT_NO_SETTINGS)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in DEFAULT_DOCUMENT_NO_SETTINGS:
                merged[key] = value

    merged["enabled"] = bool(merged.get("enabled", True))
    merged["use_document_no_as_filename"] = bool(merged.get("use_document_no_as_filename", True))

    merged["document_no_cell"] = str(merged.get("document_no_cell") or "").strip().upper()
    merged["default_sales_name"] = str(merged.get("default_sales_name") or DEFAULT_APP_SETTINGS["default_sales_name"]).strip() or DEFAULT_APP_SETTINGS["default_sales_name"]
    merged["default_salesperson_code"] = str(merged.get("default_salesperson_code") or DEFAULT_APP_SETTINGS["default_salesperson_code"]).strip() or DEFAULT_APP_SETTINGS["default_salesperson_code"]
    merged["default_company_code"] = str(merged.get("default_company_code") or DEFAULT_APP_SETTINGS["default_company_code"]).strip() or DEFAULT_APP_SETTINGS["default_company_code"]
    merged["default_sequence"] = str(merged.get("default_sequence") or DEFAULT_APP_SETTINGS["default_sequence"]).strip() or DEFAULT_APP_SETTINGS["default_sequence"]

    doc_rule = str(merged.get("document_no_rule") or "").strip()
    if not doc_rule and legacy_document_no_rule:
        doc_rule = str(legacy_document_no_rule or "").strip()
    merged["document_no_rule"] = doc_rule or DEFAULT_DOCUMENT_NO_SETTINGS["document_no_rule"]

    prod_rule = str(merged.get("product_code_rule") or "").strip()
    merged["product_code_rule"] = prod_rule or DEFAULT_DOCUMENT_NO_SETTINGS["product_code_rule"]

    return merged


def normalize_description_settings(raw):
    merged = deepcopy(DEFAULT_DESCRIPTION_SETTINGS)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in DEFAULT_DESCRIPTION_SETTINGS:
                merged[key] = value

    merged["enabled"] = bool(merged.get("enabled", False))
    merged["template_name"] = Path(str(merged.get("template_name") or "").strip()).name
    merged["target_cell"] = str(merged.get("target_cell") or "").strip().upper()

    return merged


def normalize_layout_preview(raw):
    merged = deepcopy(DEFAULT_LAYOUT_PREVIEW)
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key in DEFAULT_LAYOUT_PREVIEW:
                merged[key] = value

    merged["enabled"] = bool(merged.get("enabled", False))
    merged["image_path"] = str(merged.get("image_path") or "").strip().replace("\\", "/")

    try:
        merged["image_width"] = max(0, int(round(float(merged.get("image_width") or 0))))
    except (TypeError, ValueError):
        merged["image_width"] = 0

    try:
        merged["image_height"] = max(0, int(round(float(merged.get("image_height") or 0))))
    except (TypeError, ValueError):
        merged["image_height"] = 0

    if not merged["image_path"]:
        merged["enabled"] = False
        merged["image_width"] = 0
        merged["image_height"] = 0

    return merged


def get_default_description_template_name(profile_name: str):
    name = str(profile_name or "").strip()
    if not name:
        return ""

    if name in PRODUCT_DESCRIPTION_TEMPLATE_MAP:
        return PRODUCT_DESCRIPTION_TEMPLATE_MAP[name]

    for product_type, template_name in PRODUCT_DESCRIPTION_TEMPLATE_MAP.items():
        if product_type in name:
            return template_name

    return ""


def _strip_reserved_from_mappings(mappings: dict):
    if not isinstance(mappings, dict):
        return {}
    return {
        k: v
        for k, v in mappings.items()
        if str(k or "").strip() and str(k).strip() not in RESERVED_DOCUMENT_MAPPING_KEYS
    }


def normalize_profile(profile: dict):
    if "id" not in profile:
        profile["id"] = str(uuid4())

    if "name" not in profile:
        profile["name"] = "未命名映射"

    if "profile_version" not in profile:
        profile["profile_version"] = "v2"
    else:
        profile["profile_version"] = str(profile.get("profile_version") or "v2").strip() or "v2"

    if "template_file" not in profile:
        profile["template_file"] = ""

    if "template_display_name" not in profile:
        profile["template_display_name"] = ""

    if "mappings" not in profile:
        profile["mappings"] = {}

    # legacy composite mapping compatibility
    if "composite_mappings" not in profile:
        profile["composite_mappings"] = []

    legacy_rule = profile.get("document_no_rule")
    raw_settings = profile.get("document_no_settings")
    profile["document_no_settings"] = normalize_document_no_settings(
        raw_settings if isinstance(raw_settings, dict) else {},
        legacy_document_no_rule=legacy_rule if legacy_rule else None,
    )
    profile["description_settings"] = normalize_description_settings(
        profile.get("description_settings") if isinstance(profile.get("description_settings"), dict) else {}
    )
    if not profile["description_settings"].get("template_name"):
        profile["description_settings"]["template_name"] = get_default_description_template_name(profile.get("name"))

    profile["image_fields"] = normalize_image_mappings(
        profile.get("image_fields") if isinstance(profile.get("image_fields"), list) else []
    )
    profile["layout_config"] = normalize_layout_config(
        profile.get("layout_config") if isinstance(profile.get("layout_config"), dict) else default_layout_config()
    )
    profile["layout_preview"] = normalize_layout_preview(
        profile.get("layout_preview") if isinstance(profile.get("layout_preview"), dict) else {}
    )

    if "document_no_rule" in profile:
        del profile["document_no_rule"]

    profile["mappings"] = _strip_reserved_from_mappings(profile.get("mappings") or {})
    mapping_keys = set(profile["mappings"].keys())
    raw_order = profile.get("mapping_order") if isinstance(profile.get("mapping_order"), list) else []
    clean_order = []
    for key in raw_order:
        key = str(key or "").strip()
        if key and key in mapping_keys and key not in clean_order:
            clean_order.append(key)
    for key in profile["mappings"].keys():
        if key not in clean_order:
            clean_order.append(key)
    profile["mapping_order"] = clean_order

    if "mapping_defaults" not in profile or not isinstance(profile.get("mapping_defaults"), dict):
        profile["mapping_defaults"] = {}
    profile["mapping_defaults"] = {
        str(k or "").strip(): str(v) if v is not None else ""
        for k, v in (profile.get("mapping_defaults") or {}).items()
        if str(k or "").strip() and str(k or "").strip() not in RESERVED_DOCUMENT_MAPPING_KEYS
    }

    return profile


def load_profiles():
    ensure_dirs()

    if not PROFILES_FILE.exists():
        return []

    with open(PROFILES_FILE, "r", encoding="utf-8") as f:
        profiles = json.load(f)

    return [normalize_profile(profile) for profile in profiles]


def save_profiles(profiles):
    ensure_dirs()

    profiles = [normalize_profile(profile) for profile in profiles]

    with open(PROFILES_FILE, "w", encoding="utf-8") as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

    return profiles


def get_profile(profile_id: str):
    profiles = load_profiles()

    for profile in profiles:
        if profile.get("id") == profile_id:
            return normalize_profile(profile)

    return None


def create_profile(name: str):
    name = str(name or "").strip()

    if not name:
        raise ValueError("映射名不能为空")

    profiles = load_profiles()
    app_settings = load_app_settings()
    document_no_settings = deepcopy(DEFAULT_DOCUMENT_NO_SETTINGS)
    document_no_settings["default_sales_name"] = app_settings.get("default_sales_name") or DEFAULT_APP_SETTINGS["default_sales_name"]
    document_no_settings["default_salesperson_code"] = app_settings.get("default_salesperson_code") or DEFAULT_APP_SETTINGS["default_salesperson_code"]
    document_no_settings["default_company_code"] = app_settings.get("default_company_code") or DEFAULT_APP_SETTINGS["default_company_code"]
    document_no_settings["default_sequence"] = app_settings.get("default_sequence") or DEFAULT_APP_SETTINGS["default_sequence"]

    profile = {
        "id": str(uuid4()),
        "name": name,
        "template_file": "",
        "template_display_name": "",
        "profile_version": "v3",
        "mappings": {},
        "mapping_order": [],
        "mapping_defaults": {},
        # legacy composite mapping compatibility
        "composite_mappings": [],
        "document_no_settings": document_no_settings,
        "description_settings": deepcopy(DEFAULT_DESCRIPTION_SETTINGS),
        "image_fields": [],
        "layout_preview": deepcopy(DEFAULT_LAYOUT_PREVIEW),
    }

    profiles.append(profile)
    save_profiles(profiles)

    return normalize_profile(profile)


def delete_profile(profile_id: str):
    profiles = load_profiles()
    profile = get_profile(profile_id)

    if not profile:
        raise ValueError("映射不存在")

    template_file = profile.get("template_file")

    if template_file:
        file_path = TEMPLATE_UPLOAD_DIR / template_file
        if file_path.exists():
            file_path.unlink()

    new_profiles = [
        profile for profile in profiles
        if profile.get("id") != profile_id
    ]

    save_profiles(new_profiles)

    return {
        "deleted": profile_id
    }


def update_profile_mappings(
    profile_id: str,
    mappings: dict,
    composite_mappings=None,
    document_no_settings=None,
    mapping_defaults=None,
        description_settings=None,
        image_fields=None,
        layout_config=None,
        layout_preview=None,
        mapping_order=None,
):
    profiles = load_profiles()

    for profile in profiles:
        if profile.get("id") == profile_id:
            if mappings is not None:
                clean_mappings = {}

                for key, cell in (mappings or {}).items():
                    key = str(key or "").strip()
                    if key in RESERVED_DOCUMENT_MAPPING_KEYS:
                        continue
                    cell = str(cell or "").strip().upper()

                    if key and cell:
                        clean_mappings[key] = cell

                profile["mappings"] = clean_mappings
                clean_order = []
                if isinstance(mapping_order, list):
                    for key in mapping_order:
                        key = str(key or "").strip()
                        if key in clean_mappings and key not in clean_order:
                            clean_order.append(key)
                for key in clean_mappings.keys():
                    if key not in clean_order:
                        clean_order.append(key)
                profile["mapping_order"] = clean_order
            # legacy composite mapping compatibility
            if composite_mappings is not None:
                clean_composite_mappings = []

                for item in composite_mappings:
                    cell = str(item.get("cell", "")).strip().upper()
                    template = str(item.get("template", "")).strip()

                    if cell and template:
                        clean_composite_mappings.append({
                            "cell": cell,
                            "template": template
                        })

                profile["composite_mappings"] = clean_composite_mappings

            if mapping_defaults is not None:
                current_mappings = _strip_reserved_from_mappings(profile.get("mappings") or {})
                clean_defaults = {}
                for key, val in (mapping_defaults or {}).items():
                    key = str(key or "").strip()
                    if not key or key in RESERVED_DOCUMENT_MAPPING_KEYS:
                        continue
                    if key not in current_mappings:
                        continue
                    clean_defaults[key] = str(val) if val is not None else ""
                profile["mapping_defaults"] = clean_defaults

            if document_no_settings is not None:
                current = profile.get("document_no_settings")
                merged = {}
                if isinstance(current, dict):
                    merged.update(current)
                if isinstance(document_no_settings, dict):
                    merged.update(document_no_settings)
                profile["document_no_settings"] = normalize_document_no_settings(merged)

            if description_settings is not None:
                current = profile.get("description_settings")
                merged = {}
                if isinstance(current, dict):
                    merged.update(current)
                if isinstance(description_settings, dict):
                    merged.update(description_settings)
                profile["description_settings"] = normalize_description_settings(merged)

            if image_fields is not None:
                profile["image_fields"] = normalize_image_mappings(image_fields, validate=True)

            if layout_config is not None:
                profile["layout_config"] = normalize_layout_config(layout_config)

            if layout_preview is not None:
                current = profile.get("layout_preview")
                merged = {}
                if isinstance(current, dict):
                    merged.update(current)
                if isinstance(layout_preview, dict):
                    merged.update(layout_preview)
                profile["layout_preview"] = normalize_layout_preview(merged)

            save_profiles(profiles)

            return normalize_profile(profile)

    raise ValueError("映射不存在")


def upload_template_file(profile_id: str, uploaded_file):
    profiles = load_profiles()

    for profile in profiles:
        if profile.get("id") == profile_id:
            ensure_dirs()

            original_name = uploaded_file.filename or "template.xlsx"
            suffix = Path(original_name).suffix.lower()

            if suffix not in [".xlsx", ".xlsm"]:
                raise ValueError("只支持上传 .xlsx 或 .xlsm 文件")

            filename = f"{profile_id}{suffix}"
            target_path = TEMPLATE_UPLOAD_DIR / filename
            old_template = str(profile.get("template_file") or "").strip()
            if old_template and old_template != filename:
                old_path = TEMPLATE_UPLOAD_DIR / Path(old_template).name
                if old_path.exists():
                    old_path.unlink()

            with target_path.open("wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)

            profile["template_file"] = filename
            profile["template_display_name"] = original_name

            save_profiles(profiles)

            return normalize_profile(profile)

    raise ValueError("映射不存在")


def delete_template_file(profile_id: str):
    profiles = load_profiles()

    for profile in profiles:
        if profile.get("id") == profile_id:
            template_file = str(profile.get("template_file") or "").strip()

            if template_file:
                file_path = TEMPLATE_UPLOAD_DIR / Path(template_file).name
                if file_path.exists():
                    file_path.unlink()

            profile["template_file"] = ""
            profile["template_display_name"] = ""
            save_profiles(profiles)

            return normalize_profile(profile)

    raise ValueError("映射不存在")
