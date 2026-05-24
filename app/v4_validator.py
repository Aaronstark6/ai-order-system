from app.logger import get_logger


logger = get_logger(__name__)


def _is_dict(value):
    return isinstance(value, dict)


def _get_nested_dict(data, key):
    value = data.get(key) if _is_dict(data) else None
    return value if _is_dict(value) else {}


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


def validate_order_object(order_object):
    errors = []
    warnings = []

    if not _is_dict(order_object) or not order_object:
        errors.append("Order Object 必须存在")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
        }

    customer = _get_nested_dict(order_object, "customer")
    product = _get_nested_dict(order_object, "product")

    if not customer:
        errors.append("缺少 customer")
    if not product:
        errors.append("缺少 product")

    if not str(product.get("product_type") or "").strip():
        warnings.append("缺少 product.product_type")

    if not str(product.get("product_name") or "").strip():
        warnings.append("product.product_name 为空")

    if "fields" not in product or not _is_dict(product.get("fields")):
        warnings.append("product.fields 不存在或不是 object")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }
