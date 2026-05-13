import re


FORMULA_FIELD_PRIORITY = ("配方要求", "配方", "Formula", "Ingredients")
IGNORED_LINE_KEYWORDS = (
    "serving size",
    "servings per container",
    "other ingredients",
    "suggested use",
    "warning",
)
IGNORED_PREFIX_WORDS = {
    "organic",
    "pure",
    "natural",
    "extract",
    "standardized",
    "standardised",
    "total",
}
AMOUNT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(mg|mcg|μg|ug|g|ml|iu)\b", re.IGNORECASE)
SOURCE_MARK_RE = re.compile(r"\[(模板|AI|系统|人工)\]")


def get_formula_text_from_description_fields(description_fields):
    if not isinstance(description_fields, dict):
        return ""

    for key in FORMULA_FIELD_PRIORITY:
        value = description_fields.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def _contains_chinese(text):
    return bool(re.search(r"[\u4e00-\u9fff]", str(text or "")))


def _normalize_amount(value, unit):
    amount = float(value)
    unit_text = str(unit or "").lower()
    if unit_text == "g":
        return amount * 1000
    if unit_text == "mg":
        return amount
    if unit_text in {"mcg", "μg", "ug"}:
        return amount / 1000
    return amount


def _strip_field_prefix(line):
    text = SOURCE_MARK_RE.sub("", str(line or "")).strip()
    for sep in ("：", ":"):
        if sep in text:
            prefix, value = text.split(sep, 1)
            if prefix.strip() in FORMULA_FIELD_PRIORITY:
                return value.strip()
    return text


def _is_non_ingredient_line(line):
    text = str(line or "").strip().lower()
    if not text:
        return True
    if any(keyword in text for keyword in IGNORED_LINE_KEYWORDS):
        return True
    return text.startswith(("total ", "total:"))


def _ingredient_name_from_line(line, amount_match):
    text = _strip_field_prefix(line)
    if amount_match.start() <= 1:
        name = text[amount_match.end():].strip()
    else:
        name = text[:amount_match.start()].strip()

    name = re.sub(r"^[\s,;:/\-–—]+|[\s,;:/\-–—]+$", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _ingredient_initial(name):
    text = str(name or "").strip()
    while True:
        match = re.match(r"^([A-Za-z][A-Za-z'-]*)\b", text)
        if not match:
            return ""
        word = match.group(1).strip("-'").lower()
        if word not in IGNORED_PREFIX_WORDS:
            return word[0].upper()
        text = text[match.end():].strip()


def extract_ingredient_initials_from_formula_text(formula_text):
    ingredients = []
    for index, raw_line in enumerate(str(formula_text or "").splitlines()):
        line = _strip_field_prefix(raw_line)
        if _contains_chinese(line) or _is_non_ingredient_line(line):
            continue

        matches = list(AMOUNT_RE.finditer(line))
        if not matches:
            continue

        amount_match = matches[-1]
        name = _ingredient_name_from_line(line, amount_match)
        initial = _ingredient_initial(name)
        if not initial:
            continue

        amount = _normalize_amount(amount_match.group(1), amount_match.group(2))
        ingredients.append((amount, index, initial))

    top_three = sorted(ingredients, key=lambda item: (-item[0], item[1]))[:3]
    return "".join(sorted(initial for _, _, initial in top_three))


def extract_ingredient_initials_from_description_fields(description_fields):
    return extract_ingredient_initials_from_formula_text(
        get_formula_text_from_description_fields(description_fields)
    )
