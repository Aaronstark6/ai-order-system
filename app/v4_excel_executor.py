from copy import copy
from datetime import datetime
from pathlib import Path
import re

from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter
from openpyxl.drawing.image import Image as XLImage

from app.runtime_paths import get_base_dir


SUPPORTED_OP_TYPES = {"write_text", "write_number", "write_multiline", "write_table_cell", "write_block", "write_image"}


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


def _operation_value(operation):
    value = operation.get("value")
    return "" if value is None else value


def _is_empty_operation(operation):
    return str(_operation_value(operation)).strip() == ""


def _is_mapping_confirmed(operation):
    return bool(
        operation.get("mapping_confirmed")
        or operation.get("confirmed")
        or operation.get("user_confirmed")
        or operation.get("explicitly_confirmed")
    )


def _cell_has_template_value(cell):
    return cell.value is not None and str(cell.value).strip() != ""


def _cell_has_formula(cell):
    value = cell.value
    return isinstance(value, str) and value.strip().startswith("=")


def _offset_cell_ref(cell_ref, row_offset=0, col_offset=0):
    match = re.match(r"^([A-Za-z]+)([1-9][0-9]*)$", str(cell_ref or "").strip())
    if not match:
        return str(cell_ref or "").strip().upper()

    col_letters = match.group(1).upper()
    row = int(match.group(2))
    col = column_index_from_string(col_letters)

    try:
        row_delta = int(row_offset or 0)
    except (TypeError, ValueError):
        row_delta = 0

    try:
        col_delta = int(col_offset or 0)
    except (TypeError, ValueError):
        col_delta = 0

    target_row = max(1, row + row_delta)
    target_col = max(1, col + col_delta)
    return f"{get_column_letter(target_col)}{target_row}"


def _operation_target_cell(operation):
    base_cell = str(operation.get("target_cell") or "").strip().upper()
    if not base_cell:
        return ""
    return _offset_cell_ref(
        base_cell,
        row_offset=operation.get("row_offset"),
        col_offset=operation.get("col_offset"),
    )


def _operation_sheet_name(operation):
    if not isinstance(operation, dict):
        return ""
    return str(
        operation.get("target_sheet")
        or operation.get("sheet_name")
        or operation.get("worksheet")
        or operation.get("sheet")
        or ""
    ).strip()


def _resolve_operation_worksheet(workbook, operation, warnings):
    sheet_name = _operation_sheet_name(operation)
    if not sheet_name:
        return workbook.active

    if sheet_name in workbook.sheetnames:
        return workbook[sheet_name]

    warnings.append(f"指定 sheet 不存在：{sheet_name}，已使用默认 active sheet。")
    return workbook.active


def _formula_protection_skip(operation, requested_cell, write_cell, formula_value):
    reason = f"{write_cell} 目标单元格包含公式，已保护并跳过写入。"
    skipped = dict(operation)
    skipped["skipped"] = True
    skipped["safety_status"] = "skipped"
    skipped["skip_code"] = "formula_protected"
    skipped["skip_reason"] = reason
    skipped["requested_cell"] = requested_cell
    skipped["target_cell"] = write_cell
    skipped["existing_formula"] = str(formula_value or "")
    return skipped, reason


def _empty_safety(warnings=None, skipped_operations=None, overwrite_warnings=None, formula_protection=None):
    formula_protection = formula_protection if isinstance(formula_protection, dict) else {}
    return {
        "has_conflicts": False,
        "conflicts": [],
        "warnings": warnings if isinstance(warnings, list) else [],
        "skipped_operations": skipped_operations if isinstance(skipped_operations, list) else [],
        "overwrite_warnings": overwrite_warnings if isinstance(overwrite_warnings, list) else [],
        "formula_protection": {
            "enabled": True,
            "protected_count": int(formula_protection.get("protected_count") or 0),
            "protected_cells": formula_protection.get("protected_cells") if isinstance(formula_protection.get("protected_cells"), list) else [],
        },
    }


def execute_operations_to_excel(template_file, operations):
    template_path = Path(template_file)
    warnings = []
    skipped_operations = []
    overwrite_warnings = []
    formula_protected_operations = []
    formula_protected_cells = []

    if not template_path.is_file():
        warnings.append("Excel 模板不存在。")
        return {
            "success": False,
            "error": "Excel 模板不存在",
            "warnings": warnings,
            "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings, {}),
            "operations_written": 0,
        }

    if not isinstance(operations, list) or not operations:
        warnings.append("暂无 operations。")
        return {
            "success": False,
            "error": "暂无 operations",
            "warnings": warnings,
            "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings, {}),
            "operations_written": 0,
        }

    workbook = load_workbook(template_path)
    operations_written = 0

    for index, operation in enumerate(operations, start=1):
        if not isinstance(operation, dict):
            warnings.append(f"第 {index} 条 operation 无效，已跳过。")
            continue

        op_type = str(operation.get("op_type") or operation.get("operation") or "").strip()
        if op_type and op_type not in SUPPORTED_OP_TYPES:
            warnings.append(f"第 {index} 条 operation 类型 {op_type} 暂不支持，已跳过。")
            continue

        try:
            worksheet = _resolve_operation_worksheet(workbook, operation, warnings)
            
            if op_type == "write_image":
                image_path = operation.get("image_path")
                if not image_path:
                    warnings.append(f"第 {index} 条 operation 缺少 image_path，已跳过。")
                    continue
                
                image_file = Path(image_path)
                if not image_file.is_file():
                    raise ValueError(f"图片文件不存在：{image_path}")
                
                xl_image = XLImage(str(image_file))
                
                anchor_cell = operation.get("image_anchor_cell") or operation.get("target_cell")
                if not anchor_cell:
                    warnings.append(f"第 {index} 条 operation 缺少 image_anchor_cell 或 target_cell，已跳过。")
                    continue
                
                worksheet.add_image(xl_image, anchor_cell)
                
                operations_written += 1
            else:
                target_cell = _operation_target_cell(operation)
                if not target_cell:
                    warnings.append(f"第 {index} 条 operation 缺少 target_cell，已跳过。")
                    continue

                if _is_empty_operation(operation):
                    reason = f"{target_cell} value 为空，Excel 写入前已跳过。"
                    warnings.append(reason)
                    skipped = dict(operation)
                    skipped["skipped"] = True
                    skipped["safety_status"] = "skipped"
                    skipped["skip_code"] = "empty_value"
                    skipped["skip_reason"] = reason
                    skipped_operations.append(skipped)
                    continue

                write_cell = _resolve_merged_target(worksheet, target_cell, warnings)
                cell = worksheet[write_cell]

                if _cell_has_formula(cell):
                    skipped, reason = _formula_protection_skip(
                        operation,
                        requested_cell=target_cell,
                        write_cell=write_cell,
                        formula_value=cell.value,
                    )
                    warnings.append(reason)
                    skipped_operations.append(skipped)
                    formula_protected_operations.append(skipped)
                    formula_protected_cells.append(
                        {
                            "sheet_name": worksheet.title,
                            "target_cell": write_cell,
                            "requested_cell": target_cell,
                            "existing_formula": str(cell.value or ""),
                            "source": str(operation.get("source") or operation.get("type") or ""),
                            "op_type": op_type,
                        }
                    )
                    continue

                if _cell_has_template_value(cell) and not _is_mapping_confirmed(operation):
                    warning = f"{write_cell} 目标单元格已有模板内容，可能发生覆盖。"
                    warnings.append(warning)
                    overwrite_warnings.append(
                        {
                            "sheet_name": worksheet.title,
                            "target_cell": write_cell,
                            "requested_cell": target_cell,
                            "source": str(operation.get("source") or operation.get("type") or ""),
                            "op_type": op_type,
                            "warning": warning,
                        }
                    )
                cell.value = _operation_value(operation)
                if "\n" in str(cell.value or "") or op_type in {"write_multiline", "write_block"}:
                    _set_wrap_text(cell)
                operations_written += 1
        except Exception as exc:
            warnings.append(f"operation 执行失败：{exc}")

    output_dir = get_base_dir() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"v4_core_{_safe_filename_part(template_path.stem)}_{timestamp}.xlsx"
    output_path = output_dir / filename
    workbook.save(output_path)

    formula_protection = {
        "protected_count": len(formula_protected_operations),
        "protected_cells": formula_protected_cells,
    }

    return {
        "success": True,
        "filename": filename,
        "output_path": str(output_path),
        "download_url": f"/api/download/{filename}",
        "operations_written": operations_written,
        "warnings": warnings,
        "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings, formula_protection),
    }


def execute_processed_operations_to_excel(template_file, processed_operations):
    return execute_operations_to_excel(template_file, processed_operations)
