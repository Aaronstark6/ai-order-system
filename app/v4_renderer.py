from app.logger import get_logger


logger = get_logger(__name__)


def _is_dict(value):
    return isinstance(value, dict)


def _get_dict(source, key):
    value = source.get(key) if _is_dict(source) else None
    return value if _is_dict(value) else {}


def _is_empty(value):
    return value is None or value == ""


def _display_value(value):
    if isinstance(value, bool):
        return "是" if value else "否"
    return str(value)


def _field_label(fields_schema, field_key):
    field_schema = fields_schema.get(field_key) if _is_dict(fields_schema) else None
    if _is_dict(field_schema):
        return field_schema.get("label") or field_key
    return field_key


def _render_labeled_lines(values, fields_schema):
    if not _is_dict(values):
        return ""

    lines = []
    field_keys = list(fields_schema.keys()) if _is_dict(fields_schema) else list(values.keys())
    for field_key in field_keys:
        if field_key not in values:
            continue

        value = values.get(field_key)
        if _is_empty(value):
            continue

        lines.append(f"{_field_label(fields_schema, field_key)}：{_display_value(value)}")

    return "\n".join(lines)


def _render_formula_requirements(requirements):
    if not isinstance(requirements, list):
        return ""

    lines = []
    for item in requirements:
        if not _is_dict(item):
            continue

        name_en = str(item.get("name_en") or "").strip()
        name_cn = str(item.get("name_cn") or "").strip()
        amount = str(item.get("amount") or "").strip()
        percentage = str(item.get("percentage") or "").strip()

        name = ""
        if name_en and name_cn:
            name = f"{name_en}（{name_cn}）"
        elif name_en:
            name = name_en
        elif name_cn:
            name = name_cn

        details = [part for part in [amount, percentage] if part]
        if name and details:
            lines.append(f"{name}：{'，'.join(details)}")
        elif name:
            lines.append(name)
        elif details:
            lines.append("，".join(details))

    return "\n".join(lines)


def render_example_to_description_fields(example_data: dict, schema: dict) -> dict:
    warnings = []
    description_fields = {
        "产品形式": "",
        "产品要求": "",
        "配方要求": "",
        "包装要求": "",
    }

    try:
        if not _is_dict(example_data):
            raise ValueError("example_data must be a dict")
        if not _is_dict(schema):
            raise ValueError("schema must be a dict")

        product = _get_dict(example_data, "product")
        form_key = product.get("form")
        product_forms = _get_dict(schema, "product_forms")
        form_schema = product_forms.get(form_key) if form_key else None

        if not form_key:
            warnings.append("product.form 不存在")
        elif not _is_dict(form_schema):
            warnings.append(f"product.form 不在 schema.product_forms 中：{form_key}")
        else:
            description_fields["产品形式"] = form_schema.get("label") or form_key
            product_values = product.get(form_key)
            if _is_dict(product_values):
                description_fields["产品要求"] = _render_labeled_lines(
                    product_values,
                    _get_dict(form_schema, "fields"),
                )

        formula = _get_dict(example_data, "formula")
        requirements = formula.get("requirements")
        if not requirements:
            warnings.append("formula.requirements 为空")
        description_fields["配方要求"] = _render_formula_requirements(requirements)

        packaging = _get_dict(example_data, "packaging")
        if not packaging:
            warnings.append("packaging 为空")
        description_fields["包装要求"] = _render_labeled_lines(
            packaging,
            _get_dict(_get_dict(schema, "packaging"), "fields"),
        )

        logger.info("V4 renderer prototype finished: warnings=%s", len(warnings))
        return {
            "success": True,
            "description_fields": description_fields,
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception("V4 renderer prototype failed")
        return {
            "success": False,
            "error": str(exc),
            "description_fields": {},
            "warnings": warnings,
        }
