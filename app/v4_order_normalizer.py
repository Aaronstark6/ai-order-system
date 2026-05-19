from copy import deepcopy


SCHEMA_VERSION = "v4.1"


CUSTOMER_NAME_KEYS = (
    "customer_name",
    "客户名称",
    "客户名",
    "customer",
    "client_name",
    "client",
)

CUSTOMER_TYPE_KEYS = (
    "customer_type",
    "客户性质",
    "客户类型",
    "client_type",
)

CUSTOMER_COUNTRY_KEYS = (
    "customer_country",
    "客户国家",
    "国家",
    "country",
)

ORDER_QUANTITY_KEYS = (
    "quantity",
    "order_quantity",
    "订单数量",
    "数量",
)

ORDER_DATE_KEYS = (
    "order_date",
    "deal_date",
    "date",
    "订单日期",
    "成交日期",
    "日期",
)

ORDER_NO_KEYS = (
    "order_no",
    "document_no",
    "订单号",
    "文档编号",
)

PRODUCT_TYPE_KEYS = (
    "product_type",
    "product_form",
    "产品类型",
    "产品形式",
    "剂型",
)

PRODUCT_NAME_KEYS = (
    "product_name",
    "产品名称",
    "品名",
)


RESERVED_KEYS = set(
    CUSTOMER_NAME_KEYS
    + CUSTOMER_TYPE_KEYS
    + CUSTOMER_COUNTRY_KEYS
    + ORDER_QUANTITY_KEYS
    + ORDER_DATE_KEYS
    + ORDER_NO_KEYS
    + PRODUCT_TYPE_KEYS
    + PRODUCT_NAME_KEYS
)


def _clean_text(value):
    if value is None:
        return ""
    return str(value).strip()


def _first_value(data, keys):
    if not isinstance(data, dict):
        return ""
    for key in keys:
        if key in data:
            value = _clean_text(data.get(key))
            if value:
                return value
    return ""


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict)):
        return len(value) == 0
    return False


def _field_label(key):
    return str(key or "").strip()


def _build_product_fields(flat_data):
    fields = {}
    if not isinstance(flat_data, dict):
        return fields

    for key, value in flat_data.items():
        key_text = str(key or "").strip()
        if not key_text:
            continue
        if key_text in RESERVED_KEYS:
            continue
        if _is_empty(value):
            continue
        if isinstance(value, (dict, list)):
            continue

        fields[key_text] = {
            "label": _field_label(key_text),
            "value": value,
        }

    return fields


def normalize_flat_order_to_v4_order_object(flat_data):
    flat_data = deepcopy(flat_data) if isinstance(flat_data, dict) else {}

    customer_name = _first_value(flat_data, CUSTOMER_NAME_KEYS)
    customer_type = _first_value(flat_data, CUSTOMER_TYPE_KEYS)
    customer_country = _first_value(flat_data, CUSTOMER_COUNTRY_KEYS)

    quantity = _first_value(flat_data, ORDER_QUANTITY_KEYS)
    order_date = _first_value(flat_data, ORDER_DATE_KEYS)
    order_no = _first_value(flat_data, ORDER_NO_KEYS)

    product_type = _first_value(flat_data, PRODUCT_TYPE_KEYS)
    product_name = _first_value(flat_data, PRODUCT_NAME_KEYS)

    order_object = {
        "schema_version": SCHEMA_VERSION,
        "customer": {
            "name": customer_name,
            "country": customer_country,
            "type": customer_type,
        },
        "order": {
            "order_no": order_no,
            "quantity": quantity,
            "order_date": order_date,
        },
        "product": {
            "product_type": product_type,
            "product_name": product_name,
            "fields": _build_product_fields(flat_data),
            "tables": {},
        },
    }

    warnings = []
    if not customer_name:
        warnings.append("未识别 customer.name")
    if not product_type:
        warnings.append("未识别 product.product_type")
    if not quantity:
        warnings.append("未识别 order.quantity")

    return {
        "success": True,
        "order_object": order_object,
        "warnings": warnings,
        "source_keys": list(flat_data.keys()),
    }
