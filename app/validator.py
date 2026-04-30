def is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def validate_order(data: dict) -> dict:
    """
    A级：缺了不能下单
    B级：建议确认
    C级：可以后补或默认
    """

    missing_A = []
    missing_B = []
    missing_C = []
    risk_warnings = []

    basic = data.get("basic_info", {})
    product = data.get("product_info", {})
    packaging = data.get("packaging_info", {})
    compliance = data.get("compliance_info", {})

    # A级字段：必须确认
    A_fields = [
        ("客户名称", basic.get("customer_name")),
        ("数量", basic.get("quantity")),
        ("产品名称", product.get("product_name")),
        ("净含量", product.get("net_weight")),
        ("包装方式", packaging.get("packaging_type")),
        ("标签语言", compliance.get("label_language")),
        ("目标市场", compliance.get("target_market")),
    ]

    for field_name, value in A_fields:
        if is_empty(value):
            missing_A.append(field_name)

    # B级字段：建议确认
    B_fields = [
        ("口味", product.get("flavor")),
        ("每份用量", product.get("serving_size")),
        ("冲调比例", product.get("mixing_ratio")),
        ("单包规格", packaging.get("single_pack_spec")),
        ("每盒数量", packaging.get("box_qty")),
        ("每箱数量", packaging.get("carton_qty")),
        ("标签要求", packaging.get("label_requirement")),
    ]

    for field_name, value in B_fields:
        if is_empty(value):
            missing_B.append(field_name)

    # C级字段：可后补
    C_fields = [
        ("批号格式", data.get("production_info", {}).get("batch_format")),
        ("有效期", data.get("production_info", {}).get("expiry")),
        ("密封方式", data.get("production_info", {}).get("seal_type")),
    ]

    for field_name, value in C_fields:
        if is_empty(value):
            missing_C.append(field_name)

    if missing_A:
        risk_warnings.append("存在A级必填字段缺失，不建议生成正式生产订单。")

    if missing_B:
        risk_warnings.append("存在B级建议确认字段缺失，可能导致包装、标签或生产细节返工。")

    ai_risks = data.get("risk_warnings", [])
    if isinstance(ai_risks, list):
        risk_warnings.extend(ai_risks)

    data["validation"] = {
        "missing_A": missing_A,
        "missing_B": missing_B,
        "missing_C": missing_C,
        "can_produce": len(missing_A) == 0,
        "risk_warnings": risk_warnings
    }

    return data
