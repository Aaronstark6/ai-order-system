from pathlib import Path

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.utils.exceptions import InvalidFileException

from app.logger import get_logger


logger = get_logger(__name__)


def _normalize_labels(labels):
    if not isinstance(labels, list):
        return []

    normalized = []
    seen = set()
    for label in labels:
        text = str(label or "").strip()
        if text and text not in seen:
            normalized.append(text)
            seen.add(text)
    return normalized


def _resolve_merged_cell(ws, cell_ref):
    for merged_range in ws.merged_cells.ranges:
        if cell_ref in merged_range:
            return merged_range.start_cell.coordinate
    return cell_ref


def _right_cell_ref(cell):
    return f"{get_column_letter(cell.column + 1)}{cell.row}"


def scan_labels_in_excel(template_path, labels):
    warnings = []
    label_list = _normalize_labels(labels)
    if not label_list:
        return {
            "success": False,
            "matches": [],
            "unmatched_labels": [],
            "warnings": ["没有可扫描的字段标签"],
        }

    template = Path(template_path) if template_path else None
    if not template or not template.is_file():
        return {
            "success": False,
            "matches": [],
            "unmatched_labels": label_list,
            "warnings": ["请先上传 Excel 模板"],
        }

    try:
        wb = load_workbook(template, data_only=True)
    except (InvalidFileException, OSError, ValueError) as exc:
        logger.exception("[LabelLocator] Template scan failed: path=%s", template)
        return {
            "success": False,
            "matches": [],
            "unmatched_labels": label_list,
            "warnings": [str(exc) or "模板扫描失败"],
        }

    label_set = set(label_list)
    matches_by_label = {}
    duplicate_count = {}

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if cell.value is None:
                    continue

                value = str(cell.value).strip()
                if value not in label_set:
                    continue

                target_cell = _resolve_merged_cell(ws, _right_cell_ref(cell))
                match = {
                    "label": value,
                    "sheet": ws.title,
                    "label_cell": cell.coordinate,
                    "target_cell": target_cell,
                    "value": value,
                }
                if value not in matches_by_label:
                    matches_by_label[value] = match
                else:
                    duplicate_count[value] = duplicate_count.get(value, 1) + 1

    for label, count in duplicate_count.items():
        if count > 1:
            warnings.append(f"标签“{label}”命中多个位置，已使用第一个")

    matches = [matches_by_label[label] for label in label_list if label in matches_by_label]
    unmatched_labels = [label for label in label_list if label not in matches_by_label]

    logger.info(
        "[LabelLocator] Template labels scanned: labels=%s matches=%s unmatched=%s warnings=%s",
        len(label_list),
        len(matches),
        len(unmatched_labels),
        len(warnings),
    )
    return {
        "success": True,
        "matches": matches,
        "unmatched_labels": unmatched_labels,
        "warnings": warnings,
    }
