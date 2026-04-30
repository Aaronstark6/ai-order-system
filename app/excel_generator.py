import re
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment

from app.template_manager import get_profile


BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_UPLOAD_DIR = BASE_DIR / "templates" / "uploads"
OUTPUT_DIR = BASE_DIR / "output"


def safe_filename_text(text):
    text = str(text or "").strip()

    if not text:
        return "unknown"

    bad_chars = ["/", "\\", ":", "*", "?", "\"", "<", ">", "|"]

    for char in bad_chars:
        text = text.replace(char, "_")

    return text


def render_composite_template(template: str, data: dict):
    def replace_placeholder(match):
        key = match.group(1).strip()
        value = data.get(key)

        if value is None:
            return ""

        return str(value)

    return re.sub(r"\{([^{}]+)\}", replace_placeholder, template)


def generate_excel(data: dict, profile_id: str):
    profile = get_profile(profile_id)

    if not profile:
        return {
            "success": False,
            "error": "请选择有效的模板映射"
        }

    template_file = profile.get("template_file")

    if not template_file:
        return {
            "success": False,
            "error": f"映射「{profile.get('name')}」还没有上传Excel模板"
        }

    template_path = TEMPLATE_UPLOAD_DIR / template_file

    if not template_path.exists():
        return {
            "success": False,
            "error": f"模板文件不存在：{template_path}"
        }

    mappings = profile.get("mappings", {})
    composite_mappings = profile.get("composite_mappings", [])

    if not mappings and not composite_mappings:
        return {
            "success": False,
            "error": f"映射「{profile.get('name')}」还没有配置字段单元格"
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    workbook = load_workbook(template_path)
    sheet = workbook.active

    # 普通字段映射
    for field_key, cell in mappings.items():
        value = data.get(field_key)

        if value is None:
            value = ""

        try:
            sheet[cell] = value
        except Exception as e:
            return {
                "success": False,
                "error": f"字段 {field_key} 的单元格位置 {cell} 无效：{str(e)}"
            }

    # 组合单元格映射
    for item in composite_mappings:
        cell = item.get("cell", "")
        template = item.get("template", "")

        if not cell or not template:
            continue

        try:
            rendered_text = render_composite_template(template, data)
            sheet[cell] = rendered_text

            old_alignment = sheet[cell].alignment
            sheet[cell].alignment = Alignment(
                horizontal=old_alignment.horizontal,
                vertical=old_alignment.vertical,
                text_rotation=old_alignment.text_rotation,
                wrap_text=True,
                shrink_to_fit=old_alignment.shrink_to_fit,
                indent=old_alignment.indent
            )

        except Exception as e:
            return {
                "success": False,
                "error": f"组合单元格 {cell} 写入失败：{str(e)}"
            }

    customer_name = safe_filename_text(data.get("customer_name") or "客户")
    product_name = safe_filename_text(data.get("product_name") or "订单")
    profile_name = safe_filename_text(profile.get("name") or "模板")

    filename = f"{profile_name}_{product_name}_{customer_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_file = OUTPUT_DIR / filename

    workbook.save(output_file)

    return {
        "success": True,
        "filename": filename,
        "download_url": f"/api/download/{filename}"
    }
