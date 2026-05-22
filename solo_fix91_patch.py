from pathlib import Path

path = Path("app/routes/v4.py")
text = path.read_text(encoding="utf-8")

# 1. 补 import base64
old = "import json\nimport re\nimport shutil\nimport uuid\n"
new = "import base64\nimport json\nimport re\nimport shutil\nimport uuid\n"

if "import base64\n" not in text:
    if old not in text:
        raise SystemExit("找不到 import 锚点，未修改。")
    text = text.replace(old, new, 1)


# 2. 在 export-confirmed-excel 前插入图片导出 helper
anchor = '''
@router.post("/api/v4/export-confirmed-excel")
'''

helper = r'''

def _confirmed_cell_is_image_item(item):
    if not isinstance(item, dict):
        return False
    if str(item.get("field_type") or "").strip() == "image":
        return True
    image = item.get("image")
    return isinstance(image, dict) and bool(str(image.get("data_url") or "").strip())


def _split_confirmed_cells_for_excel_export(confirmed_cells):
    text_items = []
    image_items = []
    for item in confirmed_cells if isinstance(confirmed_cells, list) else []:
        if _confirmed_cell_is_image_item(item):
            image_items.append(item)
        else:
            text_items.append(item)
    return text_items, image_items


def _image_extension_from_mime_type(mime_type):
    mime = str(mime_type or "").strip().lower()
    if mime == "image/png":
        return ".png"
    if mime in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if mime == "image/webp":
        return ".webp"
    return ""


def _extract_image_file_from_confirmed_item(item, tmp_dir):
    image = item.get("image") if isinstance(item, dict) else {}
    image = image if isinstance(image, dict) else {}

    data_url = str(image.get("data_url") or "").strip()
    mime_type = str(image.get("mime_type") or "").strip().lower()

    if not data_url:
        return None, "图片 data_url 为空"

    if "," not in data_url or not data_url.startswith("data:"):
        return None, "图片 data_url 格式无效"

    header, encoded = data_url.split(",", 1)
    header_mime = header[5:].split(";")[0].strip().lower()
    mime_type = mime_type or header_mime

    ext = _image_extension_from_mime_type(mime_type)
    if not ext:
        return None, f"不支持的图片类型：{mime_type or 'unknown'}"

    try:
        raw = base64.b64decode(encoded)
    except Exception as exc:
        return None, f"图片 base64 解码失败：{exc}"

    if not raw:
        return None, "图片内容为空"

    tmp_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
    image_path = tmp_dir / filename
    image_path.write_bytes(raw)
    return image_path, ""


def _fit_openpyxl_image_contain(openpyxl_image, max_width=220, max_height=160):
    try:
        width = float(openpyxl_image.width or 0)
        height = float(openpyxl_image.height or 0)
        if width <= 0 or height <= 0:
            return
        ratio = min(float(max_width) / width, float(max_height) / height, 1.0)
        openpyxl_image.width = int(width * ratio)
        openpyxl_image.height = int(height * ratio)
    except Exception:
        return


def _target_cell_for_image_item(item):
    image = item.get("image") if isinstance(item, dict) else {}
    image = image if isinstance(image, dict) else {}
    return _cell_key(
        item.get("image_anchor_cell")
        or image.get("image_anchor_cell")
        or item.get("cell")
        or item.get("display_cell")
    )


def _insert_confirmed_images_into_excel(exported_file_path, confirmed_cells, excel_feature_flags=None):
    summary = {
        "total": 0,
        "inserted": 0,
        "skipped": 0,
        "warnings": [],
        "disabled": False,
    }

    flags = excel_feature_flags if isinstance(excel_feature_flags, dict) else {}
    if flags.get("image_fields") is not True:
        summary["disabled"] = True
        return summary

    image_items = [
        item for item in confirmed_cells if _confirmed_cell_is_image_item(item)
    ] if isinstance(confirmed_cells, list) else []
    summary["total"] = len(image_items)

    if not image_items:
        return summary

    try:
        from openpyxl import load_workbook
        from openpyxl.drawing.image import Image as OpenpyxlImage
    except Exception as exc:
        summary["skipped"] = len(image_items)
        summary["warnings"].append(f"openpyxl 图片模块不可用：{exc}")
        return summary

    exported_path = Path(exported_file_path)
    if not exported_path.exists():
        summary["skipped"] = len(image_items)
        summary["warnings"].append(f"导出文件不存在，无法插入图片：{exported_path}")
        return summary

    tmp_dir = Path("output") / "_tmp_images"

    try:
        workbook = load_workbook(exported_path)
        sheet = workbook.active
    except Exception as exc:
        summary["skipped"] = len(image_items)
        summary["warnings"].append(f"打开导出 Excel 失败：{exc}")
        return summary

    changed = False
    for item in image_items:
        label = str(item.get("label") or item.get("field_key") or "").strip()
        target_cell = _target_cell_for_image_item(item)

        if not target_cell:
            summary["skipped"] += 1
            summary["warnings"].append(f"图片字段缺少目标单元格：{label or '未命名图片字段'}")
            continue

        image_path, error = _extract_image_file_from_confirmed_item(item, tmp_dir)
        if error:
            summary["skipped"] += 1
            summary["warnings"].append(f"{target_cell} 图片处理失败：{error}")
            continue

        try:
            excel_image = OpenpyxlImage(str(image_path))
            _fit_openpyxl_image_contain(excel_image, max_width=220, max_height=160)
            sheet.add_image(excel_image, target_cell)
            summary["inserted"] += 1
            changed = True
        except Exception as exc:
            summary["skipped"] += 1
            summary["warnings"].append(f"{target_cell} 图片插入失败：{exc}")

    if changed:
        try:
            workbook.save(exported_path)
        except Exception as exc:
            summary["warnings"].append(f"保存包含图片的 Excel 失败：{exc}")

    return summary

'''

if helper.strip() not in text:
    if anchor not in text:
        raise SystemExit("找不到 export-confirmed-excel 装饰器锚点，未插入 helper。")
    text = text.replace(anchor, helper + anchor, 1)


# 3. 在 export-confirmed-excel 中分离文本字段与图片字段
old = '''        override_result = _override_operations_with_confirmed_cells(
            processed_operations,
            confirmed_cells,
            profile=profile,
            template_path=template_path,
        )'''

new = '''        text_confirmed_cells, image_confirmed_cells = _split_confirmed_cells_for_excel_export(confirmed_cells)

        override_result = _override_operations_with_confirmed_cells(
            processed_operations,
            text_confirmed_cells,
            profile=profile,
            template_path=template_path,
        )'''

if new not in text:
    if old not in text:
        raise SystemExit("找不到 override_result confirmed_cells 锚点，未修改。")
    text = text.replace(old, new, 1)


# 4. 在导出成功、路径解析完成后，回读审计前插入图片写入
old = '''        if excel_feature_flags.get("export_readback_check", True):
            export_readback_audit = _build_export_readback_audit(
                exported_file_path,
                confirmed_cells,
                profile=profile,
            )'''

new = '''        image_export_summary = _insert_confirmed_images_into_excel(
            exported_file_path,
            image_confirmed_cells,
            excel_feature_flags=excel_feature_flags,
        )
        if image_export_summary.get("warnings"):
            export_result["warnings"] = [
                *(export_result.get("warnings", []) or []),
                *image_export_summary.get("warnings", []),
            ]

        if excel_feature_flags.get("export_readback_check", True):
            export_readback_audit = _build_export_readback_audit(
                exported_file_path,
                text_confirmed_cells,
                profile=profile,
            )'''

if new not in text:
    if old not in text:
        raise SystemExit("找不到 export_readback_audit 锚点，未修改。")
    text = text.replace(old, new, 1)


# 5. 顶层 response 增加 image_export_summary
old = '''            "excel_feature_flags": excel_feature_flags,
            "export_readback_audit": export_readback_audit,
            "parse_result": pipeline_e2e_result.get("parse_result", {}),'''

new = '''            "excel_feature_flags": excel_feature_flags,
            "image_export_summary": image_export_summary,
            "export_readback_audit": export_readback_audit,
            "parse_result": pipeline_e2e_result.get("parse_result", {}),'''

if new not in text:
    if old not in text:
        raise SystemExit("找不到顶层 response 插入锚点，未修改。")
    text = text.replace(old, new, 1)


# 6. export_result 内增加 image_export_summary
old = '''                "excel_feature_flags": excel_feature_flags,
                "readback_audit": export_readback_audit,
            },'''

new = '''                "excel_feature_flags": excel_feature_flags,
                "image_export_summary": image_export_summary,
                "readback_audit": export_readback_audit,
            },'''

if new not in text:
    if old not in text:
        raise SystemExit("找不到 export_result response 插入锚点，未修改。")
    text = text.replace(old, new, 1)


path.write_text(text, encoding="utf-8")
print("V4-EXCEL-FIX91 patch applied: app/routes/v4.py")
