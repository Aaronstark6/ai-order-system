import re
from copy import copy

try:
    from openpyxl.drawing.image import Image as ExcelImage
except ImportError:
    ExcelImage = None
from openpyxl.utils import column_index_from_string, get_column_letter

from app.image_manager import resolve_uploaded_image_path
from app.layout_schema import normalize_layout_config


CELL_RANGE_RE = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)(?::\$?[A-Z]{1,3}\$?\d+)?$")


def _left_top_cell(range_text):
    text = str(range_text or "").strip().upper()
    if not text:
        return ""

    match = CELL_RANGE_RE.match(text)
    if not match:
        raise ValueError(f"Excel区域格式非法：{text}")
    return f"{match.group(1)}{match.group(2)}"


def _offset_cell(cell_ref, row_offset=0, col_offset=0):
    match = CELL_RANGE_RE.match(str(cell_ref or "").strip().upper())
    if not match:
        raise ValueError(f"Excel单元格格式非法：{cell_ref}")

    col_index = column_index_from_string(match.group(1)) + int(col_offset or 0)
    row_index = int(match.group(2)) + int(row_offset or 0)
    if col_index < 1 or row_index < 1:
        raise ValueError(f"Excel单元格格式非法：{cell_ref}")
    return f"{get_column_letter(col_index)}{row_index}"


def _render_description_fields(description_fields):
    if not isinstance(description_fields, dict) or not description_fields:
        return ""

    parts = []
    for key, value in description_fields.items():
        field_name = str(key or "").strip()
        field_value = "" if value is None else str(value).strip()
        if not field_name or not field_value:
            continue

        if "\n" in field_value:
            parts.append(f"{field_name}：\n{field_value}")
        else:
            parts.append(f"{field_name}：{field_value}")

    return "\n\n".join(parts)


def _set_wrap_text_only(cell):
    current = copy(cell.alignment)
    current.wrap_text = True
    cell.alignment = current


def _render_block(block, description_fields=None):
    block_type = str(block.get("type") or "").strip()
    if block_type != "description_fields":
        return ""
    return _render_description_fields(description_fields)


def _to_positive_number(value):
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0:
        return None
    return number


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def _apply_image_size(img, options):
    if not isinstance(options, dict):
        options = {}

    width = _to_positive_number(options.get("width"))
    height = _to_positive_number(options.get("height"))
    keep_ratio = _to_bool(options.get("keep_ratio"), default=True)
    if not width and not height:
        return

    if not keep_ratio:
        if width:
            img.width = round(width)
        if height:
            img.height = round(height)
        return

    original_width = _to_positive_number(getattr(img, "width", None))
    original_height = _to_positive_number(getattr(img, "height", None))
    if not original_width or not original_height:
        if width:
            img.width = round(width)
        if height:
            img.height = round(height)
        return

    if width and height:
        scale = min(width / original_width, height / original_height)
    elif width:
        scale = width / original_width
    else:
        scale = height / original_height

    img.width = round(original_width * scale)
    img.height = round(original_height * scale)


def _render_image_block(sheet, block, image_data, target_cell):
    source = str(block.get("source") or "").strip()
    if not source or not isinstance(image_data, dict):
        return False

    item = image_data.get(source)
    if not isinstance(item, dict):
        return False

    image_path = resolve_uploaded_image_path(item.get("image_path"))
    if not image_path:
        return False

    if ExcelImage is None:
        raise RuntimeError("图片渲染需要安装 pillow。")

    try:
        img = ExcelImage(str(image_path))
    except ImportError as e:
        raise RuntimeError("图片渲染需要安装 pillow。") from e

    _apply_image_size(img, block.get("options") if isinstance(block.get("options"), dict) else {})
    sheet.add_image(img, target_cell)
    return True


def _source_keys_from_options(options):
    if not isinstance(options, dict):
        return []

    raw_keys = options.get("source_keys")
    if isinstance(raw_keys, list):
        values = raw_keys
    elif isinstance(raw_keys, str):
        values = raw_keys.split(",")
    else:
        values = []

    keys = []
    seen = set()
    for value in values:
        key = str(value or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _positive_int(value, default):
    number = _to_positive_number(value)
    if not number:
        return default
    return max(1, int(round(number)))


def _gallery_image_options(options):
    if not isinstance(options, dict):
        options = {}
    return {
        "width": options.get("image_width") or 180,
        "height": options.get("image_height") or 140,
        "keep_ratio": options.get("keep_ratio"),
    }


def _render_image_gallery_block(sheet, block, image_data, target_cell):
    if not isinstance(image_data, dict):
        return []

    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    source_keys = _source_keys_from_options(options)
    if not source_keys:
        return []

    columns = _positive_int(options.get("columns"), 3)
    row_step = _positive_int(options.get("row_step"), 8)
    col_step = _positive_int(options.get("col_step"), 4)
    size_options = _gallery_image_options(options)
    written_cells = []
    image_index = 0

    for key in source_keys:
        item = image_data.get(key)
        if not isinstance(item, dict):
            continue

        image_path = resolve_uploaded_image_path(item.get("image_path"))
        if not image_path:
            continue

        if ExcelImage is None:
            raise RuntimeError("图片渲染需要安装 pillow。")

        try:
            img = ExcelImage(str(image_path))
        except ImportError as e:
            raise RuntimeError("图片渲染需要安装 pillow。") from e

        row_index = image_index // columns
        col_index = image_index % columns
        cell = _offset_cell(
            target_cell,
            row_offset=row_index * row_step,
            col_offset=col_index * col_step,
        )
        _apply_image_size(img, size_options)
        sheet.add_image(img, cell)
        written_cells.append(cell)
        image_index += 1

    return written_cells


def collect_layout_image_keys(profile):
    if not isinstance(profile, dict):
        return set()

    raw_config = profile.get("layout_config")
    if not isinstance(raw_config, dict):
        return set()

    layout_config = normalize_layout_config(raw_config)
    if layout_config.get("enabled") is not True:
        return set()

    keys = set()
    for region in layout_config.get("regions", []):
        if not isinstance(region, dict) or region.get("enabled") is False:
            continue
        if str(region.get("sheet") or "active").strip().lower() != "active":
            continue
        if not str(region.get("range") or "").strip():
            continue

        blocks = region.get("blocks")
        if not isinstance(blocks, list):
            continue

        for block in blocks:
            if not isinstance(block, dict) or block.get("enabled") is not True:
                continue
            block_type = str(block.get("type") or "").strip()
            if block_type == "image":
                source = str(block.get("source") or "").strip()
                if source:
                    keys.add(source)
            elif block_type == "image_gallery":
                options = block.get("options") if isinstance(block.get("options"), dict) else {}
                keys.update(_source_keys_from_options(options))
    return keys


def render_layout(workbook, data, profile, description_fields=None, description_text=None, image_data=None):
    try:
        if workbook is None:
            return {"success": False, "error": "workbook 不能为空"}
        if not isinstance(profile, dict):
            return {"success": False, "error": "profile 格式异常"}

        raw_config = profile.get("layout_config")
        if raw_config is None:
            return {
                "success": True,
                "skipped": True,
                "regions_count": 0,
                "blocks_count": 0,
                "written_cells": [],
                "written_images": [],
            }
        if not isinstance(raw_config, dict):
            return {"success": False, "error": "layout_config 格式异常"}

        layout_config = normalize_layout_config(raw_config)
        if layout_config.get("enabled") is not True:
            return {
                "success": True,
                "skipped": True,
                "regions_count": 0,
                "blocks_count": 0,
                "written_cells": [],
                "written_images": [],
            }

        regions_count = 0
        blocks_count = 0
        written_cells = []
        written_images = []

        for region in layout_config.get("regions", []):
            if not isinstance(region, dict):
                return {"success": False, "error": "layout region 格式异常"}
            if region.get("enabled") is False:
                continue

            sheet_name = str(region.get("sheet") or "active").strip().lower()
            if sheet_name != "active":
                continue

            range_text = str(region.get("range") or "").strip()
            if not range_text:
                continue

            try:
                target_cell = _left_top_cell(range_text)
            except ValueError as e:
                return {
                    "success": False,
                    "error": f"layout region {region.get('id') or region.get('name') or ''} {str(e)}".strip(),
                }

            blocks = region.get("blocks")
            if not isinstance(blocks, list):
                return {"success": False, "error": f"layout region {region.get('id') or ''} blocks 格式异常"}

            region_parts = []
            region_written = False
            for block in blocks:
                if not isinstance(block, dict):
                    return {"success": False, "error": "layout block 格式异常"}
                if block.get("enabled") is not True:
                    continue

                block_type = str(block.get("type") or "").strip()
                if block_type == "description_fields":
                    block_text = _render_block(block, description_fields=description_fields)
                    if not block_text:
                        continue

                    blocks_count += 1
                    region_parts.append(block_text)
                    continue

                if block_type == "image":
                    try:
                        inserted = _render_image_block(workbook.active, block, image_data, target_cell)
                    except RuntimeError as e:
                        return {"success": False, "error": str(e)}
                    if not inserted:
                        continue

                    blocks_count += 1
                    region_written = True
                    written_images.append(target_cell)
                    continue

                if block_type == "image_gallery":
                    try:
                        gallery_cells = _render_image_gallery_block(workbook.active, block, image_data, target_cell)
                    except RuntimeError as e:
                        return {"success": False, "error": str(e)}
                    if not gallery_cells:
                        continue

                    blocks_count += 1
                    region_written = True
                    written_images.extend(gallery_cells)
                    continue

                continue

            if not region_parts and not region_written:
                continue

            regions_count += 1
            if region_parts:
                cell = workbook.active[target_cell]
                cell.value = "\n\n".join(region_parts)
                _set_wrap_text_only(cell)
                written_cells.append(target_cell)

        return {
            "success": True,
            "skipped": False,
            "regions_count": regions_count,
            "blocks_count": blocks_count,
            "written_cells": written_cells,
            "written_images": written_images,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
