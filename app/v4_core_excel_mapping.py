import json
from json import JSONDecodeError

from app.logger import get_logger
from app.runtime_paths import get_base_dir


logger = get_logger(__name__)


def _get_core_excel_mapping_path():
    return get_base_dir() / "v4" / "rules" / "core_excel_mapping.json"


def load_core_excel_mapping():
    mapping_path = _get_core_excel_mapping_path()
    try:
        with mapping_path.open("r", encoding="utf-8") as f:
            mapping = json.load(f)
    except JSONDecodeError as exc:
        logger.error("[CoreExcelMapping] Mapping JSON parse failed: path=%s error=%s", mapping_path, exc)
        return {}
    except OSError as exc:
        logger.error("[CoreExcelMapping] Mapping read failed: path=%s error=%s", mapping_path, exc)
        return {}

    return mapping if isinstance(mapping, dict) else {}


def description_fields_to_operations(description_fields, mapping):
    warnings = []
    operations = []

    if not isinstance(description_fields, dict):
        return {
            "success": False,
            "operations": [],
            "warnings": ["description_fields 必须是对象"],
        }

    mappings = mapping.get("mappings", []) if isinstance(mapping, dict) else []
    if not isinstance(mappings, list):
        return {
            "success": False,
            "operations": [],
            "warnings": ["mapping.mappings 必须是数组"],
        }

    for item in mappings:
        if not isinstance(item, dict):
            warnings.append("发现无效映射项，已跳过。")
            continue

        source_field = str(item.get("source_field") or "").strip()
        target_cell = str(item.get("target_cell") or "").strip()
        operation = str(item.get("operation") or "write_text").strip()
        if not source_field:
            warnings.append("映射项缺少 source_field，已跳过。")
            continue
        if not target_cell:
            warnings.append(f"字段 {source_field} 缺少 target_cell，已跳过。")
            continue
        if source_field not in description_fields:
            warnings.append(f"字段 {source_field} 不存在，已跳过。")
            continue

        operations.append({
            "operation": operation,
            "source_field": source_field,
            "target_cell": target_cell,
            "value": "" if description_fields.get(source_field) is None else str(description_fields.get(source_field)),
        })

    logger.info(
        "[CoreExcelMapping] Operations generated: operations=%s warnings=%s",
        len(operations),
        len(warnings),
    )
    return {
        "success": True,
        "operations": operations,
        "warnings": warnings,
    }
