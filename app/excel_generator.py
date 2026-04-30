import re
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import Alignment

from app.template_manager import get_profile

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_DIR / "templates/uploads"
OUTPUT_DIR = BASE_DIR / "output"


def render(template, data):
    return re.sub(r"\{(.*?)\}", lambda m: str(data.get(m.group(1), "")), template)


def generate_excel(data, profile_id):
    profile = get_profile(profile_id)
    template_path = TEMPLATE_DIR / profile["template_file"]

    wb = load_workbook(template_path)
    ws = wb.active

    # 普通字段
    for k, cell in profile["mappings"].items():
        ws[cell] = data.get(k, "")

    # 组合字段
    for item in profile["composite_mappings"]:
        text = render(item["template"], data)
        ws[item["cell"]] = text
        ws[item["cell"]].alignment = Alignment(wrap_text=True)

    filename = f"order_{datetime.now().strftime('%H%M%S')}.xlsx"
    path = OUTPUT_DIR / filename
    wb.save(path)

    return {
        "success": True,
        "download_url": f"/api/download/{filename}"
    }
