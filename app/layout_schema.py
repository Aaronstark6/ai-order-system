from copy import deepcopy


DEFAULT_LAYOUT_CONFIG = {
    "enabled": False,
    "regions": [],
}

DEFAULT_LAYOUT_REGION = {
    "id": "",
    "name": "",
    "type": "",
    "enabled": True,
    "sheet": "active",
    "range": "",
    "blocks": [],
    "options": {},
}

DEFAULT_LAYOUT_BLOCK = {
    "id": "",
    "type": "",
    "source": "",
    "enabled": True,
    "options": {},
}


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        text = value.strip().lower()
        if text in {"true", "1", "yes", "on"}:
            return True
        if text in {"false", "0", "no", "off", ""}:
            return False
    return bool(value)


def default_layout_config():
    return deepcopy(DEFAULT_LAYOUT_CONFIG)


def normalize_layout_block(block):
    if not isinstance(block, dict):
        block = {}

    return {
        "id": str(block.get("id") or "").strip(),
        "type": str(block.get("type") or "").strip(),
        "source": str(block.get("source") or "").strip(),
        "enabled": _to_bool(block.get("enabled"), default=True),
        "options": block.get("options") if isinstance(block.get("options"), dict) else {},
    }


def normalize_layout_region(region):
    if not isinstance(region, dict):
        region = {}

    raw_blocks = region.get("blocks")
    blocks = raw_blocks if isinstance(raw_blocks, list) else []

    return {
        "id": str(region.get("id") or "").strip(),
        "name": str(region.get("name") or "").strip(),
        "type": str(region.get("type") or "").strip(),
        "enabled": _to_bool(region.get("enabled"), default=True),
        "sheet": str(region.get("sheet") or "active").strip() or "active",
        "range": str(region.get("range") or "").strip().upper(),
        "blocks": [normalize_layout_block(block) for block in blocks],
        "options": region.get("options") if isinstance(region.get("options"), dict) else {},
    }


def normalize_layout_config(raw):
    if not isinstance(raw, dict):
        raw = {}

    raw_regions = raw.get("regions")
    regions = raw_regions if isinstance(raw_regions, list) else []

    return {
        "enabled": _to_bool(raw.get("enabled"), default=False),
        "regions": [normalize_layout_region(region) for region in regions],
    }
