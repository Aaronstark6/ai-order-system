import re


AM_PM = r"(?:\u4e0a\u5348|\u4e0b\u5348)"
TIME_LINE_RE = re.compile(
    rf"^(?:{AM_PM})?\s*\d{{1,2}}:\d{{2}}(?::\d{{2}})?$",
    re.IGNORECASE,
)
DATE_TIME_LINE_RES = [
    re.compile(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"),
    re.compile(r"^\d{4}\u5e74\d{1,2}\u6708\d{1,2}\u65e5(?:\s+\d{1,2}:\d{2}(?::\d{2})?)?$"),
    re.compile(r"^\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?$"),
]
NICKNAME_PREFIX_RE = re.compile(
    r"^[A-Za-z\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff]{0,24}\s*[:\uff1a]\s*"
)
RECALL_LINE_RE = re.compile(r"^(?:\u4f60|\u5bf9\u65b9|.+?)?\u64a4\u56de\u4e86\u4e00\u6761\u6d88\u606f$")
BRACKET_SYSTEM_LINE_RE = re.compile(
    r"^\[(?:\u56fe\u7247|\u6587\u4ef6|\u8bed\u97f3|\u89c6\u9891|\u8868\u60c5)\]$"
)
STANDALONE_SYSTEM_WORDS = {
    "\u56fe\u7247",
    "\u6587\u4ef6",
    "\u8bed\u97f3",
    "\u89c6\u9891",
    "\u8868\u60c5",
    "\u5df2\u8bfb",
    "\u672a\u8bfb",
}


def _normalize_line(line):
    return re.sub(r"[ \t]+", " ", str(line or "").strip())


def _strip_nickname_prefix(line):
    text = str(line or "").strip()
    previous = None
    while text and text != previous:
        previous = text
        text = NICKNAME_PREFIX_RE.sub("", text, count=1).strip()
    return text


def _is_time_line(line):
    return bool(TIME_LINE_RE.match(line))


def _is_date_time_line(line):
    return any(pattern.match(line) for pattern in DATE_TIME_LINE_RES)


def _is_system_line(line):
    if not line:
        return False
    if RECALL_LINE_RE.match(line):
        return True
    if BRACKET_SYSTEM_LINE_RE.match(line):
        return True
    return line in STANDALONE_SYSTEM_WORDS


def _append_clean_line(lines, line):
    if not line:
        if lines and lines[-1] != "":
            lines.append("")
        return
    lines.append(line)


def preprocess_chat_text(text: str) -> dict:
    raw_text = "" if text is None else str(text)
    raw_lines = raw_text.splitlines()
    clean_lines = []
    removed_lines = []

    for raw_line in raw_lines:
        line = _normalize_line(raw_line)
        if not line:
            _append_clean_line(clean_lines, "")
            continue

        if _is_time_line(line) or _is_date_time_line(line):
            removed_lines.append(raw_line)
            continue

        without_prefix = _strip_nickname_prefix(line)
        if not without_prefix:
            removed_lines.append(raw_line)
            continue

        if _is_system_line(without_prefix):
            removed_lines.append(raw_line)
            continue

        _append_clean_line(clean_lines, without_prefix)

    while clean_lines and clean_lines[0] == "":
        clean_lines.pop(0)
    while clean_lines and clean_lines[-1] == "":
        clean_lines.pop()

    clean_text = "\n".join(clean_lines)
    return {
        "raw_text": raw_text,
        "clean_text": clean_text,
        "removed_lines": removed_lines,
        "stats": {
            "raw_lines": len(raw_lines),
            "clean_lines": len(clean_lines),
            "removed_lines": max(0, len(raw_lines) - len(clean_lines)),
        },
    }
