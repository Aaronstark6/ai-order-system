from app.v4_template_intelligence import infer_structured_mapping_from_labels
from app.v4_template_scanner import scan_block_regions, scan_excel_labels, scan_table_regions


def analyze_template(template_path):
    labels = scan_excel_labels(template_path)
    structured_mapping_preview = infer_structured_mapping_from_labels(labels)
    table_regions = scan_table_regions(template_path)
    block_regions = scan_block_regions(template_path)

    return {
        "success": True,
        "labels": labels,
        "structured_mapping_preview": structured_mapping_preview,
        "table_regions": table_regions,
        "block_regions": block_regions,
        "summary": {
            "labels_count": len(labels),
            "structured_mapping_count": len(structured_mapping_preview),
            "table_regions_count": len(table_regions),
            "block_regions_count": len(block_regions),
        },
    }
