from openpyxl.utils.cell import coordinate_to_tuple

from app.logger import get_logger


logger = get_logger(__name__)


def _is_dict(value):
    return isinstance(value, dict)


def _is_empty(value):
    return value is None or value == ""


def _get_nested_value(data, path):
    if not path:
        return None, False

    current = data
    for part in str(path).split("."):
        if not _is_dict(current) or part not in current:
            return None, False
        current = current.get(part)

    return current, True


def _get_template_rules(rules_config, template_key):
    templates = rules_config.get("templates") if _is_dict(rules_config) else None
    if not _is_dict(templates):
        return None

    template = templates.get(template_key)
    return template if _is_dict(template) else None


def _target_cell(rule):
    target = rule.get("target") if _is_dict(rule) else None
    return target.get("cell") if _is_dict(target) else ""


def _is_valid_cell_ref(value):
    text = str(value or "").strip()
    if not text:
        return False

    try:
        row, column = coordinate_to_tuple(text)
    except Exception:
        return False

    return 1 <= row <= 1048576 and 1 <= column <= 16384


def _mark_operation_status(operation):
    reasons = []
    status = "ok"

    if not str(operation.get("rule_id") or "").strip():
        reasons.append("rule_id 缺失")
        status = "error"

    if not str(operation.get("type") or "").strip():
        reasons.append("type 缺失")
        status = "error"

    target_cell = str(operation.get("target_cell") or "").strip()
    if not target_cell:
        reasons.append("target_cell 缺失")
        status = "error"
    elif not _is_valid_cell_ref(target_cell):
        reasons.append(f"target_cell 无效：{target_cell}")
        status = "error"

    if _is_empty(operation.get("value")) and status != "error":
        reasons.append("value 为空")
        status = "warning"

    operation["status"] = status
    operation["status_reasons"] = reasons
    return operation


def _invalid_operation(rule, reason):
    operation = {
        "rule_id": rule.get("id") if _is_dict(rule) else "",
        "type": rule.get("type") if _is_dict(rule) else "",
        "target_cell": _target_cell(rule) if _is_dict(rule) else "",
        "value": "",
    }
    operation = _mark_operation_status(operation)
    operation["status"] = "error"
    operation["status_reasons"].append(reason)
    return operation


def _summarize_operations(operations):
    summary = {
        "total": len(operations),
        "ok": 0,
        "warning": 0,
        "error": 0,
    }

    for operation in operations:
        status = operation.get("status")
        if status not in summary:
            status = "ok"
        summary[status] += 1

    return summary


def _build_checkbox_operation(rule, example_data, warnings):
    rule_id = rule.get("id") or ""
    condition = rule.get("condition") if _is_dict(rule.get("condition")) else {}
    condition_path = condition.get("path")
    expected_value = condition.get("equals")
    actual_value, exists = _get_nested_value(example_data, condition_path)

    if not exists:
        warnings.append(f"规则 {rule_id} 的 condition.path 不存在：{condition_path}")

    checked_text = rule.get("checked_text", "")
    unchecked_text = rule.get("unchecked_text", "")
    value = checked_text if exists and actual_value == expected_value else unchecked_text

    return _mark_operation_status({
        "rule_id": rule_id,
        "type": "checkbox",
        "target_cell": _target_cell(rule),
        "value": value,
    })


def _build_text_operation(rule, description_fields, warnings):
    rule_id = rule.get("id") or ""
    source = rule.get("source") if _is_dict(rule.get("source")) else {}
    description_field = source.get("description_field")

    if not _is_dict(description_fields) or description_field not in description_fields:
        warnings.append(f"规则 {rule_id} 的 description_field 不存在：{description_field}")
        value = ""
    else:
        value = description_fields.get(description_field)

    return _mark_operation_status({
        "rule_id": rule_id,
        "type": "text",
        "target_cell": _target_cell(rule),
        "value": "" if value is None else value,
    })


def build_excel_rule_preview(
    example_data: dict,
    description_fields: dict,
    rules_config: dict,
    template_key: str,
) -> dict:
    warnings = []
    operations = []

    try:
        if not _is_dict(example_data):
            raise ValueError("example_data must be a dict")
        if not _is_dict(description_fields):
            raise ValueError("description_fields must be a dict")
        if not _is_dict(rules_config):
            raise ValueError("rules_config must be a dict")

        template = _get_template_rules(rules_config, template_key)
        if not template:
            warnings.append(f"template_key 不存在：{template_key}")
            return {
                "success": True,
                "template_key": template_key,
                "operations": operations,
                "warnings": warnings,
                "validation": _summarize_operations(operations),
            }

        rules = template.get("rules")
        if not isinstance(rules, list) or not rules:
            warnings.append(f"模板 {template_key} 的 rules 为空")
            return {
                "success": True,
                "template_key": template_key,
                "operations": operations,
                "warnings": warnings,
                "validation": _summarize_operations(operations),
            }

        for rule in rules:
            if not _is_dict(rule):
                warnings.append("发现非 object 规则，已跳过")
                continue

            rule_type = rule.get("type")
            if rule_type == "checkbox":
                operations.append(_build_checkbox_operation(rule, example_data, warnings))
            elif rule_type == "text":
                operations.append(_build_text_operation(rule, description_fields, warnings))
            else:
                warnings.append(f"不支持的规则类型：{rule_type}")
                operations.append(_invalid_operation(rule, f"不支持的规则类型：{rule_type}"))

        logger.info(
            "V4 Excel rule preview built: template_key=%s operations=%s warnings=%s",
            template_key,
            len(operations),
            len(warnings),
        )
        return {
            "success": True,
            "template_key": template_key,
            "operations": operations,
            "warnings": warnings,
            "validation": _summarize_operations(operations),
        }
    except Exception as exc:
        logger.exception("V4 Excel rule preview failed: template_key=%s", template_key)
        return {
            "success": False,
            "error": str(exc),
            "operations": [],
            "warnings": warnings,
            "validation": _summarize_operations([]),
        }
