"""V4 template matcher foundation."""

from app.v4_ai_template_parser import parse_template_to_rules
from app.v4_template_cache import (
    TEMPLATE_CACHE_PARSER_VERSION,
    TEMPLATE_CACHE_SOURCE,
    has_cached_rules,
    load_meta,
    load_rules,
    save_fingerprint,
    save_meta,
    save_rules,
)
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


def match_or_parse_template(excel_path):
    fingerprint = build_template_fingerprint(excel_path)
    layout_hash = fingerprint.get("layout_hash")

    if has_cached_rules(layout_hash):
        cached_rules = load_rules(layout_hash)
        return {
            "cache_hit": True,
            "layout_hash": layout_hash,
            "fingerprint": fingerprint,
            "rules": cached_rules,
            "warnings": [],
            "source": "cache",
            "meta": load_meta(layout_hash),
        }

    parser_result = parse_template_to_rules(excel_path)
    if not parser_result.get("success"):
        return {
            "cache_hit": False,
            "layout_hash": layout_hash,
            "fingerprint": fingerprint,
            "rules": [],
            "warnings": parser_result.get("warnings", []),
            "source": TEMPLATE_CACHE_SOURCE,
            "success": False,
            "error": parser_result.get("error", "AI 模板解析失败"),
            "raw_result": parser_result.get("raw_result"),
        }

    rules = parser_result.get("rules", [])
    if not isinstance(rules, list):
        rules = []

    save_fingerprint(fingerprint)
    save_rules(layout_hash, rules)
    meta = save_meta(
        layout_hash,
        {
            "source": TEMPLATE_CACHE_SOURCE,
            "rules_count": len(rules),
            "parser_version": TEMPLATE_CACHE_PARSER_VERSION,
        },
    )

    return {
        "cache_hit": False,
        "layout_hash": layout_hash,
        "fingerprint": fingerprint,
        "rules": rules,
        "warnings": parser_result.get("warnings", []),
        "source": TEMPLATE_CACHE_SOURCE,
        "meta": meta,
        "raw_result": parser_result.get("raw_result"),
    }
