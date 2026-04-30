def build_order_schema(ai_data: dict) -> dict:
    """
    把 AI 返回的扁平 JSON，整理成系统内部统一结构。
    """

    return {
        "product_type": ai_data.get("product_type", "solid_drink"),

        "basic_info": {
            "customer_name": ai_data.get("customer_name", ""),
            "quantity": ai_data.get("quantity", ""),
            "salesperson": ai_data.get("salesperson", "")
        },

        "product_info": {
            "product_name": ai_data.get("product_name", ""),
            "flavor": ai_data.get("flavor", ""),
            "net_weight": ai_data.get("net_weight", ""),
            "serving_size": ai_data.get("serving_size", ""),
            "mixing_ratio": ai_data.get("mixing_ratio", "")
        },

        "packaging_info": {
            "packaging_type": ai_data.get("packaging_type", ""),
            "single_pack_spec": ai_data.get("single_pack_spec", ""),
            "box_qty": ai_data.get("box_qty", ""),
            "carton_qty": ai_data.get("carton_qty", ""),
            "label_requirement": ai_data.get("label_requirement", "")
        },

        "production_info": {
            "batch_format": ai_data.get("batch_format", ""),
            "expiry": ai_data.get("expiry", ""),
            "seal_type": ai_data.get("seal_type", "")
        },

        "compliance_info": {
            "target_market": ai_data.get("target_market", ""),
            "label_language": ai_data.get("label_language", "")
        },

        "validation": {
            "missing_A": [],
            "missing_B": [],
            "missing_C": [],
            "can_produce": False,
            "risk_warnings": []
        }
    }
