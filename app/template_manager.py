import json
import shutil
from pathlib import Path
from uuid import uuid4


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMPLATE_UPLOAD_DIR = BASE_DIR / "templates" / "uploads"
PROFILES_FILE = DATA_DIR / "template_profiles.json"


def ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMPLATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


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

    if "document_no_rule" not in profile:
        profile["document_no_rule"] = ""

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
        "composite_mappings": [],
        "document_no_rule": ""
    }

    profiles.append(profile)
    save_profiles(profiles)

    return profile


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


def update_profile_mappings(profile_id: str, mappings: dict, composite_mappings=None, document_no_rule: str = ""):
    profiles = load_profiles()

    if composite_mappings is None:
        composite_mappings = []

    for profile in profiles:
        if profile.get("id") == profile_id:
            clean_mappings = {}

            for key, cell in mappings.items():
                key = str(key or "").strip()
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
            profile["document_no_rule"] = str(document_no_rule or "").strip()

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
