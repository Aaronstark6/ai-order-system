from app.excel_writer import normalize_cell_ref
from app.logger import get_logger


logger = get_logger(__name__)

ALLOWED_RULE_TYPES = {"checkbox", "text"}


def _is_dict(value):
    return isinstance(value, dict)


def _is_blank(value):
    return value is None or str(value).strip() == ""


def _path(prefix, *parts):
    return ".".join([prefix, *[str(part) for part in parts]])


def _validate_target(rule_id, rule_path, rule, errors, warnings):
    target = rule.get("target") if _is_dict(rule) else None
    if not _is_dict(target):
        errors.append(f"{rule_path}.target 必须是 object")
        return

    cell = target.get("cell")
    if _is_blank(cell):
        errors.append(f"{rule_path}.target.cell 不能为空")
    elif not normalize_cell_ref(cell):
        errors.append(f"{rule_path}.target.cell 格式不正确：{cell}")

    if _is_blank(target.get("sheet")):
        warnings.append(f"规则 {rule_id or rule_path} 未设置 sheet，将默认使用 active。")


def _validate_checkbox_rule(rule_path, rule, errors):
    condition = rule.get("condition") if _is_dict(rule) else None
    if not _is_dict(condition):
        errors.append(f"{rule_path}.condition 必须是 object")
    else:
        if _is_blank(condition.get("path")):
            errors.append(f"{rule_path}.condition.path 不能为空")
        if _is_blank(condition.get("equals")):
            errors.append(f"{rule_path}.condition.equals 不能为空")

    if _is_blank(rule.get("checked_text")):
        errors.append(f"{rule_path}.checked_text 不能为空")
    if _is_blank(rule.get("unchecked_text")):
        errors.append(f"{rule_path}.unchecked_text 不能为空")


def _validate_text_rule(rule_path, rule, errors):
    source = rule.get("source") if _is_dict(rule) else None
    if not _is_dict(source):
        errors.append(f"{rule_path}.source 必须是 object")
    elif _is_blank(source.get("description_field")):
        errors.append(f"{rule_path}.source.description_field 不能为空")


def _validate_rule(template_key, index, rule, seen_ids, errors, warnings):
    rule_path = f"templates.{template_key}.rules[{index}]"
    if not _is_dict(rule):
        errors.append(f"{rule_path} 必须是 object")
        return

    rule_id = rule.get("id")
    rule_type = rule.get("type")

    if _is_blank(rule_id):
        errors.append(f"{rule_path}.id 不能为空")
    elif rule_id in seen_ids:
        errors.append(f"模板 {template_key} 中规则 id 重复：{rule_id}")
    else:
        seen_ids.add(rule_id)

    if _is_blank(rule_type):
        errors.append(f"{rule_path}.type 不能为空")
    elif rule_type not in ALLOWED_RULE_TYPES:
        errors.append(f"{rule_path}.type 只能是 checkbox 或 text")

    _validate_target(rule_id, rule_path, rule, errors, warnings)

    if rule_type == "checkbox":
        _validate_checkbox_rule(rule_path, rule, errors)
    elif rule_type == "text":
        _validate_text_rule(rule_path, rule, errors)


def validate_excel_render_rules(rules_config: dict) -> dict:
    errors = []
    warnings = []

    try:
        if not _is_dict(rules_config):
            errors.append("Excel 渲染规则配置必须是 object")
            return {
                "success": False,
                "errors": errors,
                "warnings": warnings,
            }

        if _is_blank(rules_config.get("version")):
            errors.append("version 不能为空")

        templates = rules_config.get("templates")
        if not _is_dict(templates):
            errors.append("templates 必须是 object")
            templates = {}
        elif not templates:
            warnings.append("暂无 Excel 渲染规则模板。")

        for template_key, template in templates.items():
            template_path = _path("templates", template_key)
            if not _is_dict(template):
                errors.append(f"{template_path} 必须是 object")
                continue

            if _is_blank(template.get("label")):
                errors.append(f"{template_path}.label 不能为空")

            if "rules" not in template:
                errors.append(f"{template_path}.rules 不能为空")
                continue

            rules = template.get("rules")
            if not isinstance(rules, list):
                errors.append(f"{template_path}.rules 必须是 list")
                continue

            seen_ids = set()
            for index, rule in enumerate(rules):
                _validate_rule(template_key, index, rule, seen_ids, errors, warnings)

        logger.info(
            "V4 Excel render rules validation finished: errors=%s warnings=%s",
            len(errors),
            len(warnings),
        )
        return {
            "success": not errors,
            "errors": errors,
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception("V4 Excel render rules validation failed")
        return {
            "success": False,
            "errors": [f"Excel 渲染规则校验失败：{exc}"],
            "warnings": warnings,
        }
