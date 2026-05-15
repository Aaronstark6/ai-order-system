"""Shared helpers for writing text values into Excel worksheets."""

from openpyxl.cell.cell import MergedCell
from openpyxl.utils.cell import coordinate_to_tuple

from app.logger import get_logger


logger = get_logger(__name__)


def normalize_cell_ref(cell_ref):
    text = str(cell_ref or "").strip().upper()
    if not text:
        return ""

    try:
        coordinate_to_tuple(text)
    except Exception:
        return ""
    return text


def resolve_merged_cell_anchor(ws, cell_ref):
    for merged_range in ws.merged_cells.ranges:
        if cell_ref in merged_range:
            return merged_range.start_cell.coordinate
    return cell_ref


def safe_write_cell(ws, cell_ref, value):
    cell = normalize_cell_ref(cell_ref)
    if not cell:
        logger.warning("Skip cell write: invalid cell_ref=%s", cell_ref)
        return None

    try:
        cell_obj = ws[cell]
        target_cell = resolve_merged_cell_anchor(ws, cell)
        if isinstance(cell_obj, MergedCell) or target_cell != cell:
            logger.debug("[Excel] Merged cell redirect: %s -> %s", cell, target_cell)
        ws[target_cell].value = value
        return target_cell
    except Exception as e:
        logger.exception("Cell write failed: cell_ref=%s", cell_ref)
        raise ValueError(f"单元格 {cell_ref} 写入失败：{e}") from e
