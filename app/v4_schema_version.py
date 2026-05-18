CURRENT_SCHEMA_VERSION = "v4.1"


def get_current_schema_version():
    return CURRENT_SCHEMA_VERSION


def get_order_object_schema_version(order_object):
    if not isinstance(order_object, dict):
        return None

    schema_version = order_object.get("schema_version")
    if schema_version is None:
        return None

    schema_version = str(schema_version).strip()
    return schema_version or None


def check_schema_compatibility(order_object):
    current_version = get_current_schema_version()
    order_object_version = get_order_object_schema_version(order_object)

    if order_object_version is None:
        return {
            "current_version": current_version,
            "order_object_version": None,
            "compatible": True,
            "level": "warning",
            "message": "Order Object 未声明 schema_version，已按当前版本兼容处理。",
        }

    if order_object_version == current_version:
        return {
            "current_version": current_version,
            "order_object_version": order_object_version,
            "compatible": True,
            "level": "ok",
            "message": "Schema Version 兼容。",
        }

    return {
        "current_version": current_version,
        "order_object_version": order_object_version,
        "compatible": False,
        "level": "error",
        "message": f"Schema Version 不兼容：当前支持 {current_version}，Order Object 声明为 {order_object_version}。",
    }
