import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_schema import get_product_types


logger = get_logger(__name__)


def _get_block_merge_rules_path():
    return get_base_dir() / "v4" / "rules" / "block_merge_rules.json"


def load_block_merge_rules():
    rules_path = _get_block_merge_rules_path()
    try:
        with rules_path.open("r", encoding="utf-8") as f:
            rules = json.load(f)
    except JSONDecodeError as exc:
        logger.error("[BlockMergeEngine] Rules JSON parse failed: path=%s error=%s", rules_path, exc)
        return {}
    except OSError as exc:
        logger.error("[BlockMergeEngine] Rules read failed: path=%s error=%s", rules_path, exc)
        return {}

    return rules if isinstance(rules, dict) else {}


def _normalize_line(line):
    if not isinstance(line, dict):
        return None

    label = str(line.get("label") or "").strip()
    field_id = str(line.get("field_id") or "").strip()
    if not label and not field_id:
        return None
    return {
        "label": label or field_id,
        "field_id": field_id,
    }


def _normalize_block(block):
    if not isinstance(block, dict):
        return None

    block_name = str(block.get("block_name") or "").strip()
    target_cell = str(block.get("target_cell") or "").strip()
    lines = []
    raw_lines = block.get("lines", [])
    if isinstance(raw_lines, list):
        for line in raw_lines:
            normalized_line = _normalize_line(line)
            if normalized_line:
                lines.append(normalized_line)

    if not block_name and not target_cell and not lines:
        return None

    return {
        "block_name": block_name or "未命名区块",
        "target_cell": target_cell,
        "lines": lines,
    }


def normalize_block_merge_rules(rules):
    source = rules if isinstance(rules, dict) else {}
    raw_blocks = source.get("blocks", [])
    if not isinstance(raw_blocks, list):
        raw_blocks = []

    blocks = []
    for block in raw_blocks:
        normalized_block = _normalize_block(block)
        if normalized_block:
            blocks.append(normalized_block)

    return {
        "version": "V4-Core.16",
        "blocks": blocks,
    }


def save_block_merge_rules(rules):
    rules_path = _get_block_merge_rules_path()
    normalized = normalize_block_merge_rules(rules)
    try:
        rules_path.parent.mkdir(parents=True, exist_ok=True)
        with rules_path.open("w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as exc:
        logger.exception("[BlockMergeEngine] Rules save failed: path=%s", rules_path)
        return {
            "success": False,
            "error": str(exc) or "区块合并规则保存失败",
        }

    logger.info(
        "[BlockMergeEngine] Rules saved: path=%s blocks=%s",
        rules_path,
        len(normalized.get("blocks", [])),
    )
    return {
        "success": True,
        "data": normalized,
    }


def _find_product_type(product_type_value):
    product_type_value = str(product_type_value or "").strip()
    if not product_type_value:
        return {}

    for product_type in get_product_types():
        if not isinstance(product_type, dict):
            continue
        key = str(product_type.get("key") or "").strip()
        name = str(product_type.get("name") or "").strip()
        if product_type_value in {key, name}:
            return product_type
    return {}


def _build_field_lookup(product_type):
    lookup = {}
    fields = product_type.get("fields", []) if isinstance(product_type, dict) else []
    if not isinstance(fields, list):
        return lookup

    for field in fields:
        if not isinstance(field, dict):
            continue
        key = str(field.get("key") or "").strip()
        name = str(field.get("name") or "").strip()
        if key:
            lookup[key] = key
        if key and name:
            lookup[name] = key
    return lookup


def _resolve_product_field(order_object, field_id):
    product = order_object.get("product", {}) if isinstance(order_object, dict) else {}
    if not isinstance(product, dict):
        return ""

    fields = product.get("fields", {})
    if not isinstance(fields, dict):
        return ""

    identifier = str(field_id or "").strip()
    if not identifier:
        return ""
    if identifier in fields:
        return fields.get(identifier, "")

    product_type = _find_product_type(product.get("product_type"))
    mapped_key = _build_field_lookup(product_type).get(identifier)
    if mapped_key and mapped_key in fields:
        return fields.get(mapped_key, "")

    for source_key, value in fields.items():
        if str(source_key).strip() == identifier:
            return value
    return ""


def _normalize_blocks(block_rules):
    blocks = block_rules.get("blocks", []) if isinstance(block_rules, dict) else []
    return blocks if isinstance(blocks, list) else []


def _normalize_lines(block):
    lines = block.get("lines", []) if isinstance(block, dict) else []
    return lines if isinstance(lines, list) else []


def build_block_operations(order_object, block_rules):
    warnings = []
    operations = []

    if not isinstance(order_object, dict):
        return {
            "success": False,
            "operations": [],
            "warnings": ["Order Object 必须是对象"],
        }

    for block in _normalize_blocks(block_rules):
        if not isinstance(block, dict):
            continue

        block_name = str(block.get("block_name") or "").strip() or "未命名区块"
        target_cell = str(block.get("target_cell") or "").strip()
        if not target_cell:
            warnings.append(f"区块缺少 target_cell：{block_name}")
            continue

        value_lines = []
        for line in _normalize_lines(block):
            if not isinstance(line, dict):
                continue
            label = str(line.get("label") or "").strip()
            field_id = str(line.get("field_id") or "").strip()
            if not label or not field_id:
                continue
            value = _resolve_product_field(order_object, field_id)
            value_text = str(value or "").strip()
            if not value_text:
                continue
            value_lines.append(f"{label}：{value_text}")

        if not value_lines:
            warnings.append(f"区块为空：{block_name}")
            continue

        operations.append({
            "operation": "write_text",
            "target_cell": target_cell,
            "value": "\n".join(value_lines),
            "block_name": block_name,
        })

    logger.info(
        "[BlockMergeEngine] Block operations generated: operations=%s warnings=%s",
        len(operations),
        len(warnings),
    )
    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
