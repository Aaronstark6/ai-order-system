from openpyxl.utils.cell import coordinate_from_string, get_column_letter
from openpyxl.utils import column_index_from_string


STRUCTURED_LABELS = {
    "产品名称": "product.product_name",
    "产品类型": "product.product_type",
    "客户名称": "customer.name",
    "国家地区": "customer.country",
    "包装规格": "product.fields.包装规格",
    "甜味剂": "product.fields.甜味剂",
    "口味": "product.fields.口味",
}


def _clean_label(value):
    return str(value or "").strip().rstrip(":：")


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
