from app.logger import get_logger


logger = get_logger(__name__)


def _is_dict(value):
    return isinstance(value, dict)


def _get_nested_dict(data, key):
    value = data.get(key) if _is_dict(data) else None
    return value if _is_dict(value) else {}


def _is_blank(value):
    return value is None or str(value).strip() == ""


def _field_matches(field_key, field_name, values):
    return field_key in values or field_name in values


def _field_value(field_key, field_name, values):
    if field_key in values:
        return values.get(field_key)
    if field_name in values:
        return values.get(field_name)
    return None


def _normalize_compare_value(value):
    return str(value or "").strip().lower()


def _get_order_product_type(order_object):
    product = _get_nested_dict(order_object, "product")
    return str(product.get("product_type") or "").strip()


def _find_product_type(product_type_key, product_types):
    for product_type in product_types:
        if not _is_dict(product_type):
            continue
        key = str(product_type.get("key") or "").strip()
        name = str(product_type.get("name") or "").strip()
        if product_type_key and product_type_key in {key, name}:
            return product_type
    return {}


def _product_type_field_maps(product_type):
    fields = product_type.get("fields", []) if _is_dict(product_type) else []
    field_by_identifier = {}
    required_fields = []
    unique_fields = []

    if not isinstance(fields, list):
        return field_by_identifier, required_fields

    for field in fields:
        if not _is_dict(field):
            continue

        field_key = str(field.get("key") or "").strip()
        field_name = str(field.get("name") or field_key).strip()
        if field_key:
            field_by_identifier[field_key] = field
        if field_name:
            field_by_identifier[field_name] = field
        if field.get("required"):
            required_fields.append(field)
        unique_fields.append(field)

    return field_by_identifier, required_fields, unique_fields


def _field_rule_values(field, key):
    values = field.get(key, []) if _is_dict(field) else []
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _validate_field_value_rules(field, field_value, errors):
    field_key = str(field.get("key") or "").strip()
    field_name = str(field.get("name") or field_key).strip()
    normalized_value = _normalize_compare_value(field_value)
    if not normalized_value:
        return

    forbidden_values = _field_rule_values(field, "forbidden_values")
    normalized_forbidden = {_normalize_compare_value(value) for value in forbidden_values}
    if normalized_value in normalized_forbidden:
        errors.append({
            "field": field_name or field_key,
            "field_key": field_key,
            "message": f"{field_name or field_key}不能填写“{str(field_value).strip()}”。",
        })
        return

    allowed_values = _field_rule_values(field, "allowed_values")
    normalized_allowed = {_normalize_compare_value(value) for value in allowed_values}
    if normalized_allowed and normalized_value not in normalized_allowed:
        errors.append({
            "field": field_name or field_key,
            "field_key": field_key,
            "message": f"{field_name or field_key}的值“{str(field_value).strip()}”不在允许范围内。",
        })


def validate_order_object(order_object: dict) -> dict:
    from app.v4_schema import get_product_types

    errors = []
    warnings = []

    logger.info("[Validator] Execution started")

    if not _is_dict(order_object):
        logger.info("[Validator] Loaded Order Object: invalid payload")
        logger.info("[Validator] Product Type = ")
        logger.info("[Validator] Errors = 1")
        logger.info("[Validator] Warnings = 0")
        return {
            "valid": False,
            "errors": [
                {
                    "field": "order_object",
                    "message": "Order Object 必须是对象",
                }
            ],
            "warnings": [],
        }

    product = _get_nested_dict(order_object, "product")
    product_fields = product.get("fields", {})
    if not _is_dict(product_fields):
        errors.append({
            "field": "product.fields",
            "message": "产品字段必须是对象",
        })
        product_fields = {}

    product_type_key = _get_order_product_type(order_object)
    logger.info("[Validator] Loaded Order Object")
    logger.info("[Validator] Product Type = %s", product_type_key)

    product_types = get_product_types()
    product_type = _find_product_type(product_type_key, product_types)

    if not product_type_key:
        errors.append({
            "field": "product.product_type",
            "message": "产品类型不能为空",
        })
    elif not product_type:
        errors.append({
            "field": "product.product_type",
            "message": f"产品类型不存在：{product_type_key}",
        })

    if product_type:
        field_by_identifier, required_fields, unique_fields = _product_type_field_maps(product_type)
        fields_with_required_errors = set()

        for field in required_fields:
            field_key = str(field.get("key") or "").strip()
            field_name = str(field.get("name") or field_key).strip()
            if not _field_matches(field_key, field_name, product_fields) or _is_blank(
                _field_value(field_key, field_name, product_fields)
            ):
                fields_with_required_errors.add(field_key or field_name)
                errors.append({
                    "field": field_name or field_key,
                    "field_key": field_key,
                    "message": f"{field_name or field_key}不能为空",
                })

        for field in unique_fields:
            field_key = str(field.get("key") or "").strip()
            field_name = str(field.get("name") or field_key).strip()
            if (field_key or field_name) in fields_with_required_errors:
                continue
            if _field_matches(field_key, field_name, product_fields):
                _validate_field_value_rules(
                    field,
                    _field_value(field_key, field_name, product_fields),
                    errors,
                )

        for field_key in product_fields:
            if field_key not in field_by_identifier:
                warnings.append({
                    "field": field_key,
                    "message": f"未知产品字段：{field_key}",
                })

    result = {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
    logger.info(
        "V4 order object validation finished: valid=%s errors=%s warnings=%s",
        result["valid"],
        len(errors),
        len(warnings),
    )
    logger.info("[Validator] Errors = %s", len(errors))
    logger.info("[Validator] Warnings = %s", len(warnings))
    return result


def _validate_required_product_context(example_data, schema, errors):
    product = _get_nested_dict(example_data, "product")
    product_form = product.get("form")

    if not product_form:
        errors.append("缺少 product.form")
        return product, "", {}

    product_forms = _get_nested_dict(schema, "product_forms")
    form_schema = product_forms.get(product_form)
    if not _is_dict(form_schema):
        errors.append(f"未知产品形式：{product_form}")
        return product, product_form, {}

    return product, product_form, form_schema


def _warn_missing_fields(source, field_schema, message_builder, warnings):
    fields = _get_nested_dict(field_schema, "fields")
    if not fields:
        return

    source = source if _is_dict(source) else {}
    for field_key in fields:
        if field_key not in source:
            warnings.append(message_builder(field_key))


def validate_example_order(example_data: dict, schema: dict) -> dict:
    errors = []
    warnings = []

    if not _is_dict(example_data):
        errors.append("示例订单必须是 dict")
    if not _is_dict(schema):
        errors.append("Product Schema 必须是 dict")

    if errors:
        logger.error("V4 example validation failed: errors=%s", errors)
        return {
            "success": False,
            "errors": errors,
            "warnings": warnings,
        }

    product, product_form, form_schema = _validate_required_product_context(
        example_data,
        schema,
        errors,
    )

    if errors:
        logger.error("V4 example validation failed: errors=%s", errors)
        return {
            "success": False,
            "errors": errors,
            "warnings": warnings,
        }

    product_values = product.get(product_form)
    if not _is_dict(product_values):
        errors.append(f"缺少产品结构：product.{product_form}")
        logger.error("V4 example validation failed: errors=%s", errors)
        return {
            "success": False,
            "errors": errors,
            "warnings": warnings,
        }

    _warn_missing_fields(
        product_values,
        form_schema,
        lambda field_key: f"缺少产品字段：{product_form}.{field_key}",
        warnings,
    )
    _warn_missing_fields(
        _get_nested_dict(example_data, "packaging"),
        _get_nested_dict(schema, "packaging"),
        lambda field_key: f"缺少包装字段：{field_key}",
        warnings,
    )
    _warn_missing_fields(
        _get_nested_dict(example_data, "images"),
        _get_nested_dict(schema, "images"),
        lambda field_key: f"缺少图片字段：{field_key}",
        warnings,
    )

    result = {
        "success": True,
        "errors": [],
        "warnings": warnings,
    }
    logger.info("V4 example validation finished: warnings=%s", len(warnings))
    return result
