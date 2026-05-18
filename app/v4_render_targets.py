from collections import OrderedDict
from html import escape


def _as_list(value):
    return value if isinstance(value, list) else []


def _text(value):
    return "" if value is None else str(value)


def _operation_label(operation):
    for key in ("label", "field", "source_path", "target_cell"):
        value = str(operation.get(key) or "").strip()
        if value:
            return value
    return "未命名字段"


def _render_structured(operations):
    if not operations:
        return ""

    cards = []
    for operation in operations:
        label = escape(_operation_label(operation))
        value = escape(_text(operation.get("value")))
        target_cell = escape(str(operation.get("target_cell") or ""))
        cards.append(
            f"""
            <article class="field-card">
                <div class="field-label">{label}</div>
                <div class="field-meta">target_cell: {target_cell}</div>
                <div class="field-value">{value or "&nbsp;"}</div>
            </article>
            """
        )

    return f"""
    <section class="render-section">
        <h2>结构化字段</h2>
        <div class="field-grid">
            {"".join(cards)}
        </div>
    </section>
    """


def _group_table_operations(operations):
    grouped = OrderedDict()
    for operation in operations:
        table_name = str(operation.get("table_name") or "未命名表格").strip()
        grouped.setdefault(table_name, []).append(operation)
    return grouped


def _render_tables(operations):
    if not operations:
        return ""

    sections = []
    for table_name, items in _group_table_operations(operations).items():
        rows = []
        for operation in items:
            target_cell = escape(str(operation.get("target_cell") or ""))
            value = escape(_text(operation.get("value")))
            rows.append(
                f"""
                <tr>
                    <td>{target_cell}</td>
                    <td>{value or "&nbsp;"}</td>
                </tr>
                """
            )
        sections.append(
            f"""
            <div class="table-block">
                <h3>{escape(table_name)}</h3>
                <table>
                    <thead>
                        <tr>
                            <th>目标单元格</th>
                            <th>内容</th>
                        </tr>
                    </thead>
                    <tbody>
                        {"".join(rows)}
                    </tbody>
                </table>
            </div>
            """
        )

    return f"""
    <section class="render-section">
        <h2>动态表格</h2>
        {"".join(sections)}
    </section>
    """


def _render_blocks(operations):
    if not operations:
        return ""

    blocks = []
    for operation in operations:
        block_name = escape(str(operation.get("block_name") or operation.get("target_cell") or "文本块"))
        value = escape(_text(operation.get("value")))
        target_cell = escape(str(operation.get("target_cell") or ""))
        blocks.append(
            f"""
            <article class="text-block">
                <div class="block-title">{block_name}</div>
                <div class="field-meta">target_cell: {target_cell}</div>
                <pre>{value}</pre>
            </article>
            """
        )

    return f"""
    <section class="render-section">
        <h2>区块文本</h2>
        {"".join(blocks)}
    </section>
    """


def render_processed_operations_to_html(processed_operations):
    operations = _as_list(processed_operations)
    structured = []
    tables = []
    blocks = []

    for operation in operations:
        if not isinstance(operation, dict):
            continue
        op_type = str(operation.get("op_type") or "").strip()
        source = str(operation.get("source") or "").strip()
        if op_type == "write_table_cell" or source == "table":
            tables.append(operation)
        elif op_type == "write_block" or source == "block":
            blocks.append(operation)
        elif op_type == "write_text" or source == "structured":
            structured.append(operation)

    html = f"""
    <div class="v4-render-target">
        {_render_structured(structured)}
        {_render_tables(tables)}
        {_render_blocks(blocks)}
        {'' if operations else '<div class="empty-preview">暂无 Processed Operations</div>'}
    </div>
    """

    return {
        "success": True,
        "html": html,
    }


def render_unified_operations_to_html(unified_operations):
    return render_processed_operations_to_html(unified_operations)
