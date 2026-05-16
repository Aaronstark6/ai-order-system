from pathlib import Path

from app.logger import get_logger
from app.v4_template_rule_executor import execute_ai_template_to_excel


logger = get_logger(__name__)


def _operation_status_label(status):
    return {
        "ok": "正常",
        "warning": "警告",
        "error": "错误",
    }.get(status, status or "")


def _operation_type_label(operation_type):
    return {
        "checkbox": "勾选框",
        "text": "文本",
    }.get(operation_type, operation_type or "")


def _localized_operation(operation):
    if not isinstance(operation, dict):
        return {}

    return {
        "规则 ID": operation.get("rule_id", ""),
        "类型": _operation_type_label(operation.get("type", "")),
        "目标单元格": operation.get("target_cell", ""),
        "值": operation.get("value", ""),
        "写入内容": operation.get("value", ""),
        "状态": _operation_status_label(operation.get("status", "ok")),
        "异常原因": operation.get("status_reasons", []),
    }


def execute_batch_template_to_excel(example_name: str, template_paths: list) -> dict:
    warnings = []
    generated_files = []
    operation_groups = {}
    failed_items = []
    template_results = []

    if not str(example_name or "").strip():
        return {
            "成功": False,
            "错误": "示例订单不能为空",
            "生成文件列表": generated_files,
            "操作列表": operation_groups,
            "警告": warnings,
        }

    if not isinstance(template_paths, list) or not template_paths:
        return {
            "成功": False,
            "错误": "模板路径列表不能为空",
            "生成文件列表": generated_files,
            "操作列表": operation_groups,
            "警告": warnings,
        }

    logger.info(
        "V4 batch AI template export started: example_name=%s templates=%s",
        example_name,
        len(template_paths),
    )

    for template_path in template_paths:
        template_text = str(template_path or "").strip()
        template_name = Path(template_text).name or template_text or "未命名模板"

        if not template_text or not Path(template_text).is_file():
            error = f"模板缺失：{template_name}"
            warnings.append(error)
            failed_items.append({
                "模板": template_name,
                "错误": error,
            })
            continue

        result = execute_ai_template_to_excel(example_name, template_text)
        result_warnings = result.get("warnings", []) if isinstance(result, dict) else []
        warnings.extend([f"{template_name}：{warning}" for warning in result_warnings])

        if not isinstance(result, dict) or not result.get("success"):
            error = result.get("error", "生成失败") if isinstance(result, dict) else "生成失败"
            failed_items.append({
                "模板": template_name,
                "错误": error,
            })
            warnings.append(f"{template_name}：{error}")
            template_results.append({
                "模板": template_name,
                "成功": False,
                "错误": error,
            })
            continue

        filename = result.get("filename", "")
        generated_files.append(filename)
        operations = result.get("operations", [])
        if not isinstance(operations, list):
            operations = []
        operation_groups[filename or template_name] = [_localized_operation(operation) for operation in operations]
        template_results.append({
            "模板": template_name,
            "成功": True,
            "文件名": filename,
            "输出路径": result.get("output_path", ""),
            "写入操作数": result.get("operations_written", 0),
            "规则模板": result.get("template_key", ""),
            "校验统计": result.get("validation", {}),
        })

    success = bool(generated_files) and not failed_items
    response = {
        "成功": success,
        "生成文件列表": generated_files,
        "操作列表": operation_groups,
        "警告": warnings,
        "模板结果列表": template_results,
        "失败列表": failed_items,
    }
    if not success:
        response["错误"] = "批量生成未全部完成" if generated_files else "批量生成失败"

    logger.info(
        "V4 batch AI template export finished: example_name=%s generated=%s failed=%s warnings=%s",
        example_name,
        len(generated_files),
        len(failed_items),
        len(warnings),
    )
    return response
