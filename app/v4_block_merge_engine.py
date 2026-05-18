import json
from copy import deepcopy

from app.runtime_paths import get_base_dir
from app.v4_structured_excel_mapping import _get_product_field


DEFAULT_BLOCK_RULES = {
    "version": "V4-Rebuild.4",
    "blocks": [
        {
            "block_name": "产品说明块",
            "target_cell": "B20",
            "lines": [
                {"label": "产品名称", "source_path": "product.product_name"},
                {"label": "产品类型", "source_path": "product.product_type"},
            ],
        }
    ],
}


def _rules_path():
    return get_base_dir() / "v4" / "rules" / "block_merge_rules.json"


def _ensure_rules_file():
    path = _rules_path()
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(DEFAULT_BLOCK_RULES, f, ensure_ascii=False, indent=2)
            f.write("\n")
    return path


def load_block_merge_rules():
    path = _ensure_rules_file()
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        data = deepcopy(DEFAULT_BLOCK_RULES)
    return data if isinstance(data, dict) else deepcopy(DEFAULT_BLOCK_RULES)


def _get_nested(data, source_path):
    current = data
    for part in str(source_path or "").split("."):
        if not part:
            continue
        if not isinstance(current, dict) or part not in current:
            return None, False
        current = current.get(part)
    return current, True


def _line_value(order_object, line):
    if not isinstance(line, dict):
        return "", False
    if line.get("field_id"):
        return _get_product_field(order_object, str(line.get("field_id") or ""))
    return _get_nested(order_object, line.get("source_path"))


def build_block_operations(order_object):
    rules = load_block_merge_rules()
    warnings = []
    operations = []

    for block in rules.get("blocks", []) if isinstance(rules.get("blocks"), list) else []:
        if not isinstance(block, dict):
            continue

        lines = []
        for line in block.get("lines", []) if isinstance(block.get("lines"), list) else []:
            if not isinstance(line, dict):
                continue
            label = str(line.get("label") or line.get("field_id") or line.get("source_path") or "").strip()
            value, found = _line_value(order_object, line)
            if not found:
                warnings.append(f"{label or '未命名字段'} 未找到，已使用空值。")
                value = ""
            lines.append(f"{label}：{'' if value is None else str(value)}")

        operations.append(
            {
                "block_name": str(block.get("block_name") or "").strip(),
                "target_cell": str(block.get("target_cell") or "").strip(),
                "operation": "write_text",
                "value": "\n".join(lines),
            }
        )

    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
