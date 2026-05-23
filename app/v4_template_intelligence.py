from openpyxl.utils.cell import coordinate_from_string, get_column_letter
from openpyxl.utils import column_index_from_string


STRUCTURED_LABELS = {
    "产品名称": "product.product_name",
    "品名": "product.product_name",
    "产品": "product.product_name",
    "产品类型": "product.product_type",
    "客户名称": "customer.name",
    "客户": "customer.name",
    "客户公司": "customer.name",
    "公司名称": "customer.name",
    "国家地区": "customer.country",
    "国家": "customer.country",
    "出口国家": "customer.country",
    "目的国": "customer.country",
    "联系人": "customer.contact_person",
    "联系人姓名": "customer.contact_person",
    "数量": "order.quantity",
    "订购数量": "order.quantity",
    "采购数量": "order.quantity",
    "规格": "product.spec",
    "产品规格": "product.spec",
    "净含量": "product.spec",
    "包装": "product.packaging",
    "包装方式": "product.packaging",
    "单价": "order.unit_price",
    "价格": "order.unit_price",
    "交期": "order.delivery_time",
    "交货期": "order.delivery_time",
    "Logo": "document.logo",
    "LOGO": "document.logo",
    "图片": "document.image",
    "产品图片": "product.image",
    "包装规格": "product.fields.包装规格",
    "甜味剂": "product.fields.甜味剂",
    "口味": "product.fields.口味",
}


def _clean_label(value):
    text = str(value or "").strip()
    while text and (text.endswith(":") or text.endswith("：")):
        text = text.rstrip(":：").rstrip()
    return text


def _infer_target_cell(label_cell):
    try:
        col_letter, row_number = coordinate_from_string(str(label_cell or "").strip())
        col_index = column_index_from_string(col_letter)
    except Exception:
        return ""

    if col_index == 1:
        return f"{get_column_letter(col_index + 1)}{row_number}"
    return f"{col_letter}{row_number + 1}"


def infer_structured_mapping_from_labels(labels):
    mappings = []
    seen = set()
    labels = labels if isinstance(labels, list) else []
    for item in labels:
        if not isinstance(item, dict):
            continue
        label = _clean_label(item.get("value"))
        source_path = STRUCTURED_LABELS.get(label)
        if not source_path:
            continue

        key = (item.get("sheet", ""), label, item.get("cell", ""))
        if key in seen:
            continue
        seen.add(key)
        mappings.append(
            {
                "sheet": item.get("sheet", ""),
                "label": label,
                "source_path": source_path,
                "target_cell": _infer_target_cell(item.get("cell")),
                "operation": "write_text",
                "reason": "Template Intelligence 根据标签自动推断",
            }
        )
    return mappings
