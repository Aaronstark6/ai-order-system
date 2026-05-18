from openpyxl import load_workbook
from openpyxl.utils import column_index_from_string, get_column_letter

from app.v4_template_intelligence import infer_structured_mapping_from_labels
from app.v4_mapping_generator import generate_auto_mapping
from app.v4_template_scanner import scan_excel_labels


HEADER_FIELDS = {
    "原料名": "name",
    "原料": "name",
    "项目名称": "name",
    "项目": "name",
    "含量": "amount",
    "结果": "result",
    "百分比": "percentage",
    "规格": "spec",
    "标准": "standard",
    "营养成分": "nutrient",
    "每份含量": "amount",
    "NRV%": "nrv",
}

BLOCK_KEYWORDS = [
    "产品说明",
    "产品特点",
    "包装要求",
    "其他要求",
    "备注",
    "说明",
]

SCORING_KEYWORDS = [
    "产品描述",
    "产品详细要求",
    "包装要求",
    "配方要求",
    "容器要求",
    "装量要求",
    "容器内填充物",
    "瓶口密封",
    "盖子密封",
    "标签要求",
    "客户设计制作",
    "我司设计制作",
    "生产日期",
    "批号",
    "客户名称",
    "客户性质",
    "负责人",
    "文档编号",
    "日期",
    "原料名",
    "含量",
    "百分比",
    "项目名称",
    "标准",
    "结果",
]

SEMANTIC_RULES = [
    (
        "product_detail",
        [
            "产品详细",
            "产品描述",
            "软胶囊",
            "片剂",
            "固体饮料",
            "软糖",
        ],
    ),
    (
        "packaging",
        [
            "包装要求",
            "容器要求",
            "装量要求",
            "容器内填充物",
            "瓶口密封",
            "盖子密封",
        ],
    ),
    (
        "formula",
        [
            "配方要求",
            "原料名",
            "含量",
            "百分比",
        ],
    ),
    (
        "label_requirement",
        [
            "标签要求",
            "客户设计制作",
            "我司设计制作",
            "不贴标签",
        ],
    ),
    (
        "production_batch",
        [
            "生产日期",
            "批号",
        ],
    ),
    (
        "customer_info",
        [
            "客户名称",
            "客户性质",
            "数量",
            "负责人",
        ],
    ),
    (
        "document_info",
        [
            "文档编号",
            "日期",
        ],
    ),
]

SEMANTIC_NAMES = {
    "product_detail": "产品详细要求区域",
    "packaging": "包装要求区域",
    "formula": "配方要求区域",
    "label_requirement": "标签要求区域",
    "production_batch": "生产日期批号区域",
    "customer_info": "客户信息区域",
    "document_info": "文档信息区域",
    "unknown": "智能识别区域",
}


def _clean_text(value):
    text = str(value or "").strip()
    return text.rstrip(":：") if text else ""


def _cell_value(cell):
    if cell.value is None:
        return ""
    return str(cell.value).strip()


def _is_empty_cell(cell):
    return _cell_value(cell) == ""


def _load_workbook(template_path):
    return load_workbook(template_path, data_only=True)


def _row_text_cells(sheet, row_number):
    cells = []
    for cell in sheet[row_number]:
        value = _clean_text(cell.value)
        if value:
            cells.append(
                {
                    "sheet": sheet.title,
                    "row": cell.row,
                    "col": cell.column,
                    "cell": cell.coordinate,
                    "value": value,
                }
            )
    return cells


def _contiguous_runs(cells):
    if not cells:
        return []

    runs = []
    current = [cells[0]]
    for cell in cells[1:]:
        if cell["col"] == current[-1]["col"] + 1:
            current.append(cell)
        else:
            runs.append(current)
            current = [cell]
    runs.append(current)
    return runs


def _has_data_below(sheet, header_row, start_col, end_col):
    for row_number in range(header_row + 1, min(sheet.max_row, header_row + 8) + 1):
        values = [
            _cell_value(sheet.cell(row=row_number, column=col))
            for col in range(start_col, end_col + 1)
        ]
        if any(values):
            return True
    return False


def _infer_table_name(columns):
    labels = {column.get("label", "") for column in columns}
    if {"原料名", "含量"} & labels and ("百分比" in labels or "规格" in labels):
        return "配方表"
    if "项目名称" in labels and ("标准" in labels or "结果" in labels):
        return "检测项目表"
    if "营养成分" in labels or "NRV%" in labels:
        return "营养成分表"
    if "原料" in labels or "原料名" in labels:
        return "原料表"
    return "智能识别表格"


def _column_for_header(cell_info):
    label = cell_info.get("value", "")
    return {
        "label": label,
        "field": HEADER_FIELDS.get(label, label),
        "target_col": get_column_letter(cell_info.get("col", 1)),
        "header_cell": cell_info.get("cell", ""),
    }


def infer_region_bounds(items, default_end_row=None):
    normalized_items = [item for item in items if isinstance(item, dict)]
    if not normalized_items:
        return {
            "start_row": None,
            "end_row": None,
            "start_col": None,
            "end_col": None,
        }

    rows = [int(item["row"]) for item in normalized_items if item.get("row") is not None]
    cols = [int(item["col"]) for item in normalized_items if item.get("col") is not None]
    if not rows or not cols:
        return {
            "start_row": None,
            "end_row": None,
            "start_col": None,
            "end_col": None,
        }

    return {
        "start_row": min(rows),
        "end_row": default_end_row if default_end_row is not None else max(rows),
        "start_col": min(cols),
        "end_col": max(cols),
    }


def _bounds_numbers(region):
    bounds = region.get("bounds", {}) if isinstance(region, dict) else {}
    try:
        start_row = int(bounds.get("start_row"))
        end_row = int(bounds.get("end_row"))
        start_col = int(bounds.get("start_col"))
        end_col = int(bounds.get("end_col"))
    except (TypeError, ValueError):
        return None

    if end_row < start_row or end_col < start_col:
        return None

    return start_row, end_row, start_col, end_col


def _region_area(region):
    numbers = _bounds_numbers(region)
    if not numbers:
        return 0
    start_row, end_row, start_col, end_col = numbers
    return (end_row - start_row + 1) * (end_col - start_col + 1)


def _region_rows_count(region):
    numbers = _bounds_numbers(region)
    if not numbers:
        return 0
    start_row, end_row, _, _ = numbers
    return end_row - start_row + 1


def _region_cols_count(region):
    numbers = _bounds_numbers(region)
    if not numbers:
        return 0
    _, _, start_col, end_col = numbers
    return end_col - start_col + 1


def _region_text(region):
    values = [
        str(region.get("name", "")),
        str(region.get("type", "")),
    ]
    labels = region.get("label_names")
    if isinstance(labels, list):
        values.extend(str(item) for item in labels)
    return " ".join(values)


def _candidate_type(score):
    if score >= 80:
        return "strong"
    if score >= 50:
        return "candidate"
    return "weak"


def _confidence(score):
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def classify_region_semantics(region):
    text = _region_text(region)
    for semantic_type, keywords in SEMANTIC_RULES:
        matched_keywords = [keyword for keyword in keywords if keyword in text]
        if matched_keywords:
            return {
                "semantic_type": semantic_type,
                "matched_keywords": matched_keywords,
            }
    return {
        "semantic_type": "unknown",
        "matched_keywords": [],
    }


def suggest_region_name(region):
    semantic_type = str(region.get("semantic_type") or "unknown")
    return SEMANTIC_NAMES.get(semantic_type, SEMANTIC_NAMES["unknown"])


def score_region(region):
    scored = dict(region) if isinstance(region, dict) else {}
    bounds = dict(scored.get("bounds", {})) if isinstance(scored.get("bounds", {}), dict) else {}
    scored["bounds"] = bounds

    score = 35
    reasons = []
    area = _region_area(scored)
    rows_count = _region_rows_count(scored)
    cols_count = _region_cols_count(scored)
    text = _region_text(scored)
    semantic = classify_region_semantics(scored)
    scored["semantic_type"] = semantic.get("semantic_type", "unknown")
    scored["matched_keywords"] = semantic.get("matched_keywords", [])
    scored["suggested_name"] = suggest_region_name(scored)

    if area <= 1:
        score -= 25
        reasons.append("区域过小")
    elif 4 <= area <= 60:
        score += 18
        reasons.append("区域面积合理")
    elif area > 160:
        score -= 30
        reasons.append("区域过大")
    elif area > 90:
        score -= 12
        reasons.append("区域偏大")

    matched_keywords = [keyword for keyword in SCORING_KEYWORDS if keyword in text]
    if matched_keywords:
        score += min(35, len(matched_keywords) * 8)
        reasons.append("命中高质量标题")

    if scored.get("semantic_type") != "unknown":
        score += 10
        reasons.append("语义分类明确")

    columns_count = int(scored.get("columns_count") or cols_count or 0)
    if columns_count >= 2:
        score += 12
        reasons.append("列结构有效")
    if rows_count >= 2:
        score += 10
        reasons.append("包含数据行")

    label_names = scored.get("label_names")
    if isinstance(label_names, list) and len(label_names) > 8:
        score -= 18
        reasons.append("覆盖标签过多")
    if scored.get("name") in {"智能识别表格", ""}:
        score -= 5
        reasons.append("名称较泛")

    score = max(0, min(100, score))
    confidence = _confidence(score)
    if scored.get("suggested_name") != SEMANTIC_NAMES["unknown"] and confidence == "low":
        confidence = "medium"
    scored["score"] = score
    scored["confidence"] = confidence
    scored["candidate_type"] = _candidate_type(score)
    scored["reason"] = "；".join(reasons) if reasons else "基础结构候选"
    return scored


def _intersection_area(first, second):
    first_bounds = _bounds_numbers(first)
    second_bounds = _bounds_numbers(second)
    if not first_bounds or not second_bounds:
        return 0

    first_start_row, first_end_row, first_start_col, first_end_col = first_bounds
    second_start_row, second_end_row, second_start_col, second_end_col = second_bounds
    row_overlap = min(first_end_row, second_end_row) - max(first_start_row, second_start_row) + 1
    col_overlap = min(first_end_col, second_end_col) - max(first_start_col, second_start_col) + 1
    if row_overlap <= 0 or col_overlap <= 0:
        return 0
    return row_overlap * col_overlap


def _overlap_ratio(first, second):
    intersection = _intersection_area(first, second)
    if intersection <= 0:
        return 0
    smaller_area = min(_region_area(first), _region_area(second))
    if smaller_area <= 0:
        return 0
    return intersection / smaller_area


def _region_key(region):
    bounds = region.get("bounds", {}) if isinstance(region, dict) else {}
    return (
        region.get("type", ""),
        region.get("name", ""),
        region.get("sheet", ""),
        bounds.get("start_row"),
        bounds.get("end_row"),
        bounds.get("start_col"),
        bounds.get("end_col"),
    )


def deduplicate_regions(regions):
    unique = {}
    for region in regions if isinstance(regions, list) else []:
        key = _region_key(region)
        current = unique.get(key)
        if current is None or region.get("score", 0) > current.get("score", 0):
            unique[key] = region

    sorted_regions = sorted(
        unique.values(),
        key=lambda item: (
            item.get("score", 0),
            -_region_area(item),
            item.get("type", ""),
        ),
        reverse=True,
    )

    kept = []
    for region in sorted_regions:
        should_keep = True
        for kept_region in kept:
            if region.get("sheet") != kept_region.get("sheet"):
                continue
            if region.get("type") != kept_region.get("type"):
                continue
            if _overlap_ratio(region, kept_region) > 0.7:
                should_keep = False
                break
        if should_keep:
            kept.append(region)

    return sorted(
        kept,
        key=lambda item: (
            item.get("bounds", {}).get("start_row") or 0,
            item.get("bounds", {}).get("start_col") or 0,
            -item.get("score", 0),
        ),
    )


def _infer_table_end_row(sheet, header_row, start_col, end_col):
    end_row = header_row
    blank_streak = 0
    for row_number in range(header_row + 1, sheet.max_row + 1):
        row_has_value = any(
            _cell_value(sheet.cell(row=row_number, column=col))
            for col in range(start_col, end_col + 1)
        )
        if row_has_value:
            end_row = row_number
            blank_streak = 0
            continue
        blank_streak += 1
        if blank_streak >= 2:
            break
    return end_row


def infer_header_row(sheet, row_number):
    row_cells = _row_text_cells(sheet, row_number)
    candidates = []
    for run in _contiguous_runs(row_cells):
        if len(run) < 2:
            continue
        keyword_count = sum(1 for cell in run if cell.get("value") in HEADER_FIELDS)
        start_col = run[0]["col"]
        end_col = run[-1]["col"]
        has_data_below = _has_data_below(sheet, row_number, start_col, end_col)
        if keyword_count == 0 and (len(run) < 3 or not has_data_below):
            continue

        columns = [_column_for_header(cell) for cell in run]
        candidates.append(
            {
                "header_row": row_number,
                "columns": columns,
                "start_col": start_col,
                "end_col": end_col,
                "score": keyword_count * 2 + len(run) + (1 if has_data_below else 0),
                "has_data_below": has_data_below,
            }
        )

    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[0]


def scan_table_regions(template_path):
    workbook = _load_workbook(template_path)
    try:
        table_regions = []
        for sheet in workbook.worksheets:
            for row_number in range(1, sheet.max_row + 1):
                header = infer_header_row(sheet, row_number)
                if not header:
                    continue

                end_row = _infer_table_end_row(
                    sheet,
                    header["header_row"],
                    header["start_col"],
                    header["end_col"],
                )
                bounds = infer_region_bounds(
                    [
                        {"row": header["header_row"], "col": header["start_col"]},
                        {"row": end_row, "col": header["end_col"]},
                    ],
                    default_end_row=end_row,
                )
                columns = header.get("columns", [])
                table_regions.append(
                    {
                        "sheet": sheet.title,
                        "table_key": f"smart_table_{len(table_regions) + 1}",
                        "table_name": _infer_table_name(columns),
                        "header_row": header["header_row"],
                        "start_cell": columns[0]["header_cell"] if columns else "",
                        "columns": columns,
                        "bounds": bounds,
                        "detection": {
                            "method": "smart_header_row",
                            "score": header.get("score", 0),
                            "has_data_below": header.get("has_data_below", False),
                        },
                    }
                )
        return table_regions
    finally:
        workbook.close()


def _infer_block_end_row(sheet, start_row, start_col):
    end_row = start_row
    blank_streak = 0
    for row_number in range(start_row + 1, min(sheet.max_row, start_row + 12) + 1):
        row_texts = [
            _cell_value(sheet.cell(row=row_number, column=col))
            for col in range(start_col, min(sheet.max_column, start_col + 3) + 1)
        ]
        if any(row_texts):
            end_row = row_number
            blank_streak = 0
            continue
        blank_streak += 1
        if blank_streak >= 2:
            break
    return end_row


def scan_block_regions(template_path):
    workbook = _load_workbook(template_path)
    try:
        block_regions = []
        for sheet in workbook.worksheets:
            block_labels = []
            for row_number in range(1, sheet.max_row + 1):
                for cell in sheet[row_number]:
                    value = _clean_text(cell.value)
                    if value in BLOCK_KEYWORDS:
                        block_labels.append(
                            {
                                "sheet": sheet.title,
                                "row": cell.row,
                                "col": cell.column,
                                "cell": cell.coordinate,
                                "value": value,
                            }
                        )

            clusters = []
            current = []
            for label in block_labels:
                if not current:
                    current = [label]
                    continue
                same_area = label["col"] == current[-1]["col"] and label["row"] <= current[-1]["row"] + 4
                if same_area:
                    current.append(label)
                else:
                    clusters.append(current)
                    current = [label]
            if current:
                clusters.append(current)

            for cluster in clusters:
                start = cluster[0]
                end_row = max(_infer_block_end_row(sheet, item["row"], item["col"]) for item in cluster)
                bounds = infer_region_bounds(
                    [
                        {"row": start["row"], "col": start["col"]},
                        {"row": end_row, "col": min(sheet.max_column, start["col"] + 3)},
                    ],
                    default_end_row=end_row,
                )
                block_regions.append(
                    {
                        "sheet": sheet.title,
                        "block_name": " / ".join(item["value"] for item in cluster),
                        "source_cell": start["cell"],
                        "target_cell": start["cell"],
                        "labels": [item["value"] for item in cluster],
                        "bounds": bounds,
                        "detection": {
                            "method": "smart_text_cluster",
                            "label_count": len(cluster),
                        },
                    }
                )
        return block_regions
    finally:
        workbook.close()


def build_template_structure(labels, table_regions, block_regions):
    label_regions = []
    for label in labels:
        cell = str(label.get("cell", ""))
        row_digits = "".join(ch for ch in cell if ch.isdigit())
        col_letters = "".join(ch for ch in cell if ch.isalpha())
        col_number = column_index_from_string(col_letters) if col_letters else None
        label_regions.append(
            {
                "type": "label",
                "name": label.get("value", ""),
                "sheet": label.get("sheet", ""),
                "cell": cell,
                "bounds": {
                    "start_row": int(row_digits) if row_digits else None,
                    "end_row": int(row_digits) if row_digits else None,
                    "start_col": col_number,
                    "end_col": col_number,
                },
            }
        )

    table_nodes = [
        {
            "type": "table",
            "name": item.get("table_name", ""),
            "sheet": item.get("sheet", ""),
            "bounds": item.get("bounds", {}),
            "columns_count": len(item.get("columns", [])) if isinstance(item.get("columns"), list) else 0,
            "rows_count": _region_rows_count(item),
            "label_names": [
                column.get("label", "")
                for column in item.get("columns", [])
                if isinstance(column, dict) and column.get("label")
            ]
        }
        for item in table_regions
    ]
    block_nodes = [
        {
            "type": "block",
            "name": item.get("block_name", ""),
            "sheet": item.get("sheet", ""),
            "bounds": item.get("bounds", {}),
            "labels_count": len(item.get("labels", [])) if isinstance(item.get("labels"), list) else 0,
            "rows_count": _region_rows_count(item),
            "label_names": item.get("labels", []) if isinstance(item.get("labels", []), list) else [],
        }
        for item in block_regions
    ]
    raw_regions = [score_region(region) for region in table_nodes + block_nodes]
    deduped_regions = deduplicate_regions(raw_regions)
    recommended_regions = [
        region
        for region in sorted(deduped_regions, key=lambda item: item.get("score", 0), reverse=True)
        if region.get("candidate_type") in {"strong", "candidate"}
    ][:10]
    recommended_regions = sorted(
        recommended_regions,
        key=lambda item: (
            item.get("bounds", {}).get("start_row") or 0,
            item.get("bounds", {}).get("start_col") or 0,
            -item.get("score", 0),
        ),
    )

    return {
        "regions": recommended_regions,
        "raw_regions": raw_regions,
        "deduped_regions": deduped_regions,
        "recommended_regions": recommended_regions,
        "tables": [region for region in recommended_regions if region.get("type") == "table"],
        "blocks": [region for region in recommended_regions if region.get("type") == "block"],
        "labels": label_regions,
    }


def analyze_template(template_path):
    labels = scan_excel_labels(template_path)
    structured_mapping_preview = infer_structured_mapping_from_labels(labels)
    table_regions = scan_table_regions(template_path)
    block_regions = scan_block_regions(template_path)
    template_structure = build_template_structure(labels, table_regions, block_regions)
    analysis = {
        "success": True,
        "labels": labels,
        "structured_mapping_preview": structured_mapping_preview,
        "table_regions": table_regions,
        "block_regions": block_regions,
        "template_structure": template_structure,
        "summary": {
            "labels_count": len(labels),
            "structured_mapping_count": len(structured_mapping_preview),
            "table_regions_count": len(table_regions),
            "block_regions_count": len(block_regions),
            "structure_regions_count": len(template_structure.get("regions", [])),
            "raw_regions_count": len(template_structure.get("raw_regions", [])),
            "deduped_regions_count": len(template_structure.get("deduped_regions", [])),
            "recommended_regions_count": len(template_structure.get("recommended_regions", [])),
        },
    }
    analysis["auto_mapping_preview"] = generate_auto_mapping(analysis)

    return analysis
