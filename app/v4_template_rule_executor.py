from pathlib import Path

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils.cell import coordinate_from_string

from app.excel_writer import safe_write_cell
from app.logger import get_logger


logger = get_logger(__name__)


def _is_empty(value):
    return value is None or value == ""


def _style_written_cell(ws, cell_ref, value):
    try:
        cell = ws[cell_ref]
        cell.alignment = Alignment(wrap_text=True, vertical="top")

        column_letter, row = coordinate_from_string(cell_ref)
        text_value = str(value or "")
        current_width = ws.column_dimensions[column_letter].width or 0
        if len(text_value) > 40:
            ws.column_dimensions[column_letter].width = max(current_width, 48)

        if "\n" in text_value or len(text_value) > 60:
            line_count = max(1, text_value.count("\n") + 1)
            ws.row_dimensions[row].height = max(ws.row_dimensions[row].height or 0, min(120, 24 * line_count))
    except Exception:
        logger.debug("V4 template rule executor cell style skipped: cell_ref=%s", cell_ref)


def execute_rules_to_template_excel(
    template_path: str,
    operations: list,
    output_path: str,
) -> dict:
    warnings = []
    operations_written = 0

    try:
        if _is_empty(template_path):
            raise ValueError("template_path must not be empty")
        if not isinstance(operations, list):
            raise ValueError("operations must be a list")
        if _is_empty(output_path):
            raise ValueError("output_path must not be empty")

        template_file = Path(template_path)
        if not template_file.is_file():
            raise FileNotFoundError(f"template file not found: {template_path}")

        logger.info(
            "V4 template rule executor started: template_path=%s output_path=%s",
            template_path,
            output_path,
        )

        wb = load_workbook(template_file)
        ws = wb.active

        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                warnings.append(f"operation[{index}] 不是 object，已跳过")
                continue

            rule_id = operation.get("rule_id") or f"operation[{index}]"
            target_cell = operation.get("target_cell")
            value = operation.get("value")

            if _is_empty(target_cell):
                warnings.append(f"规则 {rule_id} 无 target_cell，已跳过")
                continue
            if _is_empty(value):
                warnings.append(f"规则 {rule_id} 无 value，已跳过")
                continue

            try:
                written_cell = safe_write_cell(ws, target_cell, value)
            except Exception as exc:
                warnings.append(f"规则 {rule_id} 写入 {target_cell} 失败：{exc}")
                continue

            if not written_cell:
                warnings.append(f"规则 {rule_id} 写入 cell 为空，已跳过")
                continue

            _style_written_cell(ws, written_cell, value)
            operations_written += 1

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        wb.save(output_file)

        logger.info(
            "V4 template rule executor succeeded: output_path=%s operations_written=%s warnings=%s",
            output_file,
            operations_written,
            len(warnings),
        )
        return {
            "success": True,
            "output_path": str(output_file),
            "operations_written": operations_written,
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception(
            "V4 template rule executor failed: template_path=%s output_path=%s",
            template_path,
            output_path,
        )
        return {
            "success": False,
            "error": str(exc),
            "operations_written": 0,
            "warnings": warnings,
        }
