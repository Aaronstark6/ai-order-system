"""V4 template matcher foundation."""

from app.v4_template_cache import has_cached_rules, load_rules, save_fingerprint
from app.v4_template_fingerprint import build_template_fingerprint


def match_template(excel_path):
    fingerprint = build_template_fingerprint(excel_path)
    layout_hash = fingerprint.get("layout_hash")
    save_fingerprint(fingerprint)

    cache_hit = has_cached_rules(layout_hash)
    cached_rules = load_rules(layout_hash) if cache_hit else None

    return {
        "fingerprint": fingerprint,
        "cache_hit": cache_hit,
        "cached_rules": cached_rules,
        "layout_hash": layout_hash,
    }
