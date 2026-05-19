from html import escape


def _as_list(value):
    return value if isinstance(value, list) else []


def _column_index(column):
    total = 0
    for char in str(column or "").upper():
        if "A" <= char <= "Z":
            total = total * 26 + (ord(char) - 64)
    return total


def _preview_value(value):
    if isinstance(value, dict):
        return value.get("value", "")
    return value


def _preview_status(value):
    if not isinstance(value, dict):
        return ""
    labels = []
    if value.get("skipped"):
        labels.append("skipped")
    if value.get("conflict"):
        labels.append("conflict")
    if value.get("overwrite_warning"):
        labels.append("overwrite_warning")
    return ", ".join(labels)


def _render_cell_preview(items):
    empty_row = '<tr><td colspan="8">暂无 Cell Preview</td></tr>'
    rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('cell') or ''))}</td>"
        f"<td>{escape(str(item.get('display_cell') or item.get('cell') or ''))}</td>"
        f"<td>{escape(str(item.get('merged_range') or ''))}</td>"
        f"<td>{escape(str(item.get('source') or ''))}</td>"
        f"<td>{escape(str(item.get('operation_type') or item.get('op_type') or ''))}</td>"
        f"<td>{escape(str(item.get('value') or ''))}</td>"
        f"<td>{escape(str(item.get('display_note') or ''))}</td>"
        f"<td>{escape(_preview_status(item))}</td>"
        "</tr>"
        for item in _as_list(items)
        if isinstance(item, dict)
    )
    return (
        "<section><h2>Cell Preview</h2>"
        "<table><thead><tr><th>cell</th><th>display_cell</th><th>merged_range</th><th>source</th><th>op_type</th><th>value</th><th>display_note</th><th>safety</th></tr></thead>"
        f"<tbody>{rows or empty_row}</tbody></table></section>"
    )


def _render_table_preview(tables):
    sections = []
    for table in _as_list(tables):
        if not isinstance(table, dict):
            continue
        rows = _as_list(table.get("rows"))
        columns = sorted(
            {
                column
                for row in rows
                if isinstance(row, dict)
                for column in (row.get("cells", {}) if isinstance(row.get("cells"), dict) else {})
            },
            key=_column_index,
        )
        header = "".join(f"<th>{escape(str(column))}</th>" for column in columns)
        body = "".join(
            "<tr>"
            f"<td>{escape(str(row.get('row_number') or ''))}</td>"
            + "".join(_render_table_cell((row.get("cells") or {}).get(column, "")) for column in columns)
            + "</tr>"
            for row in rows
            if isinstance(row, dict)
        )
        sections.append(
            f"<section><h2>{escape(str(table.get('table_name') or '未命名表格'))}</h2>"
            "<table><thead><tr><th>row_number</th>"
            f"{header}</tr></thead><tbody>{body or '<tr><td>暂无表格数据</td></tr>'}</tbody></table></section>"
        )
    return "".join(sections) or "<section><h2>Table Preview</h2><p>暂无 Table Preview</p></section>"


def _render_table_cell(value):
    status = _preview_status(value)
    suffix = f" · {escape(status)}" if status else ""
    if isinstance(value, dict):
        display_note = str(value.get("display_note") or "")
        merged_range = str(value.get("merged_range") or "")
        note_html = f"<div>{escape(display_note)}</div>" if display_note else ""
        merged_html = f"<div>merged: {escape(merged_range)}</div>" if merged_range else ""
        return f"<td>{escape(str(_preview_value(value) or ''))}{note_html}{merged_html}{suffix}</td>"
    return f"<td>{escape(str(_preview_value(value) or ''))}{suffix}</td>"


def _render_block_preview(blocks):
    body = "".join(
        "<article class=\"block-preview\">"
        f"<h3>{escape(str(block.get('block_name') or '未命名区块'))} · {escape(str(block.get('target_cell') or ''))}</h3>"
        f"<pre>{escape(str(block.get('value') or ''))}</pre>"
        "</article>"
        for block in _as_list(blocks)
        if isinstance(block, dict)
    )
    return f"<section><h2>Block Preview</h2>{body or '<p>暂无 Block Preview</p>'}</section>"


def render_preview_to_html(render_preview):
    render_preview = render_preview if isinstance(render_preview, dict) else {}
    html = (
        "<div class=\"v4-render-preview\">"
        f"{_render_cell_preview(render_preview.get('cells') or render_preview.get('cell_preview', []))}"
        f"{_render_table_preview(render_preview.get('table_preview', []))}"
        f"{_render_block_preview(render_preview.get('block_preview', []))}"
        "</div>"
    )
    return {
        "success": True,
        "html": html,
    }
