from pathlib import Path

# ============================================================
# 1. 修改 app/v4_excel_executor.py
# ============================================================
executor_path = Path("app/v4_excel_executor.py")
executor = executor_path.read_text(encoding="utf-8")

# 1.1 在 _cell_has_template_value 后面新增 _cell_has_formula 和 _formula_protection_skip
old = '''def _cell_has_template_value(cell):
    return cell.value is not None and str(cell.value).strip() != ""'''


new = '''def _cell_has_template_value(cell):
    return cell.value is not None and str(cell.value).strip() != ""


def _cell_has_formula(cell):
    value = cell.value
    return isinstance(value, str) and value.strip().startswith("=")


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
    return skipped, reason'''

if new not in executor:
    if old not in executor:
        raise SystemExit("找不到 _cell_has_template_value")
    executor = executor.replace(old, new, 1)
    print("1.1 Added _cell_has_formula / _formula_protection_skip")

# 1.2 修改 _empty_safety 签名
old = '''def _empty_safety(warnings=None, skipped_operations=None, overwrite_warnings=None):
    return {
        "has_conflicts": False,
        "conflicts": [],
        "warnings": warnings if isinstance(warnings, list) else [],
        "skipped_operations": skipped_operations if isinstance(skipped_operations, list) else [],
        "overwrite_warnings": overwrite_warnings if isinstance(overwrite_warnings, list) else [],
    }'''

new = '''def _empty_safety(warnings=None, skipped_operations=None, overwrite_warnings=None, formula_protection=None):
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
    }'''

if new not in executor:
    if old not in executor:
        raise SystemExit("找不到 _empty_safety")
    executor = executor.replace(old, new, 1)
    print("1.2 Updated _empty_safety")

# 1.3 在 overwrite_warnings = [] 下面新增 formula 保护变量
old = '''    overwrite_warnings = []

    if not template_path.is_file():'''
new = '''    overwrite_warnings = []
    formula_protected_operations = []
    formula_protected_cells = []

    if not template_path.is_file():'''
if new not in executor:
    if old not in executor:
        raise SystemExit("找不到 overwrite_warnings 变量声明")
    executor = executor.replace(old, new, 1)
    print("1.3 Added formula protection variables")

# 1.4 替换写入单元格的核心逻辑，增加公式保护
old = '''            write_cell = _resolve_merged_target(worksheet, target_cell, warnings)
            cell = worksheet[write_cell]
            if _cell_has_template_value(cell) and not _is_mapping_confirmed(operation):
                warning = f"{write_cell} 目标单元格已有模板内容，可能发生覆盖。"
                warnings.append(warning)
                overwrite_warnings.append(
                    {
                        "target_cell": write_cell,
                        "requested_cell": target_cell,
                        "source": str(operation.get("source") or operation.get("type") or ""),
                        "op_type": op_type,
                        "warning": warning,
                    }
                )
            cell.value = _operation_value(operation)'''

new = '''            write_cell = _resolve_merged_target(worksheet, target_cell, warnings)
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
                        "target_cell": write_cell,
                        "requested_cell": target_cell,
                        "source": str(operation.get("source") or operation.get("type") or ""),
                        "op_type": op_type,
                        "warning": warning,
                    }
                )
            cell.value = _operation_value(operation)'''

if new not in executor:
    if old not in executor:
        raise SystemExit("找不到 cell write 核心逻辑")
    executor = executor.replace(old, new, 1)
    print("1.4 Added formula protection in write logic")

# 1.5 在 return 前插入 formula_protection 变量
old = '''    return {
        "success": True,
        "filename": filename,
        "output_path": str(output_path),
        "download_url": f"/api/download/{filename}",
        "operations_written": operations_written,
        "warnings": warnings,
        "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings),
    }'''

new = '''    formula_protection = {
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
    }'''

if new not in executor:
    if old not in executor:
        raise SystemExit("找不到 execute_operations_to_excel return")
    executor = executor.replace(old, new, 1)
    print("1.5 Updated return with formula_protection")

# 1.6 替换前两个 _empty_safety 调用（模板不存在 / 暂无 operations）
old = '''            "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings),
            "operations_written": 0,
        }

    if not isinstance(operations, list) or not operations:
        warnings.append("暂无 operations。")
        return {
            "success": False,
            "error": "暂无 operations",
            "warnings": warnings,
            "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings),
            "operations_written": 0,
        }'''

new = '''            "mapping_safety": _empty_safety(warnings, skipped_operations, overwrite_warnings, {}),
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
        }'''

if new not in executor:
    if old not in executor:
        raise SystemExit("找不到前两个 _empty_safety 调用")
    executor = executor.replace(old, new, 1)
    print("1.6 Updated early _empty_safety calls")

executor_path.write_text(executor, encoding="utf-8")
print("app/v4_excel_executor.py done")


# ============================================================
# 2. 修改 app/routes/v4.py - 增加 formula_protection flag
# ============================================================
routes_path = Path("app/routes/v4.py")
routes = routes_path.read_text(encoding="utf-8")

old = '''DEFAULT_EXCEL_FEATURE_FLAGS = {
    "image_fields": False,
    "dynamic_tables": False,
    "advanced_write_modes": False,
    "option_write_enhancement": False,
    "format_protection": True,
    "export_readback_check": True,
}'''

new = '''DEFAULT_EXCEL_FEATURE_FLAGS = {
    "image_fields": False,
    "dynamic_tables": False,
    "advanced_write_modes": False,
    "option_write_enhancement": False,
    "format_protection": True,
    "formula_protection": True,
    "export_readback_check": True,
}'''

if new not in routes:
    if old not in routes:
        raise SystemExit("找不到 DEFAULT_EXCEL_FEATURE_FLAGS")
    routes = routes.replace(old, new, 1)
    print("2.1 Added formula_protection to DEFAULT_EXCEL_FEATURE_FLAGS")

routes_path.write_text(routes, encoding="utf-8")
print("app/routes/v4.py done")

print("V4-EXCEL-FIX92 patch applied")
