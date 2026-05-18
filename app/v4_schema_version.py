CURRENT_SCHEMA_VERSION = "v4.1"
SUPPORTED_SCHEMA_VERSIONS = {CURRENT_SCHEMA_VERSION}


def get_current_schema_version():
    return CURRENT_SCHEMA_VERSION


def _extract_order_object_version(order_object):
    if not isinstance(order_object, dict):
        return None
    version = str(order_object.get("schema_version") or "").strip()
    return version or None


def _extract_pipeline_state_version(pipeline_state):
    if not isinstance(pipeline_state, dict):
        return None
    schema = pipeline_state.get("schema")
    if not isinstance(schema, dict):
        return None
    version = str(schema.get("current_version") or "").strip()
    return version or None


def _extract_mapping_versions(mappings):
    if not mappings:
        return []
    mapping_items = mappings if isinstance(mappings, list) else [mappings]
    versions = []
    for item in mapping_items:
        if not isinstance(item, dict):
            continue
        version = str(item.get("schema_version") or "").strip()
        if version:
            versions.append(version)
    return versions


def validate_schema_version(order_object=None, mappings=None, pipeline_state=None):
    order_object_version = _extract_order_object_version(order_object)
    pipeline_state_version = _extract_pipeline_state_version(pipeline_state)
    mapping_versions = _extract_mapping_versions(mappings)
    checked_versions = [
        version
        for version in [order_object_version, pipeline_state_version, *mapping_versions]
        if version
    ]
    unsupported_versions = sorted(
        {version for version in checked_versions if version not in SUPPORTED_SCHEMA_VERSIONS}
    )

    if unsupported_versions:
        return {
            "current_version": CURRENT_SCHEMA_VERSION,
            "order_object_version": order_object_version,
            "pipeline_state_version": pipeline_state_version,
            "mapping_versions": mapping_versions,
            "compatible": False,
            "status": "error",
            "message": f"不支持的 Schema Version：{', '.join(unsupported_versions)}",
        }

    if not order_object_version:
        return {
            "current_version": CURRENT_SCHEMA_VERSION,
            "order_object_version": None,
            "pipeline_state_version": pipeline_state_version,
            "mapping_versions": mapping_versions,
            "compatible": True,
            "status": "warning",
            "message": "Order Object 缺少 schema_version，按当前版本兼容处理。",
        }

    return {
        "current_version": CURRENT_SCHEMA_VERSION,
        "order_object_version": order_object_version,
        "pipeline_state_version": pipeline_state_version,
        "mapping_versions": mapping_versions,
        "compatible": True,
        "status": "ok",
        "message": "Schema Version 兼容。",
    }
