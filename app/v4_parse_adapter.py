RESERVED_PARSE_KEYS = {
    "fields",
    "missing_fields",
    "raw",
    "error",
    "success",
    "metadata",
    "diagnostics",
}


def _is_simple_value(value):
    return value is None or isinstance(value, (str, int, float, bool))


def _clean_key(key):
    return str(key or "").strip()


def _set_if_valid(flat_data, key, value):
    cleaned_key = _clean_key(key)
    if cleaned_key:
        flat_data[cleaned_key] = value


def normalize_parse_result_to_flat_data(parse_result):
    flat_data = {}
    if not isinstance(parse_result, dict):
        return flat_data

    fields = parse_result.get("fields")
    if isinstance(fields, dict):
        for key, value in fields.items():
            _set_if_valid(flat_data, key, value)
    elif isinstance(fields, list):
        for item in fields:
            if not isinstance(item, dict):
                continue
            field_key = item.get("field_key") or item.get("key") or item.get("name")
            _set_if_valid(flat_data, field_key, item.get("value"))

    for key, value in parse_result.items():
        cleaned_key = _clean_key(key)
        if cleaned_key in RESERVED_PARSE_KEYS:
            continue
        if _is_simple_value(value):
            _set_if_valid(flat_data, cleaned_key, value)

    return flat_data
