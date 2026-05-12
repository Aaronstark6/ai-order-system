import re
import shutil
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment

from app.app_settings import get_export_sync_dir
from app.template_manager import (
    DEFAULT_DOCUMENT_NO_SETTINGS,
    RESERVED_DOCUMENT_MAPPING_KEYS,
    get_profile,
)
from app.description_template_manager import (
    get_description_template,
    render_description_template,
)


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


def format_deal_date_yyyymmdd(value):
    text = str(value or "").strip()
    if not text:
        return ""

    text = text.replace("/", "-")
    digits = re.sub(r"\D", "", text)

    if len(digits) == 8:
        return digits

    return ""


def format_deal_date_month_day(value):
    yyyymmdd = format_deal_date_yyyymmdd(value)
    if not yyyymmdd:
        return ""

    return yyyymmdd[4:].lstrip("0")


def get_dosage_form_code(product_form):
    text = str(product_form or "").strip()
    form_code_map = {
        "硬胶囊": "C",
        "胶囊": "C",
        "软胶囊": "S",
        "软糖": "G",
        "滴剂": "D",
        "压片": "T",
        "片剂": "T",
        "泡腾片": "E",
        "固体饮料": "B",
        "粉末": "P",
        "精油": "D",
        "凝胶": "N",
        "果冻和凝胶": "N",
    }
    return form_code_map.get(text, "")


def build_product_code(data: dict):
    salesperson_code = str(data.get("salesperson_code") or "").strip()
    month_day = format_deal_date_month_day(data.get("deal_date"))
    ingredient_initials = str(data.get("ingredient_initials") or "").strip().upper()
    dosage_form_code = get_dosage_form_code(data.get("product_form"))

    data["dosage_form_code"] = dosage_form_code
    return f"{salesperson_code}{month_day}{ingredient_initials}{dosage_form_code}"


def build_document_no(data: dict):
    yyyymmdd = format_deal_date_yyyymmdd(data.get("deal_date"))
    if not yyyymmdd:
        return ""

    product_code = build_product_code(data)
    data["product_code"] = product_code

    sales_name = str(data.get("sales_name") or "").strip()
    company_code = str(data.get("company_code") or "").strip()
    sequence = str(data.get("sequence") or "").strip()
    return f"{sales_name}-{company_code}{yyyymmdd}{sequence}-{product_code}"


def render_placeholder_rule(rule: str, data: dict):
    rule = str(rule or "").strip()
    if not rule:
        return ""

    def replace_placeholder(match):
        key = match.group(1).strip()
        if key == "deal_date_yyyymmdd":
            value = format_deal_date_yyyymmdd(data.get("deal_date"))
        elif key == "deal_date_mmdd_no_leading_zero":
            value = format_deal_date_month_day(data.get("deal_date"))
        else:
            value = data.get(key)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{([^{}]+)\}", replace_placeholder, rule).strip()


def _apply_document_no_defaults(data: dict, settings: dict):
    if not str(data.get("sales_name") or "").strip():
        data["sales_name"] = str(settings.get("default_sales_name") or "").strip()
    if not str(data.get("salesperson_code") or "").strip():
        data["salesperson_code"] = str(settings.get("default_salesperson_code") or "").strip()
    if not str(data.get("company_code") or "").strip():
        data["company_code"] = str(settings.get("default_company_code") or "").strip()
    if not str(data.get("sequence") or "").strip():
        data["sequence"] = str(settings.get("default_sequence") or "").strip()
    if not str(data.get("deal_date") or "").strip():
        data["deal_date"] = datetime.now().strftime("%Y-%m-%d")


def write_cell(sheet, cell, value):
    cell = str(cell or "").strip().upper()

    if not cell:
        return

    sheet[cell] = value


def set_wrap_text(sheet, cell):
    old_alignment = sheet[cell].alignment

    sheet[cell].alignment = Alignment(
        horizontal=old_alignment.horizontal,
        vertical=old_alignment.vertical,
        text_rotation=old_alignment.text_rotation,
        wrap_text=True,
        shrink_to_fit=old_alignment.shrink_to_fit,
        indent=old_alignment.indent
    )


def normalize_composite_values(composite_data=None, composite_values=None):
    # 向后兼容：旧调用使用 composite_values，新调用使用 composite_data
    raw = composite_data if composite_data is not None else composite_values

    if raw is None:
        return {}

    if isinstance(raw, dict):
        return {
            str(cell or "").strip().upper(): value
            for cell, value in raw.items()
            if str(cell or "").strip()
        }

    if isinstance(raw, list):
        normalized = {}

        for item in raw:
            if not isinstance(item, dict):
                continue

            cell = str(item.get("cell", "")).strip().upper()
            if not cell:
                continue

            value = item.get("value")
            if value is None:
                value = item.get("text")
            if value is None:
                value = item.get("content", "")

            normalized[cell] = value

        return normalized

    return {}


def _apply_mapping_defaults(data: dict, profile: dict):
    mapping_defaults = profile.get("mapping_defaults") or {}
    if not isinstance(mapping_defaults, dict):
        return

    for key, dv in mapping_defaults.items():
        k = str(key or "").strip()
        if not k or k in RESERVED_DOCUMENT_MAPPING_KEYS:
            continue

        cur = data.get(k)
        if isinstance(cur, str):
            if cur.strip():
                continue
        elif cur is not None and cur != "":
            continue

        if dv is not None and str(dv).strip() != "":
            data[k] = str(dv)


def generate_excel(data: dict, profile_id: str, composite_data=None, composite_values=None, description_text=None):
    if composite_values is None:
        composite_values = {}
    composite_values = normalize_composite_values(
        composite_data=composite_data,
        composite_values=composite_values
    )

    if not isinstance(data, dict):
        data = {}

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

    mappings = profile.get("mappings", {}) or {}
    composite_mappings = profile.get("composite_mappings", []) or {}
    description_settings = profile.get("description_settings", {}) or {}

    _apply_mapping_defaults(data, profile)

    settings = dict(DEFAULT_DOCUMENT_NO_SETTINGS)
    raw_settings = profile.get("document_no_settings")
    if isinstance(raw_settings, dict):
        settings.update(raw_settings)

    _apply_document_no_defaults(data, settings)

    product_code = build_product_code(data)
    data["product_code"] = product_code

    manual_document_no = str(data.get("document_no") or "").strip()
    if manual_document_no:
        document_no = manual_document_no
    else:
        document_no = build_document_no(data)
    data["document_no"] = document_no

    if not mappings and not composite_mappings and not description_settings.get("enabled"):
        return {
            "success": False,
            "error": f"映射「{profile.get('name')}」还没有配置字段单元格"
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    workbook = load_workbook(template_path)
    sheet = workbook.active

    # 普通字段映射（文档编号相关 key 仅由 document_no_settings 处理，不在此写入）
    for field_key, cell in mappings.items():
        fk = str(field_key or "").strip()
        if fk in RESERVED_DOCUMENT_MAPPING_KEYS:
            continue

        value = data.get(field_key, "")

        if value is None:
            value = ""

        try:
            write_cell(sheet, cell, value)
        except Exception as e:
            return {
                "success": False,
                "error": f"普通字段 {field_key} → {cell} 写入失败：{str(e)}"
            }

    # 组合单元格映射
    for item in composite_mappings:
        cell = str(item.get("cell", "")).strip().upper()
        template = item.get("template", "")

        if not cell:
            continue

        try:
            # 优先使用首页编辑后的组合单元格内容
            if cell in composite_values:
                final_text = composite_values.get(cell, "")
            else:
                final_text = render_composite_template(template, data)

            write_cell(sheet, cell, final_text)
            set_wrap_text(sheet, cell)

        except Exception as e:
            return {
                "success": False,
                "error": f"组合单元格 {cell} 写入失败：{str(e)}"
            }

    # 产品描述独立于组合单元格；若目标单元格相同，此处后写入以优先使用 description_text。
    if description_settings.get("enabled") is True:
        target_cell = str(description_settings.get("target_cell") or "").strip().upper()
        if target_cell:
            try:
                final_description = description_text

                if final_description is None or str(final_description).strip() == "":
                    template_name = str(description_settings.get("template_name") or "").strip()
                    if template_name:
                        template = get_description_template(template_name)
                        final_description = render_description_template(template, data)
                    else:
                        final_description = ""

                write_cell(sheet, target_cell, final_description)
                set_wrap_text(sheet, target_cell)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"产品描述写入 {target_cell} 失败：{str(e)}"
                }

    # 文档编号写入专用单元格（最后写入，避免被组合单元格覆盖）
    if settings.get("enabled", True):
        doc_cell = str(settings.get("document_no_cell") or "").strip().upper()
        if doc_cell:
            try:
                write_cell(sheet, doc_cell, data.get("document_no", ""))
            except Exception as e:
                return {
                    "success": False,
                    "error": f"文档编号写入 {doc_cell} 失败：{str(e)}"
                }

    customer_name = safe_filename_text(data.get("customer_name") or "客户")
    product_name = safe_filename_text(data.get("product_name") or "订单")
    profile_name = safe_filename_text(profile.get("name") or "模板")

    use_doc_filename = bool(settings.get("use_document_no_as_filename", True))
    if use_doc_filename and str(data.get("document_no") or "").strip():
        filename = f"{safe_filename_text(data.get('document_no'))}.xlsx"
    else:
        filename = f"{profile_name}_{product_name}_{customer_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    output_file = OUTPUT_DIR / filename

    workbook.save(output_file)

    synced = False
    sync_path = ""
    sync_error = ""
    sync_dir = str(get_export_sync_dir() or "").strip()

    if sync_dir:
        try:
            sync_target_dir = Path(sync_dir).expanduser()
            sync_target_dir.mkdir(parents=True, exist_ok=True)
            sync_target_file = sync_target_dir / filename
            shutil.copy2(output_file, sync_target_file)
            synced = True
            sync_path = str(sync_target_file)
        except Exception as e:
            sync_error = str(e)

    return {
        "success": True,
        "filename": filename,
        "output_path": str(output_file),
        "download_url": f"/api/download/{filename}",
        "synced": synced,
        "sync_path": sync_path,
        "sync_error": sync_error
    }
