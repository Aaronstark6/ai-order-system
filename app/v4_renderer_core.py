from app.logger import get_logger


logger = get_logger(__name__)


FORMULA_KEYWORDS = [
    "配方",
    "成分",
    "甜味剂",
    "香精",
    "颜色",
    "口味",
    "formula",
    "ingredient",
    "sweetener",
    "flavor",
    "color",
]

PACKAGING_KEYWORDS = [
    "包装",
    "规格",
    "瓶",
    "袋",
    "盒",
    "标签",
    "package",
    "spec",
    "bottle",
    "bag",
    "box",
    "label",
]


def _is_dict(value):
    return isinstance(value, dict)


def _is_blank(value):
    return value is None or str(value).strip() == ""


def _get_nested_dict(data, key):
    value = data.get(key) if _is_dict(data) else None
    return value if _is_dict(value) else {}


def _find_product_type(product_type_value, product_types):
    product_type_value = str(product_type_value or "").strip()
    if not product_type_value:
        return {}

    for product_type in product_types:
        if not _is_dict(product_type):
            continue
        key = str(product_type.get("key") or "").strip()
        name = str(product_type.get("name") or "").strip()
        if product_type_value in {key, name}:
            return product_type

    return {}


def _field_maps(product_type):
    fields = product_type.get("fields", []) if _is_dict(product_type) else []
    field_by_identifier = {}
    if not isinstance(fields, list):
        return field_by_identifier

    for field in fields:
        if not _is_dict(field):
            continue
        key = str(field.get("key") or "").strip()
        name = str(field.get("name") or key).strip()
        if key:
            field_by_identifier[key] = field
        if name:
            field_by_identifier[name] = field

    return field_by_identifier


def _has_keyword(text, keywords):
    text = str(text or "").lower()
    return any(keyword.lower() in text for keyword in keywords)


def _field_category(field_key, field_name):
    classify_text = f"{field_key} {field_name}"
    if _has_keyword(classify_text, FORMULA_KEYWORDS):
        return "formula_requirements"
    if _has_keyword(classify_text, PACKAGING_KEYWORDS):
        return "packaging_requirements"
    return "product_requirements"


def _append_line(groups, category, field_name, value):
    if _is_blank(value):
        return
    groups[category].append(f"{field_name}：{str(value).strip()}")


def _render_product_form(product_type, product_type_value, product_name):
    lines = []
    product_type_name = ""
    if _is_dict(product_type):
        product_type_name = str(product_type.get("name") or product_type.get("key") or "").strip()
    if not product_type_name:
        product_type_name = str(product_type_value or "").strip()

    if product_type_name:
        lines.append(f"产品类型：{product_type_name}")
    if not _is_blank(product_name):
        lines.append(f"产品名称：{str(product_name).strip()}")
    return "\n".join(lines)


def render_order_object(order_object):
    from app.v4_schema import get_product_types

    warnings = []
    groups = {
        "product_requirements": [],
        "formula_requirements": [],
        "packaging_requirements": [],
    }

    if not _is_dict(order_object):
        return {
            "success": False,
            "description_fields": {
                "product_form": "",
                "product_requirements": "",
                "formula_requirements": "",
                "packaging_requirements": "",
            },
            "warnings": ["Order Object 必须是对象"],
        }

    product = _get_nested_dict(order_object, "product")
    product_type_value = str(product.get("product_type") or "").strip()
    product_name = product.get("product_name", "")
    product_fields = product.get("fields", {})
    if not _is_dict(product_fields):
        product_fields = {}
        warnings.append("product.fields 不是对象，已按空字段处理")

    product_type = _find_product_type(product_type_value, get_product_types())
    if not product_type_value:
        warnings.append("产品类型为空")
    elif not product_type:
        warnings.append(f"产品类型未定义：{product_type_value}")

    field_by_identifier = _field_maps(product_type)
    for field_key, value in product_fields.items():
        if _is_blank(value):
            continue

        field = field_by_identifier.get(field_key)
        if _is_dict(field):
            resolved_key = str(field.get("key") or field_key).strip()
            field_name = str(field.get("name") or resolved_key).strip()
        else:
            resolved_key = str(field_key or "").strip()
            field_name = resolved_key
            warnings.append(f"未知产品字段：{resolved_key}")

        category = _field_category(resolved_key, field_name)
        _append_line(groups, category, field_name, value)

    description_fields = {
        "product_form": _render_product_form(product_type, product_type_value, product_name),
        "product_requirements": "\n".join(groups["product_requirements"]),
        "formula_requirements": "\n".join(groups["formula_requirements"]),
        "packaging_requirements": "\n".join(groups["packaging_requirements"]),
    }

    logger.info(
        "[RendererCore] Rendered Order Object: product_type=%s warnings=%s",
        product_type_value,
        len(warnings),
    )
    return {
        "success": True,
        "description_fields": description_fields,
        "warnings": warnings,
    }
