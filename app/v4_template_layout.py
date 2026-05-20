from copy import deepcopy


SECTION_MAP = {
    "document_info": {
        "section_key": "document_info",
        "title": "文档编号信息",
        "section_type": "structured",
        "order": 10,
    },
    "customer_info": {
        "section_key": "customer_info",
        "title": "客户信息确认",
        "section_type": "structured",
        "order": 20,
    },
    "product_detail": {
        "section_key": "product_detail",
        "title": "产品规格确认",
        "section_type": "structured",
        "order": 30,
    },
    "formula": {
        "section_key": "formula",
        "title": "配方信息确认",
        "section_type": "table",
        "order": 40,
    },
    "packaging": {
        "section_key": "packaging",
        "title": "包装要求确认",
        "section_type": "block",
        "order": 50,
    },
    "label_requirement": {
        "section_key": "label_requirement",
        "title": "标签要求确认",
        "section_type": "block",
        "order": 60,
    },
    "production_batch": {
        "section_key": "production_batch",
        "title": "生产日期批号确认",
        "section_type": "block",
        "order": 70,
    },
}

DEFAULT_SECTION = {
    "section_key": "other",
    "title": "其他字段确认",
    "section_type": "other",
    "order": 900,
}


def _safe_dict(value):
    return value if isinstance(value, dict) else {}


def _safe_list(value):
    return value if isinstance(value, list) else []


def _region_bounds(region):
    region = _safe_dict(region)
    bounds = deepcopy(_safe_dict(region.get("bounds")))
    for key in ("start_row", "end_row", "start_col", "end_col"):
        if key not in bounds and key in region:
            bounds[key] = region.get(key)
    return bounds


def _sort_key(section):
    bounds = _safe_dict(section.get("bounds"))
    return (
        section.get("order", 900),
        int(bounds.get("start_row") or 0),
        int(bounds.get("start_col") or 0),
    )


def _section_template_for_region(region):
    semantic_type = str(_safe_dict(region).get("semantic_type") or "unknown")
    return deepcopy(SECTION_MAP.get(semantic_type, DEFAULT_SECTION))


def _dedupe_section_keys(sections):
    counts = {}
    result = []
    for section in sections:
        base_key = section.get("section_key") or "other"
        counts[base_key] = counts.get(base_key, 0) + 1
        if counts[base_key] > 1:
            section = deepcopy(section)
            section["section_key"] = f"{base_key}_{counts[base_key]}"
            section["title"] = f"{section.get('title') or DEFAULT_SECTION['title']} {counts[base_key]}"
        result.append(section)
    return result


def build_layout_sections_from_template_analysis(template_analysis):
    analysis = _safe_dict(template_analysis)
    template_structure = _safe_dict(analysis.get("template_structure"))
    regions = _safe_list(template_structure.get("recommended_regions"))
    if not regions:
        regions = _safe_list(template_structure.get("regions"))

    layout_sections = []
    for region in regions:
        if not isinstance(region, dict):
            continue
        section = _section_template_for_region(region)
        section.update(
            {
                "bounds": _region_bounds(region),
                "semantic_type": str(region.get("semantic_type") or "unknown"),
                "matched_keywords": _safe_list(region.get("matched_keywords")),
                "confidence": region.get("confidence"),
                "score": region.get("score"),
                "source_region_name": region.get("region_name")
                or region.get("name")
                or region.get("title")
                or "",
                "source": "template_structure",
                "items": [],
            }
        )
        layout_sections.append(section)

    layout_sections.sort(key=_sort_key)
    layout_sections = _dedupe_section_keys(layout_sections)

    return {
        "success": True,
        "layout_sections": layout_sections,
        "summary": {
            "sections_count": len(layout_sections),
            "source_regions_count": len(regions),
        },
    }
