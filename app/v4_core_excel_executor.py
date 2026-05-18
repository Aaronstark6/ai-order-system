from copy import copy
from datetime import datetime
from pathlib import Path
import re

from openpyxl import load_workbook

from app.runtime_paths import get_base_dir


def _safe_filename_part(value):
    text = str(value or "").strip()
    text = re.sub(r"[^\w.-]+", "_", text, flags=re.UNICODE)
    return text.strip("._") or "template"


def _set_wrap_text(cell):
    alignment = copy(cell.alignment)
    alignment.wrap_text = True
    alignment.vertical = alignment.vertical or "top"
    cell.alignment = alignment


def _resolve_merged_target(ws, cell_ref, warnings):
    for merged_range in ws.merged_cells.ranges:
        if cell_ref in merged_range:
            start_cell = merged_range.start_cell.coordinate
            if start_cell != cell_ref:
                warnings.append(f"{cell_ref} 位于合并单元格内，已写入左上角 {start_cell}。")
            return start_cell
    return cell_ref


def execute_processed_operations_to_excel(template_file, processed_operations):
    template_path = Path(template_file)
    warnings = []

    if not template_path.is_file():
        return {
            "success": False,
            "error": "Excel 模板不存在",
            "warnings": warnings,
            "operations_written": 0,
        }

    if not isinstance(processed_operations, list) or not processed_operations:
        return {
            "success": False,
            "error": "暂无 processed operations",
            "warnings": warnings,
            "operations_written": 0,
        }

    wb = load_workbook(template_path)
    ws = wb.active
    operations_written = 0

    for index, operation in enumerate(processed_operations, start=1):
        if not isinstance(operation, dict):
            warnings.append(f"第 {index} 条 operation 无效，已跳过。")
            continue

        target_cell = str(operation.get("target_cell") or "").strip()
        if not target_cell:
            warnings.append(f"第 {index} 条 operation 缺少 target_cell，已跳过。")
            continue

        try:
            write_cell = _resolve_merged_target(ws, target_cell, warnings)
            cell = ws[write_cell]
            cell.value = "" if operation.get("value") is None else str(operation.get("value"))
            _set_wrap_text(cell)
            operations_written += 1
        except Exception as exc:
            warnings.append(f"{target_cell} 写入失败：{exc}")

    output_dir = get_base_dir() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    template_name = _safe_filename_part(template_path.stem)
    filename = f"v4_core_{template_name}_{timestamp}.xlsx"
    output_path = output_dir / filename
    wb.save(output_path)

    return {
        "success": True,
        "filename": filename,
        "output_path": str(output_path),
        "download_url": f"/api/download/{filename}",
        "operations_written": operations_written,
        "warnings": warnings,
    }
