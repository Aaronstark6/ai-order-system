import json
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from zipfile import BadZipFile

from fastapi import APIRouter, Body, File, Form, UploadFile
from fastapi.responses import FileResponse
from openpyxl.utils.exceptions import InvalidFileException

from app.logger import get_logger
from app.runtime_paths import get_base_dir
from app.v4_batch_template_executor import execute_batch_template_to_excel
from app.v4_excel_rule_executor import execute_excel_rule_preview_to_workbook
from app.v4_excel_renderer import export_description_fields_to_debug_excel
from app.v4_excel_rule_preview import build_excel_rule_preview
from app.v4_excel_rules import get_template_rules, load_excel_render_rules, save_excel_render_rules
from app.v4_excel_rules_validator import validate_excel_render_rules
from app.v4_examples import list_examples, load_example, save_example
from app.v4_renderer import render_example_to_description_fields
from app.v4_schema import get_product_form, get_product_forms, load_product_schema, save_product_schema
from app.v4_schema_version import check_schema_compatibility, get_current_schema_version
from app.v4_template_cache import (
    delete_cached_template,
    get_cached_template_detail,
    list_cached_templates,
    save_fingerprint,
    update_template_info,
)
from app.v4_template_fingerprint import SUPPORTED_SUFFIXES, build_template_fingerprint
from app.v4_template_matcher import match_or_parse_template, match_template
from app.v4_template_rule_executor import (
    execute_ai_template_to_excel,
    execute_rules_to_template_excel,
    execute_rules_to_template_excel_with_preview,
    执行模板规则并生成Excel,
)
from app.v4_validator import validate_example_order


router = APIRouter()
logger = get_logger(__name__)


def _save_v4_uploaded_template(file: UploadFile):
    original_name = Path(file.filename or "").name
    if not original_name:
        raise ValueError("上传文件为空")
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError("仅支持 .xlsx、.xlsm、.xltx、.xltm 格式的 Excel 模板")

    upload_dir = get_base_dir() / "data" / "v4_template_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_output_filename_part(Path(original_name).stem or "template")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stem}_{timestamp}_{uuid.uuid4().hex[:8]}{suffix}"
    output_path = upload_dir / filename

    with output_path.open("wb") as buffer:
        file.file.seek(0)
        shutil.copyfileobj(file.file, buffer)

    if output_path.stat().st_size <= 0:
        output_path.unlink(missing_ok=True)
        raise ValueError("上传文件为空")

    return output_path


def _remove_v4_uploaded_template(path):
    if not path:
        return
    try:
        Path(path).unlink(missing_ok=True)
    except Exception:
        logger.warning("V4 temporary template cleanup failed: path=%s", path, exc_info=True)


@router.get("/api/v4/health")
def api_v4_health():
    schema_loaded = False
    examples_count = 0
    excel_rules_loaded = False

    try:
        base_dir = get_base_dir()
        schema_path = base_dir / "v4" / "schemas" / "product_schema.json"
        examples_dir = base_dir / "v4" / "examples"
        rules_path = base_dir / "v4" / "schemas" / "excel_render_rules.json"

        if not schema_path.is_file():
            raise FileNotFoundError(f"Product Schema not found: {schema_path}")
        with schema_path.open("r", encoding="utf-8") as f:
            schema = json.load(f)
        schema_loaded = isinstance(schema, dict) and bool(schema)
        if not schema_loaded:
            raise ValueError("Product Schema is empty or invalid")

        if not examples_dir.is_dir():
            raise FileNotFoundError(f"Examples directory not found: {examples_dir}")
        examples_count = len(list(examples_dir.glob("*.json")))

        if not rules_path.is_file():
            raise FileNotFoundError(f"Excel render rules not found: {rules_path}")
        with rules_path.open("r", encoding="utf-8") as f:
            excel_rules = json.load(f)
        excel_rules_loaded = isinstance(excel_rules, dict) and bool(excel_rules)
        if not excel_rules_loaded:
            raise ValueError("Excel render rules are empty or invalid")

        return {
            "success": True,
            "version": "v4-dev",
            "module": "v4",
            "schema_loaded": schema_loaded,
            "examples_count": examples_count,
            "excel_rules_loaded": excel_rules_loaded,
            "message": "V4 experimental chain is available",
        }
    except Exception as exc:
        logger.exception("V4 health check failed")
        return {
            "success": False,
            "version": "v4-dev",
            "module": "v4",
            "schema_loaded": schema_loaded,
            "examples_count": examples_count,
            "excel_rules_loaded": excel_rules_loaded,
            "error": str(exc),
        }


def _safe_output_filename_part(value: str) -> str:
    text = str(value or "").strip()
    if text.endswith(".json"):
        text = text[:-5]
    text = re.sub(r"[^\w.-]+", "_", text, flags=re.UNICODE)
    return text.strip("._") or "output"


def _resolve_template_path(template_path: str):
    raw_path = str(template_path or "").strip()
    if not raw_path:
        return None, "template_path \u4e0d\u80fd\u4e3a\u7a7a"

    path = Path(raw_path)
    if ".." in path.parts:
        return None, "\u6a21\u677f\u8def\u5f84\u4e0d\u5141\u8bb8\u5305\u542b .."

    resolved = path.resolve()
    if not resolved.is_file():
        return None, "\u6a21\u677f\u6587\u4ef6\u4e0d\u5b58\u5728"

    return resolved, ""


def _resolve_v4_output_file(filename: str):
    requested_name = str(filename or "").strip()
    requested_path = Path(requested_name)
    if (
        not requested_name
        or "/" in requested_name
        or "\\" in requested_name
        or requested_name in {".", ".."}
        or requested_path.is_absolute()
        or requested_path.name != requested_name
    ):
        return None

    if requested_name.endswith(".json"):
        media_type = "application/json"
    elif requested_name.endswith(".xlsx"):
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    else:
        return None

    output_dir = (get_base_dir() / "v4" / "output").resolve()
    output_path = (output_dir / requested_name).resolve()

    try:
        output_path.relative_to(output_dir)
    except ValueError:
        return None

    if not output_path.is_file():
        return None

    return output_path, media_type


@router.get("/api/v4/product-schema")
def api_v4_product_schema():
    logger.info("V4 product schema requested")
    return {
        "success": True,
        "data": load_product_schema(),
    }


def _load_v4_order_object_for_schema_version():
    order_object_path = get_base_dir() / "v4" / "examples" / "order_object.json"
    if not order_object_path.is_file():
        return None

    try:
        with order_object_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.warning("V4 order object schema version read failed: path=%s", order_object_path, exc_info=True)
        return None


@router.get("/api/v4/schema-version")
def api_v4_schema_version():
    logger.info("V4 schema version requested")
    compatibility = check_schema_compatibility(_load_v4_order_object_for_schema_version())
    return {
        "success": True,
        "current_version": get_current_schema_version(),
        "order_object_version": compatibility.get("order_object_version"),
        "compatible": compatibility.get("compatible", True),
        "level": compatibility.get("level", "warning"),
        "message": compatibility.get("message", ""),
    }


@router.post("/api/v4/product-schema")
def api_v4_save_product_schema(schema: Any):
    result = save_product_schema(schema)
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "V4 product schema save failed"),
        }

    return {
        "success": True,
        "data": result.get("data", {}),
    }


@router.get("/api/v4/output/{filename}")
def api_v4_download_output_file(filename: str):
    resolved = _resolve_v4_output_file(filename)
    if not resolved:
        logger.info("V4 output download not found or rejected: filename=%s", filename)
        return {
            "success": False,
            "error": "\u6587\u4ef6\u4e0d\u5b58\u5728",
        }

    output_path, media_type = resolved
    logger.info("V4 output download requested: path=%s", output_path)
    return FileResponse(
        path=str(output_path),
        filename=output_path.name,
        media_type=media_type,
    )


@router.post("/api/v4/template/fingerprint")
def api_v4_template_fingerprint(file: UploadFile = File(...)):
    temp_path = None
    try:
        logger.info("V4 template fingerprint requested: filename=%s", file.filename)
        temp_path = _save_v4_uploaded_template(file)
        fingerprint = build_template_fingerprint(temp_path)
        save_fingerprint(fingerprint)
        return {
            "success": True,
            "data": fingerprint,
            "fingerprint": fingerprint,
            "layout_hash": fingerprint.get("layout_hash", ""),
        }
    except ValueError as exc:
        logger.info("V4 template fingerprint rejected: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except (BadZipFile, InvalidFileException):
        logger.info("V4 template fingerprint rejected as non Excel: filename=%s", file.filename)
        return {
            "success": False,
            "error": "文件不是 Excel",
        }
    except Exception as exc:
        logger.exception("V4 template fingerprint failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"模板指纹生成失败：{exc}",
        }
    finally:
        _remove_v4_uploaded_template(temp_path)


@router.post("/api/v4/template/fingerprint-test")
def api_v4_template_fingerprint_test(file: Optional[UploadFile] = File(None)):
    temp_path = None
    if file is None:
        return {
            "success": False,
            "error": "上传文件为空",
        }

    try:
        logger.info("V4 template fingerprint stability test requested: filename=%s", file.filename)
        temp_path = _save_v4_uploaded_template(file)
        fingerprints = [build_template_fingerprint(temp_path) for _ in range(3)]
        hashes = [fingerprint.get("layout_hash", "") for fingerprint in fingerprints]
        all_equal = len(set(hashes)) == 1
        result = {
            "all_equal": all_equal,
            "hashes": hashes,
            "fingerprints": fingerprints,
        }
        if not all_equal:
            result["warning"] = "同一个 Excel 连续 3 次生成的 layout_hash 不一致"

        return {
            "success": True,
            "data": result,
            **result,
        }
    except ValueError as exc:
        logger.info("V4 template fingerprint stability test rejected: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except (BadZipFile, InvalidFileException):
        logger.info("V4 template fingerprint stability test rejected as non Excel: filename=%s", file.filename)
        return {
            "success": False,
            "error": "文件不是 Excel",
        }
    except Exception as exc:
        logger.exception("V4 template fingerprint stability test failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"模板指纹稳定性测试失败：{exc}",
        }
    finally:
        _remove_v4_uploaded_template(temp_path)


@router.post("/api/v4/template/match")
def api_v4_template_match(file: UploadFile = File(...)):
    temp_path = None
    try:
        logger.info("V4 template match requested: filename=%s", file.filename)
        temp_path = _save_v4_uploaded_template(file)
        result = match_template(temp_path)
        return {
            "success": True,
            "data": result,
            "cache_hit": result.get("cache_hit", False),
            "layout_hash": result.get("layout_hash", ""),
            "fingerprint": result.get("fingerprint"),
            "cached_rules": result.get("cached_rules"),
        }
    except ValueError as exc:
        logger.info("V4 template match rejected: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except (BadZipFile, InvalidFileException):
        logger.info("V4 template match rejected as non Excel: filename=%s", file.filename)
        return {
            "success": False,
            "error": "文件不是 Excel",
        }
    except Exception as exc:
        logger.exception("V4 template match failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"模板缓存检查失败：{exc}",
        }
    finally:
        _remove_v4_uploaded_template(temp_path)


@router.post("/api/v4/template/match-or-parse")
def api_v4_template_match_or_parse(file: Optional[UploadFile] = File(None)):
    temp_path = None
    if file is None:
        return {
            "success": False,
            "error": "上传文件为空",
        }

    try:
        logger.info("V4 template match-or-parse requested: filename=%s", file.filename)
        temp_path = _save_v4_uploaded_template(file)
        result = match_or_parse_template(temp_path)
        if result.get("success") is False:
            return {
                "success": False,
                "error": result.get("error", "AI 解析失败"),
                "cache_hit": result.get("cache_hit", False),
                "source": result.get("source", "ai_template_parser"),
                "layout_hash": result.get("layout_hash", ""),
                "fingerprint": result.get("fingerprint"),
                "rules": result.get("rules", []),
                "warnings": result.get("warnings", []),
                "meta": result.get("meta", {}),
            }

        return {
            "success": True,
            "data": result,
            "cache_hit": result.get("cache_hit", False),
            "source": result.get("source", ""),
            "layout_hash": result.get("layout_hash", ""),
            "fingerprint": result.get("fingerprint"),
            "rules": result.get("rules", []),
            "warnings": result.get("warnings", []),
            "meta": result.get("meta", {}),
        }
    except ValueError as exc:
        logger.info("V4 template match-or-parse rejected: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except (BadZipFile, InvalidFileException):
        logger.info("V4 template match-or-parse rejected as non Excel: filename=%s", file.filename)
        return {
            "success": False,
            "error": "文件不是 Excel",
        }
    except json.JSONDecodeError as exc:
        logger.exception("V4 template cache read failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"缓存读取失败：{exc}",
        }
    except OSError as exc:
        logger.exception("V4 template cache or rules save failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"rules 保存失败：{exc}",
        }
    except Exception as exc:
        logger.exception("V4 template match-or-parse failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"AI 解析失败：{exc}",
        }
    finally:
        _remove_v4_uploaded_template(temp_path)


@router.get("/api/v4/template/cache-list")
def api_v4_template_cache_list():
    try:
        templates = list_cached_templates()
        return {
            "success": True,
            "templates": templates,
        }
    except Exception as exc:
        logger.exception("V4 template cache list failed")
        return {
            "success": False,
            "error": f"已学习模板列表加载失败：{exc}",
            "templates": [],
        }


@router.get("/api/v4/template/cache-detail/{layout_hash}")
def api_v4_template_cache_detail(layout_hash: str):
    try:
        detail = get_cached_template_detail(layout_hash)
        return {
            "success": True,
            "detail": detail,
        }
    except FileNotFoundError:
        logger.info("V4 template cache detail not found: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": "模板缓存不存在",
        }
    except ValueError as exc:
        logger.info("V4 template cache detail rejected: layout_hash=%s error=%s", layout_hash, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("V4 template cache detail failed: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": f"模板详情读取失败：{exc}",
        }


@router.delete("/api/v4/template/cache/{layout_hash}")
def api_v4_template_cache_delete(layout_hash: str):
    try:
        delete_cached_template(layout_hash)
        return {
            "success": True,
            "message": "模板缓存已删除",
        }
    except FileNotFoundError:
        logger.info("V4 template cache delete not found: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": "模板缓存不存在",
        }
    except ValueError as exc:
        logger.info("V4 template cache delete rejected: layout_hash=%s error=%s", layout_hash, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("V4 template cache delete failed: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": f"模板缓存删除失败：{exc}",
        }


@router.post("/api/v4/template/cache-update/{layout_hash}")
def api_v4_template_cache_update(layout_hash: str, payload: Any = Body(None)):
    if not isinstance(payload, dict):
        payload = {}
    try:
        template_name = payload.get("template_name")
        template_note = payload.get("template_note")
        meta = update_template_info(layout_hash, template_name=template_name, template_note=template_note)
        return {
            "success": True,
            "meta": meta,
        }
    except FileNotFoundError:
        logger.info("V4 template cache update not found: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": "模板缓存不存在",
        }
    except ValueError as exc:
        logger.info("V4 template cache update rejected: layout_hash=%s error=%s", layout_hash, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except Exception as exc:
        logger.exception("V4 template cache update failed: layout_hash=%s", layout_hash)
        return {
            "success": False,
            "error": f"模板信息更新失败：{exc}",
        }


def _load_workbench_example_order(example_order_text: str = ""):
    if not isinstance(example_order_text, str):
        example_order_text = ""
    if str(example_order_text or "").strip():
        payload = json.loads(example_order_text)
        if not isinstance(payload, dict):
            raise ValueError("example_order 必须是 JSON object")
        return payload

    example = load_example("soft_capsule_order_example")
    if not example:
        raise ValueError("默认示例订单不存在")
    return example


def _build_workbench_rules_config(rules):
    if not isinstance(rules, list) or not rules:
        raise ValueError("rules 为空")

    template_key = "workbench_template"
    return template_key, {
        "version": "v4.19-workbench",
        "description": "Workbench generated temporary rules config",
        "templates": {
            template_key: {
                "label": "Workbench 智能模板规则",
                "rules": rules,
            }
        },
    }


@router.post("/api/v4/workbench/export")
def api_v4_workbench_export(
    file: Optional[UploadFile] = File(None),
    rules: str = Form(""),
    example_order: str = Form(""),
):
    temp_path = None
    if file is None:
        return {
            "success": False,
            "error": "尚未上传模板",
        }

    try:
        if not str(rules or "").strip():
            return {
                "success": False,
                "error": "尚未完成智能解析",
            }

        parsed_rules = json.loads(rules)
        if not isinstance(parsed_rules, list) or not parsed_rules:
            return {
                "success": False,
                "error": "rules 为空",
            }

        logger.info("V4 workbench export requested: filename=%s rules=%s", file.filename, len(parsed_rules))
        temp_path = _save_v4_uploaded_template(file)
        example = _load_workbench_example_order(example_order)
        template_key, rules_config = _build_workbench_rules_config(parsed_rules)

        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "Excel 生成失败：Renderer 失败"),
            }

        preview_result = build_excel_rule_preview(
            example,
            render_result.get("description_fields", {}),
            rules_config,
            template_key,
        )
        if not preview_result.get("success"):
            return {
                "success": False,
                "error": preview_result.get("error", "Excel 生成失败：规则预览失败"),
            }

        operations = preview_result.get("operations", [])
        if not isinstance(operations, list):
            operations = []

        output_dir = get_base_dir() / "v4" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_template_name = _safe_output_filename_part(Path(file.filename or "template").stem)
        filename = f"workbench_{safe_template_name}_{timestamp}.xlsx"
        output_path = output_dir / filename

        executor_result = execute_rules_to_template_excel(
            str(temp_path),
            operations,
            str(output_path),
        )
        if not executor_result.get("success"):
            return {
                "success": False,
                "error": executor_result.get("error", "Excel 生成失败"),
                "warnings": preview_result.get("warnings", []) + executor_result.get("warnings", []),
                "operations_count": len(operations),
            }

        download_url = f"/api/v4/output/{filename}"
        if not download_url:
            return {
                "success": False,
                "error": "下载链接生成失败",
            }

        warnings = []
        warnings.extend(render_result.get("warnings", []))
        warnings.extend(preview_result.get("warnings", []))
        warnings.extend(executor_result.get("warnings", []))

        logger.info(
            "V4 workbench export succeeded: filename=%s operations=%s warnings=%s",
            filename,
            len(operations),
            len(warnings),
        )
        return {
            "success": True,
            "filename": filename,
            "download_url": download_url,
            "warnings": warnings,
            "operations_count": len(operations),
            "operations_written": executor_result.get("operations_written", 0),
        }
    except json.JSONDecodeError as exc:
        logger.info("V4 workbench export rejected by invalid JSON: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": f"Excel 生成失败：rules JSON 不合法",
        }
    except ValueError as exc:
        logger.info("V4 workbench export rejected: filename=%s error=%s", file.filename, exc)
        return {
            "success": False,
            "error": str(exc),
        }
    except (BadZipFile, InvalidFileException):
        logger.info("V4 workbench export rejected as non Excel: filename=%s", file.filename)
        return {
            "success": False,
            "error": "文件不是 Excel",
        }
    except Exception as exc:
        logger.exception("V4 workbench export failed: filename=%s", file.filename)
        return {
            "success": False,
            "error": f"Excel 生成失败：{exc}",
        }
    finally:
        _remove_v4_uploaded_template(temp_path)


@router.get("/api/v4/excel-render-rules")
def api_v4_excel_render_rules():
    logger.info("V4 Excel render rules requested")
    return {
        "success": True,
        "data": load_excel_render_rules(),
    }


@router.post("/api/v4/excel-render-rules")
def api_v4_save_excel_render_rules(rules_config: Any):
    logger.info("V4 Excel render rules save requested")
    validation_result = validate_excel_render_rules(rules_config)
    if validation_result.get("errors"):
        logger.info(
            "V4 Excel render rules save rejected by validation: errors=%s warnings=%s",
            len(validation_result.get("errors", [])),
            len(validation_result.get("warnings", [])),
        )
        return {
            "success": False,
            "error": "\u0045\u0078\u0063\u0065\u006c\u6e32\u67d3\u89c4\u5219\u6821\u9a8c\u5931\u8d25",
            "validation": validation_result,
        }

    result = save_excel_render_rules(rules_config)
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "V4 Excel render rules save failed"),
        }

    return {
        "success": True,
        "data": result.get("data", {}),
        "validation": validation_result,
    }


@router.get("/api/v4/excel-render-rules/validate")
def api_v4_validate_excel_render_rules():
    logger.info("V4 Excel render rules validation requested")
    return {
        "success": True,
        "data": validate_excel_render_rules(load_excel_render_rules()),
    }


@router.get("/api/v4/excel-render-rules/{template_key}")
def api_v4_excel_render_template_rules(template_key: str):
    template_rules = get_template_rules(template_key)
    if not template_rules:
        logger.info("V4 Excel render rules template not found: template_key=%s", template_key)
        return {
            "success": False,
            "error": "\u0045\u0078\u0063\u0065\u006c\u6e32\u67d3\u89c4\u5219\u6a21\u677f\u4e0d\u5b58\u5728",
        }

    logger.info("V4 Excel render rules template requested: template_key=%s", template_key)
    return {
        "success": True,
        "data": template_rules,
    }


@router.get("/api/v4/product-forms")
def api_v4_product_forms():
    logger.info("V4 product forms requested")
    return {
        "success": True,
        "data": get_product_forms(),
    }


@router.get("/api/v4/product-forms/{form_key}")
def api_v4_product_form(form_key: str):
    product_forms = get_product_forms()
    if form_key not in product_forms:
        logger.info("V4 product form not found: form_key=%s", form_key)
        return {
            "success": False,
            "error": "产品形式不存在",
        }

    logger.info("V4 product form requested: form_key=%s", form_key)
    return {
        "success": True,
        "data": get_product_form(form_key),
    }


@router.get("/api/v4/examples")
def api_v4_examples():
    logger.info("V4 examples requested")
    return {
        "success": True,
        "data": list_examples(),
    }


@router.get("/api/v4/examples/{example_name}")
def api_v4_example(example_name: str):
    example = load_example(example_name)
    if not example:
        logger.info("V4 example not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    logger.info("V4 example requested: example_name=%s", example_name)
    return {
        "success": True,
        "data": example,
    }


@router.post("/api/v4/examples/{example_name}")
def api_v4_save_example(example_name: str, data: Any):
    result = save_example(example_name, data)
    if not result.get("success"):
        return {
            "success": False,
            "error": result.get("error", "V4 example save failed"),
        }

    return {
        "success": True,
    }


@router.get("/api/v4/examples/{example_name}/validate")
def api_v4_example_validate(example_name: str):
    example = load_example(example_name)
    if not example:
        logger.info("V4 example validate not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    logger.info("V4 example validate requested: example_name=%s", example_name)
    return {
        "success": True,
        "data": validate_example_order(example, load_product_schema()),
    }


@router.get("/api/v4/examples/{example_name}/render-description")
def api_v4_example_render_description(example_name: str):
    example = load_example(example_name)
    if not example:
        logger.info("V4 example render-description not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    logger.info("V4 example render-description requested: example_name=%s", example_name)
    return {
        "success": True,
        "data": render_example_to_description_fields(example, load_product_schema()),
    }


@router.get("/api/v4/examples/{example_name}/excel-rule-preview")
def api_v4_example_excel_rule_preview(example_name: str, template_key: str = ""):
    if not str(template_key or "").strip():
        return {
            "success": False,
            "error": "template_key \u4e0d\u80fd\u4e3a\u7a7a",
        }

    example = load_example(example_name)
    if not example:
        logger.info("V4 example Excel rule preview not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    try:
        logger.info(
            "V4 example Excel rule preview requested: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "V4 renderer failed"),
            }

        preview_result = build_excel_rule_preview(
            example,
            render_result.get("description_fields", {}),
            load_excel_render_rules(),
            template_key,
        )
        if not preview_result.get("success"):
            return {
                "success": False,
                "error": preview_result.get("error", "V4 Excel rule preview failed"),
            }

        return {
            "success": True,
            "data": preview_result,
        }
    except Exception as exc:
        logger.exception(
            "V4 example Excel rule preview failed: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-rule-excel")
def api_v4_example_export_rule_excel(example_name: str, template_key: str = ""):
    if not str(template_key or "").strip():
        return {
            "success": False,
            "error": "template_key \u4e0d\u80fd\u4e3a\u7a7a",
        }

    example = load_example(example_name)
    if not example:
        logger.info("V4 example export rule Excel not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    try:
        logger.info(
            "V4 example export rule Excel requested: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "V4 renderer failed"),
            }

        preview_result = build_excel_rule_preview(
            example,
            render_result.get("description_fields", {}),
            load_excel_render_rules(),
            template_key,
        )
        if not preview_result.get("success"):
            return {
                "success": False,
                "error": preview_result.get("error", "V4 Excel rule preview failed"),
            }

        output_dir = get_base_dir() / "v4" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_example_name = _safe_output_filename_part(example_name)
        safe_template_key = _safe_output_filename_part(template_key)
        filename = f"{safe_example_name}_{safe_template_key}_rule_excel_{timestamp}.xlsx"
        output_path = output_dir / filename

        executor_result = execute_excel_rule_preview_to_workbook(
            preview_result.get("operations", []),
            str(output_path),
        )
        if not executor_result.get("success"):
            return {
                "success": False,
                "error": executor_result.get("error", "V4 Excel rule executor failed"),
            }

        warnings = []
        warnings.extend(preview_result.get("warnings", []))
        warnings.extend(executor_result.get("warnings", []))

        logger.info(
            "V4 example export rule Excel succeeded: output_path=%s operations_written=%s warnings=%s",
            output_path,
            executor_result.get("operations_written", 0),
            len(warnings),
        )
        return {
            "success": True,
            "output_path": str(output_path),
            "filename": filename,
            "operations_written": executor_result.get("operations_written", 0),
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception(
            "V4 example export rule Excel failed: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-template-rule-excel")
def api_v4_example_export_template_rule_excel(example_name: str, payload: Any = Body(None), template_key: str = ""):
    if not str(template_key or "").strip():
        return {
            "success": False,
            "error": "template_key \u4e0d\u80fd\u4e3a\u7a7a",
        }
    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": "template_path \u4e0d\u80fd\u4e3a\u7a7a",
        }

    template_path, template_path_error = _resolve_template_path(payload.get("template_path"))
    if template_path_error:
        return {
            "success": False,
            "error": template_path_error,
        }

    example = load_example(example_name)
    if not example:
        logger.info("V4 example export template rule Excel not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    try:
        logger.info(
            "V4 example export template rule Excel requested: example_name=%s template_key=%s template_path=%s",
            example_name,
            template_key,
            template_path,
        )
        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "V4 renderer failed"),
            }

        preview_result = build_excel_rule_preview(
            example,
            render_result.get("description_fields", {}),
            load_excel_render_rules(),
            template_key,
        )
        if not preview_result.get("success"):
            return {
                "success": False,
                "error": preview_result.get("error", "V4 Excel rule preview failed"),
            }
        operations = preview_result.get("operations", [])
        if not isinstance(operations, list):
            operations = []

        output_dir = get_base_dir() / "v4" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_example_name = _safe_output_filename_part(example_name)
        safe_template_key = _safe_output_filename_part(template_key)
        filename = f"{safe_example_name}_{safe_template_key}_template_rule_{timestamp}.xlsx"
        output_path = output_dir / filename

        executor_result = execute_rules_to_template_excel(
            str(template_path),
            operations,
            str(output_path),
        )
        if not executor_result.get("success"):
            return {
                "success": False,
                "error": executor_result.get("error", "V4 template rule executor failed"),
            }

        warnings = []
        warnings.extend(preview_result.get("warnings", []))
        warnings.extend(executor_result.get("warnings", []))

        logger.info(
            "V4 example export template rule Excel succeeded: output_path=%s operations_written=%s warnings=%s",
            output_path,
            executor_result.get("operations_written", 0),
            len(warnings),
        )
        return {
            "success": True,
            "filename": filename,
            "output_path": str(output_path),
            "operations_written": executor_result.get("operations_written", 0),
            "operations": operations,
            "warnings": warnings,
        }
    except Exception as exc:
        logger.exception(
            "V4 example export template rule Excel failed: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-template-rule-excel-with-preview")
def api_v4_example_export_template_rule_excel_with_preview(example_name: str, payload: Any = Body(None), template_key: str = ""):
    if not str(template_key or "").strip():
        return {
            "success": False,
            "error": "template_key \u4e0d\u80fd\u4e3a\u7a7a",
        }
    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": "template_path \u4e0d\u80fd\u4e3a\u7a7a",
        }

    template_path, template_path_error = _resolve_template_path(payload.get("template_path"))
    if template_path_error:
        return {
            "success": False,
            "error": template_path_error,
        }

    try:
        logger.info(
            "V4 example export template rule Excel with preview requested: example_name=%s template_key=%s template_path=%s",
            example_name,
            template_key,
            template_path,
        )
        result = execute_rules_to_template_excel_with_preview(
            example_name,
            template_key,
            str(template_path),
        )
        if not result.get("success"):
            logger.info(
                "V4 example export template rule Excel with preview failed: example_name=%s template_key=%s error=%s",
                example_name,
                template_key,
                result.get("error", ""),
            )
            return result

        logger.info(
            "V4 example export template rule Excel with preview succeeded: filename=%s operations_written=%s warnings=%s",
            result.get("filename", ""),
            result.get("operations_written", 0),
            len(result.get("warnings", [])),
        )
        return result
    except Exception as exc:
        logger.exception(
            "V4 example export template rule Excel with preview failed: example_name=%s template_key=%s",
            example_name,
            template_key,
        )
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-ai-template-excel")
def api_v4_example_export_ai_template_excel(example_name: str, payload: Any = Body(None)):
    if not isinstance(payload, dict):
        return {
            "success": False,
            "error": "template_path \u4e0d\u80fd\u4e3a\u7a7a",
        }

    template_path, template_path_error = _resolve_template_path(payload.get("template_path"))
    if template_path_error:
        return {
            "success": False,
            "error": template_path_error,
        }

    try:
        logger.info(
            "V4 example export AI template Excel requested: example_name=%s template_path=%s",
            example_name,
            template_path,
        )
        result = execute_ai_template_to_excel(example_name, str(template_path))
        if not result.get("success"):
            logger.info(
                "V4 example export AI template Excel failed: example_name=%s error=%s",
                example_name,
                result.get("error", ""),
            )
            return result

        logger.info(
            "V4 example export AI template Excel succeeded: filename=%s operations_written=%s warnings=%s",
            result.get("filename", ""),
            result.get("operations_written", 0),
            len(result.get("warnings", [])),
        )
        return result
    except Exception as exc:
        logger.exception("V4 example export AI template Excel failed: example_name=%s", example_name)
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-ai-template-excel-cn")
def api_v4_example_export_ai_template_excel_cn(example_name: str, payload: Any = Body(None)):
    if not isinstance(payload, dict):
        return {
            "成功": False,
            "错误": "模板路径不能为空",
        }

    template_path, template_path_error = _resolve_template_path(payload.get("template_path"))
    if template_path_error:
        return {
            "成功": False,
            "错误": template_path_error,
        }

    try:
        logger.info(
            "V4 example export AI template Excel CN requested: example_name=%s template_path=%s",
            example_name,
            template_path,
        )
        result = 执行模板规则并生成Excel(example_name, str(template_path))
        if not result.get("成功"):
            logger.info(
                "V4 example export AI template Excel CN failed: example_name=%s error=%s",
                example_name,
                result.get("错误", ""),
            )
        return result
    except Exception as exc:
        logger.exception("V4 example export AI template Excel CN failed: example_name=%s", example_name)
        return {
            "成功": False,
            "错误": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-batch-ai-excel")
def api_v4_example_export_batch_ai_excel(example_name: str, payload: Any = Body(None)):
    if not isinstance(payload, dict):
        return {
            "成功": False,
            "错误": "模板路径列表不能为空",
        }

    template_paths = payload.get("template_paths")
    if not isinstance(template_paths, list) or not template_paths:
        return {
            "成功": False,
            "错误": "模板路径列表不能为空",
        }

    resolved_template_paths = []
    for template_path in template_paths:
        resolved_path, template_path_error = _resolve_template_path(template_path)
        if template_path_error:
            return {
                "成功": False,
                "错误": f"模板缺失：{template_path or '未命名模板'}；{template_path_error}",
            }
        resolved_template_paths.append(str(resolved_path))

    try:
        logger.info(
            "V4 example export batch AI Excel requested: example_name=%s templates=%s",
            example_name,
            len(resolved_template_paths),
        )
        result = execute_batch_template_to_excel(example_name, resolved_template_paths)
        if not result.get("成功"):
            logger.info(
                "V4 example export batch AI Excel finished with issues: example_name=%s error=%s",
                example_name,
                result.get("错误", ""),
            )
        return result
    except Exception as exc:
        logger.exception("V4 example export batch AI Excel failed: example_name=%s", example_name)
        return {
            "成功": False,
            "错误": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-render-json")
def api_v4_example_export_render_json(example_name: str):
    example = load_example(example_name)
    if not example:
        logger.info("V4 example export render JSON not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    try:
        logger.info("V4 example export render JSON requested: example_name=%s", example_name)
        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "V4 renderer failed"),
            }

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = str(example_name or "").strip()
        if safe_name.endswith(".json"):
            safe_name = safe_name[:-5]
        output_dir = get_base_dir() / "v4" / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{safe_name}_render_{timestamp}.json"
        output_path = output_dir / filename

        payload = {
            "example_name": example_name,
            "generated_at": generated_at,
            "description_fields": render_result.get("description_fields", {}),
            "warnings": render_result.get("warnings", []),
        }
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.write("\n")

        logger.info("V4 example export render JSON succeeded: path=%s", output_path)
        return {
            "success": True,
            "output_path": str(output_path),
            "filename": filename,
        }
    except Exception as exc:
        logger.exception("V4 example export render JSON failed: example_name=%s", example_name)
        return {
            "success": False,
            "error": str(exc),
        }


@router.post("/api/v4/examples/{example_name}/export-debug-excel")
def api_v4_example_export_debug_excel(example_name: str):
    example = load_example(example_name)
    if not example:
        logger.info("V4 example export debug Excel not found: example_name=%s", example_name)
        return {
            "success": False,
            "error": "\u793a\u4f8b\u8ba2\u5355\u4e0d\u5b58\u5728",
        }

    try:
        logger.info("V4 example export debug Excel requested: example_name=%s", example_name)
        render_result = render_example_to_description_fields(example, load_product_schema())
        if not render_result.get("success"):
            return {
                "success": False,
                "error": render_result.get("error", "V4 renderer failed"),
            }

        export_result = export_description_fields_to_debug_excel(
            example_name,
            render_result.get("description_fields", {}),
        )
        if not export_result.get("success"):
            return {
                "success": False,
                "error": export_result.get("error", "V4 debug Excel export failed"),
            }

        logger.info(
            "V4 example export debug Excel succeeded: example_name=%s, filename=%s",
            example_name,
            export_result.get("filename"),
        )
        return {
            "success": True,
            "output_path": export_result.get("output_path", ""),
            "filename": export_result.get("filename", ""),
        }
    except Exception as exc:
        logger.exception("V4 example export debug Excel failed: example_name=%s", example_name)
        return {
            "success": False,
            "error": str(exc),
        }
