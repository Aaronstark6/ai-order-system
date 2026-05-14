import re
from copy import copy

try:
    from openpyxl.drawing.image import Image as ExcelImage
    from openpyxl.drawing.spreadsheet_drawing import AnchorMarker, OneCellAnchor
    from openpyxl.drawing.xdr import XDRPositiveSize2D
except ImportError:
    ExcelImage = None
    AnchorMarker = None
    OneCellAnchor = None
    XDRPositiveSize2D = None
from openpyxl.utils import column_index_from_string, get_column_letter

from app.image_manager import resolve_uploaded_image_path
from app.layout_schema import normalize_layout_config


CELL_RANGE_RE = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?$")
EMU_PER_PIXEL = 9525


def _left_top_cell(range_text):
    text = str(range_text or "").strip().upper()
    if not text:
        return ""

    match = CELL_RANGE_RE.match(text)
    if not match:
        raise ValueError(f"Excel区域格式非法：{text}")
    return f"{match.group(1)}{match.group(2)}"


def _range_row_bounds(range_text):
    text = str(range_text or "").strip().upper()
    match = CELL_RANGE_RE.match(text)
    if not match:
        raise ValueError(f"Invalid Excel range: {text}")

    start_row = int(match.group(2))
    end_row = int(match.group(4) or start_row)
    return min(start_row, end_row), max(start_row, end_row)


def _cell_position(cell_ref):
    match = CELL_RANGE_RE.match(str(cell_ref or "").strip().upper())
    if not match:
        raise ValueError(f"Invalid Excel cell: {cell_ref}")

    return column_index_from_string(match.group(1)), int(match.group(2))


def _offset_cell(cell_ref, row_offset=0, col_offset=0):
    match = CELL_RANGE_RE.match(str(cell_ref or "").strip().upper())
    if not match:
        raise ValueError(f"Excel单元格格式非法：{cell_ref}")

    col_index = column_index_from_string(match.group(1)) + int(col_offset or 0)
    row_index = int(match.group(2)) + int(row_offset or 0)
    if col_index < 1 or row_index < 1:
        raise ValueError(f"Excel单元格格式非法：{cell_ref}")
    return f"{get_column_letter(col_index)}{row_index}"


def pixels_to_emu(px):
    number = _to_positive_number(px)
    if not number:
        return 0
    return int(round(number * EMU_PER_PIXEL))


def add_image_with_offset(sheet, img, cell, offset_x_px=0, offset_y_px=0):
    if AnchorMarker is None or OneCellAnchor is None or XDRPositiveSize2D is None:
        raise RuntimeError("图片渲染需要安装 pillow。")

    col_index, row_index = _cell_position(cell)
    marker = AnchorMarker(
        col=col_index - 1,
        row=row_index - 1,
        colOff=pixels_to_emu(offset_x_px),
        rowOff=pixels_to_emu(offset_y_px),
    )
    img.anchor = OneCellAnchor(
        _from=marker,
        ext=XDRPositiveSize2D(
            cx=pixels_to_emu(getattr(img, "width", 0)),
            cy=pixels_to_emu(getattr(img, "height", 0)),
        ),
    )
    sheet.add_image(img)


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


def _non_negative_number(value, default=0):
    if value is None or value == "":
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(0, number)


def _row_height_to_px(height_points):
    number = _to_positive_number(height_points)
    if not number:
        return None
    return number * 96 / 72


def estimate_region_height_px(sheet, range_ref):
    text = str(range_ref or "").strip().upper()
    if not text:
        return None

    try:
        min_row, max_row = _range_row_bounds(text)
    except ValueError:
        return None

    default_height = _row_height_to_px(getattr(sheet.sheet_format, "defaultRowHeight", None)) or 20
    total = 0
    for row_index in range(min_row, max_row + 1):
        row_height = _row_height_to_px(sheet.row_dimensions[row_index].height)
        total += row_height or default_height
    return total


def _gallery_image_options(options):
    if not isinstance(options, dict):
        options = {}
    return {
        "width": options.get("image_width") or 180,
        "height": options.get("image_height") or 140,
        "keep_ratio": options.get("keep_ratio"),
    }


def _stack_image_options(options):
    if not isinstance(options, dict):
        options = {}
    return {
        "width": options.get("image_width") or 220,
        "height": options.get("image_height") or 120,
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


def _render_image_stack_row_step_legacy(sheet, block, image_data, target_cell, max_row):
    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    source_keys = _source_keys_from_options(options)
    if not source_keys:
        return {"written_cells": [], "skipped_keys": []}

    gap_rows = _positive_int(options.get("gap_rows"), 8)
    size_options = _stack_image_options(options)
    written_cells = []
    skipped_keys = []

    for index, key in enumerate(source_keys):
        try:
            cell = _offset_cell(target_cell, row_offset=gap_rows * index)
        except ValueError:
            skipped_keys.append(key)
            continue

        row_match = CELL_RANGE_RE.match(cell)
        if not row_match or int(row_match.group(2)) > max_row:
            skipped_keys.append(key)
            continue

        if not isinstance(image_data, dict):
            skipped_keys.append(key)
            continue

        item = image_data.get(key)
        if not isinstance(item, dict):
            skipped_keys.append(key)
            continue

        image_path = resolve_uploaded_image_path(item.get("image_path"))
        if not image_path:
            skipped_keys.append(key)
            continue

        if ExcelImage is None:
            raise RuntimeError("图片渲染需要安装 pillow。")

        try:
            img = ExcelImage(str(image_path))
        except ImportError as e:
            raise RuntimeError("图片渲染需要安装 pillow。") from e
        except Exception:
            skipped_keys.append(key)
            continue

        _apply_image_size(img, size_options)
        sheet.add_image(img, cell)
        written_cells.append(cell)

    return {"written_cells": written_cells, "skipped_keys": skipped_keys}


def _load_stack_image(image_data, key):
    if not isinstance(image_data, dict):
        return None

    item = image_data.get(key)
    if not isinstance(item, dict):
        return None

    image_path = resolve_uploaded_image_path(item.get("image_path"))
    if not image_path:
        return None

    if ExcelImage is None:
        raise RuntimeError("图片渲染需要安装 pillow。")

    try:
        return ExcelImage(str(image_path))
    except ImportError as e:
        raise RuntimeError("图片渲染需要安装 pillow。") from e
    except Exception:
        return None


def _render_image_stack_row_step(sheet, source_keys, image_data, target_cell, max_row, size_options, gap_rows):
    written_cells = []
    skipped_keys = []

    for index, key in enumerate(source_keys):
        try:
            cell = _offset_cell(target_cell, row_offset=gap_rows * index)
        except ValueError:
            skipped_keys.append(key)
            continue

        row_match = CELL_RANGE_RE.match(cell)
        if max_row and (not row_match or int(row_match.group(2)) > max_row):
            skipped_keys.append(key)
            continue

        img = _load_stack_image(image_data, key)
        if img is None:
            skipped_keys.append(key)
            continue

        _apply_image_size(img, size_options)
        sheet.add_image(img, cell)
        written_cells.append(cell)

    return {"written_cells": written_cells, "skipped_keys": skipped_keys}


def _render_image_stack_auto(sheet, source_keys, image_data, anchor_cell, size_options, gap_px, region_height_px):
    written_cells = []
    skipped_keys = []
    current_y = 0

    for key in source_keys:
        if region_height_px is not None and current_y > region_height_px:
            skipped_keys.append(key)
            continue

        img = _load_stack_image(image_data, key)
        if img is None:
            skipped_keys.append(key)
            continue

        _apply_image_size(img, size_options)
        add_image_with_offset(sheet, img, anchor_cell, offset_y_px=current_y)
        written_cells.append(anchor_cell)
        current_y += _non_negative_number(getattr(img, "height", 0), 0) + gap_px

    return {"written_cells": written_cells, "skipped_keys": skipped_keys}


def _render_image_stack_block(sheet, block, image_data, target_cell, max_row=None, region_range=None):
    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    source_keys = _source_keys_from_options(options)
    if not source_keys:
        return {"written_cells": [], "skipped_keys": []}

    layout_mode = str(options.get("layout_mode") or "row_step").strip().lower()
    if layout_mode == "auto_stack":
        anchor_text = str(options.get("anchor_cell") or "").strip()
        anchor_cell = _left_top_cell(anchor_text) if anchor_text else target_cell
        if not anchor_cell:
            return {"written_cells": [], "skipped_keys": source_keys}

        return _render_image_stack_auto(
            sheet,
            source_keys,
            image_data,
            anchor_cell,
            _stack_image_options(options),
            _non_negative_number(options.get("gap_px"), 12),
            estimate_region_height_px(sheet, region_range),
        )

    if not target_cell:
        return {"written_cells": [], "skipped_keys": source_keys}

    return _render_image_stack_row_step(
        sheet,
        source_keys,
        image_data,
        target_cell,
        max_row,
        _stack_image_options(options),
        _positive_int(options.get("gap_rows"), 8),
    )


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
            elif block_type == "image_stack":
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
                "skipped_images": [],
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
                "skipped_images": [],
            }

        regions_count = 0
        blocks_count = 0
        written_cells = []
        written_images = []
        skipped_images = []

        for region in layout_config.get("regions", []):
            if not isinstance(region, dict):
                return {"success": False, "error": "layout region 格式异常"}
            if region.get("enabled") is False:
                continue

            sheet_name = str(region.get("sheet") or "active").strip().lower()
            if sheet_name != "active":
                continue

            range_text = str(region.get("range") or "").strip()
            target_cell = ""
            max_row = None
            if range_text:
                try:
                    target_cell = _left_top_cell(range_text)
                    _, max_row = _range_row_bounds(range_text)
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
                    if not target_cell:
                        continue
                    block_text = _render_block(block, description_fields=description_fields)
                    if not block_text:
                        continue

                    blocks_count += 1
                    region_parts.append(block_text)
                    continue

                if block_type == "image":
                    if not target_cell:
                        continue
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
                    if not target_cell:
                        continue
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

                if block_type == "image_stack":
                    try:
                        stack_result = _render_image_stack_block(
                            workbook.active,
                            block,
                            image_data,
                            target_cell,
                            max_row,
                            range_text,
                        )
                    except RuntimeError as e:
                        return {"success": False, "error": str(e)}

                    stack_cells = stack_result.get("written_cells") or []
                    skipped_images.extend(stack_result.get("skipped_keys") or [])
                    if not stack_cells:
                        continue

                    blocks_count += 1
                    region_written = True
                    written_images.extend(stack_cells)
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
            "skipped_images": skipped_images,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
