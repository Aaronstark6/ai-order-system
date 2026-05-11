import json
import shutil
from copy import deepcopy
from pathlib import Path
from uuid import uuid4


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
    "default_sales_name": "Anna",
    "default_salesperson_code": "AN",
    "default_company_code": "GS",
    "default_sequence": "A01",
    "document_no_rule": "{sales_name}-{company_code}{deal_date_yyyymmdd}{sequence}-{product_code}",
    "product_code_rule": "{salesperson_code}{product_index_or_day}{product_abbr}{dosage_form_code}",
}

DEFAULT_DESCRIPTION_SETTINGS = {
    "enabled": False,
    "template_name": "",
    "target_cell": "",
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
    merged["default_sales_name"] = str(merged.get("default_sales_name") or "Anna").strip() or "Anna"
    merged["default_salesperson_code"] = str(merged.get("default_salesperson_code") or "AN").strip() or "AN"
    merged["default_company_code"] = str(merged.get("default_company_code") or "GS").strip() or "GS"
    merged["default_sequence"] = str(merged.get("default_sequence") or "A01").strip() or "A01"

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

    if "template_file" not in profile:
        profile["template_file"] = ""

    if "mappings" not in profile:
        profile["mappings"] = {}

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

    if "document_no_rule" in profile:
        del profile["document_no_rule"]

    profile["mappings"] = _strip_reserved_from_mappings(profile.get("mappings") or {})

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

    profile = {
        "id": str(uuid4()),
        "name": name,
        "template_file": "",
        "mappings": {},
        "mapping_defaults": {},
        "composite_mappings": [],
        "document_no_settings": deepcopy(DEFAULT_DOCUMENT_NO_SETTINGS),
        "description_settings": deepcopy(DEFAULT_DESCRIPTION_SETTINGS),
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
):
    profiles = load_profiles()

    if composite_mappings is None:
        composite_mappings = []

    for profile in profiles:
        if profile.get("id") == profile_id:
            clean_mappings = {}

            for key, cell in (mappings or {}).items():
                key = str(key or "").strip()
                if key in RESERVED_DOCUMENT_MAPPING_KEYS:
                    continue
                cell = str(cell or "").strip().upper()

                if key and cell:
                    clean_mappings[key] = cell

            clean_composite_mappings = []

            for item in composite_mappings:
                cell = str(item.get("cell", "")).strip().upper()
                template = str(item.get("template", "")).strip()

                if cell and template:
                    clean_composite_mappings.append({
                        "cell": cell,
                        "template": template
                    })

            profile["mappings"] = clean_mappings
            profile["composite_mappings"] = clean_composite_mappings

            if mapping_defaults is not None:
                clean_defaults = {}
                for key, val in (mapping_defaults or {}).items():
                    key = str(key or "").strip()
                    if not key or key in RESERVED_DOCUMENT_MAPPING_KEYS:
                        continue
                    if key not in clean_mappings:
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

            with target_path.open("wb") as buffer:
                shutil.copyfileobj(uploaded_file.file, buffer)

            profile["template_file"] = filename

            save_profiles(profiles)

            return normalize_profile(profile)

    raise ValueError("映射不存在")
