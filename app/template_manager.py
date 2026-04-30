import json
import shutil
from pathlib import Path
from uuid import uuid4

BASE = Path(__file__).resolve().parent.parent
DATA = BASE / "data/template_profiles.json"
UPLOAD = BASE / "templates/uploads"


def load_profiles():
    if not DATA.exists():
        return []
    return json.loads(DATA.read_text("utf-8"))


def save(profiles):
    DATA.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), "utf-8")


def get_profile(pid):
    return next(p for p in load_profiles() if p["id"] == pid)


def create_profile(name):
    profiles = load_profiles()
    p = {
        "id": str(uuid4()),
        "name": name,
        "template_file": "",
        "mappings": {},
        "composite_mappings": []
    }
    profiles.append(p)
    save(profiles)
    return p


def delete_profile(pid):
    profiles = load_profiles()
    profiles = [p for p in profiles if p["id"] != pid]
    save(profiles)
    return pid


def update_profile_mappings(pid, mappings, composite):
    profiles = load_profiles()
    for p in profiles:
        if p["id"] == pid:
            p["mappings"] = mappings
            p["composite_mappings"] = composite
    save(profiles)
    return get_profile(pid)


def upload_template_file(pid, file):
    filename = f"{pid}.xlsx"
    path = UPLOAD / filename

    with path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    profiles = load_profiles()
    for p in profiles:
        if p["id"] == pid:
            p["template_file"] = filename

    save(profiles)
    return get_profile(pid)
