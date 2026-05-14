import re
from copy import copy

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


def render_layout(workbook, data, profile, description_fields=None, description_text=None, image_data=None):
    try:
        if workbook is None:
            return {"success": False, "error": "workbook 不能为空"}
        if not isinstance(profile, dict):
            return {"success": False, "error": "profile 格式异常"}

        raw_config = profile.get("layout_config")
        if raw_config is None:
            return {"success": True, "skipped": True, "regions_count": 0, "blocks_count": 0, "written_cells": []}
        if not isinstance(raw_config, dict):
            return {"success": False, "error": "layout_config 格式异常"}

        layout_config = normalize_layout_config(raw_config)
        if layout_config.get("enabled") is not True:
            return {"success": True, "skipped": True, "regions_count": 0, "blocks_count": 0, "written_cells": []}

        regions_count = 0
        blocks_count = 0
        written_cells = []

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
            for block in blocks:
                if not isinstance(block, dict):
                    return {"success": False, "error": "layout block 格式异常"}
                if block.get("enabled") is not True:
                    continue

                block_text = _render_block(block, description_fields=description_fields)
                if not block_text:
                    continue

                blocks_count += 1
                region_parts.append(block_text)

            if not region_parts:
                continue

            regions_count += 1
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
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
