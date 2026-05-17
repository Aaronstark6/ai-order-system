"""V4 template cache helpers."""

import json
import re
from datetime import datetime
from pathlib import Path

from app.runtime_paths import get_base_dir


LAYOUT_HASH_PATTERN = re.compile(r"^[a-f0-9]{64}$")
TEMPLATE_CACHE_SOURCE = "ai_template_parser"
TEMPLATE_CACHE_PARSER_VERSION = "V4.17"


def _now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_cache_dir():
    cache_dir = get_base_dir() / "data" / "v4_template_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_cache_path(layout_hash):
    hash_text = str(layout_hash or "").strip().lower()
    if not LAYOUT_HASH_PATTERN.fullmatch(hash_text):
        raise ValueError("layout_hash 不合法")
    return ensure_cache_dir() / hash_text


def _read_json(path, default=None):
    if not path.is_file():
        return default
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _touch_meta(layout_hash, values=None):
    cache_path = get_cache_path(layout_hash)
    meta_path = cache_path / "meta.json"
    existing_meta = _read_json(meta_path, {}) or {}
    now_text = _now_text()
    meta = {
        "layout_hash": str(layout_hash or "").strip().lower(),
        "created_at": existing_meta.get("created_at") or now_text,
        "updated_at": now_text,
        "source": existing_meta.get("source") or TEMPLATE_CACHE_SOURCE,
        "rules_count": existing_meta.get("rules_count") or 0,
        "parser_version": existing_meta.get("parser_version") or TEMPLATE_CACHE_PARSER_VERSION,
    }
    if isinstance(existing_meta, dict):
        meta.update(existing_meta)
    if isinstance(values, dict):
        meta.update(values)
    meta["updated_at"] = now_text
    _write_json(meta_path, meta)
    return meta


def has_cached_rules(layout_hash):
    rules_path = get_cache_path(layout_hash) / "rules.json"
    return rules_path.is_file()


def save_fingerprint(fingerprint):
    if not isinstance(fingerprint, dict):
        raise ValueError("fingerprint 必须是对象")
    layout_hash = fingerprint.get("layout_hash")
    cache_path = get_cache_path(layout_hash)
    _write_json(cache_path / "fingerprint.json", fingerprint)
    _touch_meta(layout_hash, {"fingerprint_saved_at": _now_text()})
    return cache_path


def save_rules(layout_hash, rules):
    rules_count = len(rules) if isinstance(rules, list) else 0
    cache_path = get_cache_path(layout_hash)
    _write_json(cache_path / "rules.json", rules)
    _touch_meta(
        layout_hash,
        {
            "rules_saved_at": _now_text(),
            "source": TEMPLATE_CACHE_SOURCE,
            "rules_count": rules_count,
            "parser_version": TEMPLATE_CACHE_PARSER_VERSION,
        },
    )
    return cache_path / "rules.json"


def load_rules(layout_hash):
    return _read_json(get_cache_path(layout_hash) / "rules.json", None)


def load_meta(layout_hash):
    return _read_json(get_cache_path(layout_hash) / "meta.json", {})


def save_meta(layout_hash, meta):
    if not isinstance(meta, dict):
        raise ValueError("meta 必须是对象")
    existing_meta = load_meta(layout_hash)
    now_text = _now_text()
    payload = dict(meta)
    payload["layout_hash"] = str(layout_hash or "").strip().lower()
    payload["created_at"] = payload.get("created_at") or existing_meta.get("created_at") or now_text
    payload["updated_at"] = now_text
    payload["source"] = payload.get("source") or TEMPLATE_CACHE_SOURCE
    payload["rules_count"] = int(payload.get("rules_count") or 0)
    payload["parser_version"] = payload.get("parser_version") or TEMPLATE_CACHE_PARSER_VERSION
    meta_path = get_cache_path(layout_hash) / "meta.json"
    _write_json(meta_path, payload)
    return payload
