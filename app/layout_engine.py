"""Render layout_config blocks into Excel worksheets."""

import re
from copy import copy
from datetime import datetime

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

try:
    from openpyxl.drawing.image import Image as ExcelImage
except ImportError:
    ExcelImage = None
from openpyxl.utils import column_index_from_string, get_column_letter

from app.excel_writer import safe_write_cell
from app.image_manager import ensure_layout_cache_dir, resolve_uploaded_image_path
from app.logger import get_logger
from app.layout_schema import normalize_layout_config


CELL_RANGE_RE = re.compile(r"^\$?([A-Z]{1,3})\$?(\d+)(?::\$?([A-Z]{1,3})\$?(\d+))?$")
logger = get_logger(__name__)


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


def create_vertical_stack_image(image_paths, image_width, image_height, keep_ratio=True, gap_px=12):
    if PILImage is None:
        raise RuntimeError("图片渲染需要安装 pillow。")

    paths = [path for path in image_paths if path]
    if not paths:
        return {"path": None, "image_count": 0, "skipped_paths": [], "skipped_indexes": []}

    max_width = _to_positive_number(image_width)
    max_height = _to_positive_number(image_height)
    gap = int(round(_non_negative_number(gap_px, 12)))
    keep_ratio = _to_bool(keep_ratio, default=True)
    resampling = getattr(getattr(PILImage, "Resampling", PILImage), "LANCZOS")
    resized_images = []
    skipped_paths = []
    skipped_indexes = []

    for index, image_path in enumerate(paths):
        try:
            with PILImage.open(image_path) as source:
                original_width, original_height = source.size
                if original_width <= 0 or original_height <= 0:
                    raise ValueError("invalid image size")
                target_width = max_width or original_width
                target_height = max_height or original_height

                if keep_ratio:
                    scale = min(target_width / original_width, target_height / original_height)
                    width = max(1, int(round(original_width * scale)))
                    height = max(1, int(round(original_height * scale)))
                else:
                    width = max(1, int(round(target_width)))
                    height = max(1, int(round(target_height)))

                resized_images.append(source.convert("RGBA").resize((width, height), resampling))
        except Exception:
            skipped_paths.append(str(image_path))
            skipped_indexes.append(index)

    if not resized_images:
        return {
            "path": None,
            "image_count": 0,
            "skipped_paths": skipped_paths,
            "skipped_indexes": skipped_indexes,
        }

    stack_width = max(image.width for image in resized_images)
    stack_height = sum(image.height for image in resized_images) + gap * (len(resized_images) - 1)
    composite = PILImage.new("RGB", (stack_width, stack_height), "white")

    current_y = 0
    for image in resized_images:
        if image.mode == "RGBA":
            composite.paste(image, (0, current_y), image)
        else:
            composite.paste(image, (0, current_y))
        current_y += image.height + gap

    cache_dir = ensure_layout_cache_dir()
    composite_path = cache_dir / f"stack_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.png"
    composite.save(composite_path)
    return {
        "path": composite_path,
        "image_count": len(resized_images),
        "skipped_paths": skipped_paths,
        "skipped_indexes": skipped_indexes,
    }


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


def _keys_from_option_value(value):
    if isinstance(value, list):
        values = value
    elif isinstance(value, str):
        values = value.split(",")
    else:
        values = []

    keys = []
    seen = set()
    for item in values:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def _max_images_from_options(options):
    number = _to_positive_number(options.get("max_images") if isinstance(options, dict) else None)
    if not number:
        return 0
    return max(0, int(round(number)))


def _use_image_pool(options):
    return _to_bool(options.get("use_image_pool") if isinstance(options, dict) else None, default=False)


def _normalize_image_pool_items(image_pool):
    if not isinstance(image_pool, list):
        return []

    items = []
    seen = set()
    for index, item in enumerate(image_pool):
        if not isinstance(item, dict):
            continue

        image_path = item.get("image_path")
        key = str(item.get("key") or "").strip()
        filename = str(item.get("filename") or "").strip()
        if not key:
            key = Path(filename).stem if filename else f"pool_{index}"
        if not key:
            key = f"pool_{index}"
        if key in seen:
            key = f"{key}_{index}"
        seen.add(key)

        items.append({
            "key": key,
            "image_path": image_path,
            "label": item.get("label") or filename or key,
            "filename": filename,
        })
    return items


def _image_pool_to_image_data(image_pool):
    pool_data = {}
    for item in _normalize_image_pool_items(image_pool):
        pool_data[item["key"]] = item
    return pool_data


def get_block_image_keys(block, image_data, image_pool=None):
    if not isinstance(block, dict):
        return []

    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    exclude_keys = set(_keys_from_option_value(options.get("exclude_keys")))
    max_images = _max_images_from_options(options)

    if _use_image_pool(options):
        keys = []
        for item in _normalize_image_pool_items(image_pool):
            image_path = resolve_uploaded_image_path(item.get("image_path"))
            if not image_path:
                continue
            keys.append(item["key"])
            if max_images and len(keys) >= max_images:
                break
        return keys

    if _to_bool(options.get("auto_source"), default=False):
        keys = []
        if isinstance(image_data, dict):
            for key, item in image_data.items():
                key_text = str(key or "").strip()
                if not key_text or key_text in exclude_keys:
                    continue
                if not isinstance(item, dict):
                    continue
                if not resolve_uploaded_image_path(item.get("image_path")):
                    continue
                keys.append(key_text)
                if max_images and len(keys) >= max_images:
                    break
        return keys

    keys = [key for key in _source_keys_from_options(options) if key not in exclude_keys]
    if max_images:
        keys = keys[:max_images]
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


def _render_image_gallery_block(sheet, block, image_data, target_cell, image_pool=None):
    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    if _use_image_pool(options):
        image_data = _image_pool_to_image_data(image_pool)

    if not isinstance(image_data, dict):
        return []

    source_keys = get_block_image_keys(block, image_data, image_pool=image_pool)
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


def _resolve_stack_image_path(image_data, key):
    if not isinstance(image_data, dict):
        return None

    item = image_data.get(key)
    if not isinstance(item, dict):
        return None

    return resolve_uploaded_image_path(item.get("image_path"))


def _is_readable_stack_image(image_path):
    if PILImage is None:
        return True

    try:
        with PILImage.open(image_path) as source:
            source.verify()
        return True
    except Exception:
        return False


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

    return {
        "written_cells": written_cells,
        "skipped_keys": skipped_keys,
        "written_images_detail": [],
    }


def _render_image_stack_auto(sheet, source_keys, image_data, anchor_cell, size_options, gap_px):
    skipped_keys = []
    valid_paths = []
    valid_keys = []

    for key in source_keys:
        image_path = _resolve_stack_image_path(image_data, key)
        if not image_path or not _is_readable_stack_image(image_path):
            skipped_keys.append(key)
            continue
        valid_paths.append(image_path)
        valid_keys.append(key)

    if not valid_paths:
        return {
            "written_cells": [],
            "skipped_keys": skipped_keys,
            "written_images_detail": [],
        }

    if ExcelImage is None:
        raise RuntimeError("图片渲染需要安装 pillow。")

    composite_result = create_vertical_stack_image(
        valid_paths,
        size_options.get("width"),
        size_options.get("height"),
        _to_bool(size_options.get("keep_ratio"), default=True),
        gap_px,
    )
    composite_path = composite_result.get("path") if isinstance(composite_result, dict) else composite_result
    skipped_indexes = composite_result.get("skipped_indexes", []) if isinstance(composite_result, dict) else []
    skipped_index_set = {index for index in skipped_indexes if isinstance(index, int)}
    composite_skipped_keys = [
        key for index, key in enumerate(valid_keys)
        if index in skipped_index_set
    ]
    if composite_skipped_keys:
        skipped_keys.extend(composite_skipped_keys)

    if not composite_path:
        return {
            "written_cells": [],
            "skipped_keys": skipped_keys,
            "written_images_detail": [],
        }

    written_keys = [
        key for index, key in enumerate(valid_keys)
        if index not in skipped_index_set
    ]

    try:
        composite_img = ExcelImage(str(composite_path))
    except ImportError as e:
        raise RuntimeError("图片渲染需要安装 pillow。") from e

    except Exception:
        return {
            "written_cells": [],
            "skipped_keys": skipped_keys + written_keys,
            "written_images_detail": [],
        }

    sheet.add_image(composite_img, anchor_cell)

    return {
        "written_cells": [anchor_cell],
        "skipped_keys": skipped_keys,
        "written_images_detail": [
            {
                "type": "composite_stack",
                "cell": anchor_cell,
                "source_keys": written_keys,
                "image_count": len(written_keys),
                "skipped_count": len(skipped_keys),
                "composite_path": str(composite_path),
            }
        ],
    }


def _render_image_stack_block(sheet, block, image_data, target_cell, max_row=None, image_pool=None):
    options = block.get("options") if isinstance(block.get("options"), dict) else {}
    if _use_image_pool(options):
        image_data = _image_pool_to_image_data(image_pool)

    source_keys = get_block_image_keys(block, image_data, image_pool=image_pool)
    if not source_keys:
        return {"written_cells": [], "skipped_keys": [], "written_images_detail": []}

    layout_mode = str(options.get("layout_mode") or "row_step").strip().lower()
    if layout_mode == "auto_stack":
        anchor_text = str(options.get("anchor_cell") or "").strip()
        anchor_cell = _left_top_cell(anchor_text) if anchor_text else target_cell
        if not anchor_cell:
            return {"written_cells": [], "skipped_keys": source_keys, "written_images_detail": []}

        return _render_image_stack_auto(
            sheet,
            source_keys,
            image_data,
            anchor_cell,
            _stack_image_options(options),
            _non_negative_number(options.get("gap_px"), 12),
        )

    if not target_cell:
        return {"written_cells": [], "skipped_keys": source_keys, "written_images_detail": []}

    return _render_image_stack_row_step(
        sheet,
        source_keys,
        image_data,
        target_cell,
        max_row,
        _stack_image_options(options),
        _positive_int(options.get("gap_rows"), 8),
    )


def collect_layout_image_keys(profile, image_data=None):
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
                if _to_bool(options.get("auto_source"), default=False):
                    if isinstance(image_data, dict):
                        keys.update(get_block_image_keys(block, image_data))
                    else:
                        keys.add("*")
                else:
                    keys.update(get_block_image_keys(block, image_data))
            elif block_type == "image_stack":
                options = block.get("options") if isinstance(block.get("options"), dict) else {}
                if _to_bool(options.get("auto_source"), default=False):
                    if isinstance(image_data, dict):
                        keys.update(get_block_image_keys(block, image_data))
                    else:
                        keys.add("*")
                else:
                    keys.update(get_block_image_keys(block, image_data))
    return keys


def render_layout(workbook, data, profile, description_fields=None, description_text=None, image_data=None, image_pool=None):
    try:
        if workbook is None:
            logger.error("Layout render failed: workbook is empty")
            return {"success": False, "error": "workbook 不能为空"}
        if not isinstance(profile, dict):
            logger.error("Layout render failed: invalid profile")
            return {"success": False, "error": "profile 格式异常"}

        logger.info("Layout render started: profile_id=%s", profile.get("id") or "")
        raw_config = profile.get("layout_config")
        if raw_config is None:
            logger.info("Layout render skipped: no layout_config")
            return {
                "success": True,
                "skipped": True,
                "regions_count": 0,
                "blocks_count": 0,
                "written_cells": [],
                "written_images": [],
                "skipped_images": [],
                "written_images_detail": [],
            }
        if not isinstance(raw_config, dict):
            logger.error("Layout render failed: invalid layout_config")
            return {"success": False, "error": "layout_config 格式异常"}

        layout_config = normalize_layout_config(raw_config)
        if layout_config.get("enabled") is not True:
            logger.info("Layout render skipped: layout disabled")
            return {
                "success": True,
                "skipped": True,
                "regions_count": 0,
                "blocks_count": 0,
                "written_cells": [],
                "written_images": [],
                "skipped_images": [],
                "written_images_detail": [],
            }

        regions_count = 0
        blocks_count = 0
        written_cells = []
        written_images = []
        skipped_images = []
        written_images_detail = []

        for region in layout_config.get("regions", []):
            if not isinstance(region, dict):
                logger.error("Layout render failed: invalid region")
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
                    logger.exception("Layout render failed: invalid region range=%s", range_text)
                    return {
                        "success": False,
                        "error": f"layout region {region.get('id') or region.get('name') or ''} {str(e)}".strip(),
                    }

            blocks = region.get("blocks")
            if not isinstance(blocks, list):
                logger.error("Layout render failed: invalid blocks region_id=%s", region.get("id") or "")
                return {"success": False, "error": f"layout region {region.get('id') or ''} blocks 格式异常"}

            region_parts = []
            region_written = False
            for block in blocks:
                if not isinstance(block, dict):
                    logger.error("Layout render failed: invalid block")
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
                        logger.exception("Layout image block render failed")
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
                        gallery_cells = _render_image_gallery_block(
                            workbook.active,
                            block,
                            image_data,
                            target_cell,
                            image_pool=image_pool,
                        )
                    except RuntimeError as e:
                        logger.exception("Layout image gallery render failed")
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
                            image_pool=image_pool,
                        )
                    except RuntimeError as e:
                        logger.exception("Layout image stack render failed")
                        return {"success": False, "error": str(e)}

                    stack_cells = stack_result.get("written_cells") or []
                    skipped_images.extend(stack_result.get("skipped_keys") or [])
                    written_images_detail.extend(stack_result.get("written_images_detail") or [])
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
                written_cell = safe_write_cell(workbook.active, target_cell, "\n\n".join(region_parts))
                if not written_cell:
                    continue
                cell = workbook.active[written_cell]
                _set_wrap_text_only(cell)
                written_cells.append(written_cell)

        logger.info(
            "Layout render succeeded: regions=%s blocks=%s images=%s skipped_images=%s",
            regions_count,
            blocks_count,
            len(written_images),
            len(skipped_images),
        )
        return {
            "success": True,
            "skipped": False,
            "regions_count": regions_count,
            "blocks_count": blocks_count,
            "written_cells": written_cells,
            "written_images": written_images,
            "skipped_images": skipped_images,
            "written_images_detail": written_images_detail,
        }
    except Exception as e:
        logger.exception("Layout render failed")
        return {"success": False, "error": str(e)}
