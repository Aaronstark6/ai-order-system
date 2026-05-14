import re


FORMULA_FIELD_PRIORITY = ("配方要求", "配方", "Formula", "Ingredients")
IGNORED_LINE_KEYWORDS = (
    "serving size",
    "servings per container",
    "other ingredients",
    "suggested use",
    "warning",
    "storage",
    "directions",
    "product name",
    "product code",
    "we use this formula",
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
NO_FORMULA_MESSAGE = "未识别到配方信息，请人工填写产品成分缩写。"
NO_AMOUNT_MESSAGE = "未识别到有效成分含量，请人工填写产品成分缩写。"

AMOUNT_RE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(mcg|μg|ug|mg|g|ml|iu)\b",
    re.IGNORECASE,
)
SOURCE_MARK_RE = re.compile(r"\[(模板|AI|系统|人工)\]")
FIELD_PREFIX_RE = re.compile(
    r"^\s*(?:配方要求|配方|Formula|Ingredients)\s*[:：]\s*",
    re.IGNORECASE,
)
ENGLISH_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


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
    return FIELD_PREFIX_RE.sub("", text).strip()


def _is_non_ingredient_line(line):
    text = str(line or "").strip().lower()
    if not text:
        return True
    if any(keyword in text for keyword in IGNORED_LINE_KEYWORDS):
        return True
    return text.startswith(("total ", "total:"))


def _looks_like_english_ingredient_line(line):
    text = _strip_field_prefix(line)
    if _contains_chinese(text) or _is_non_ingredient_line(text):
        return False
    words = ENGLISH_WORD_RE.findall(text)
    if not words:
        return False
    if not AMOUNT_RE.search(text):
        if len(words) > 4 or re.search(r"[.!?。！？]", text):
            return False
        if words[0].lower() in {"we", "this", "please", "use", "with", "for"}:
            return False
    first_word = words[0].lower().strip("-'")
    if first_word in IGNORED_PREFIX_WORDS and len(words) == 1:
        return False
    return True


def _ingredient_name_from_line(line, amount_match):
    text = _strip_field_prefix(line)
    name = text[:amount_match.start()].strip()
    name = re.sub(r"[\s,;:/\-–—+|([]+$", "", name)
    name = re.sub(r"^[\s,;:/\-–—+|([]+", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _ingredient_initial(name):
    text = str(name or "").strip()
    for match in ENGLISH_WORD_RE.finditer(text):
        word = match.group(0).strip("-'").lower()
        if word and word not in IGNORED_PREFIX_WORDS:
            return word[0].upper()
    return ""


def _extract_ingredients_from_formula_text(formula_text):
    ingredients = []
    candidate_count = 0

    for index, raw_line in enumerate(str(formula_text or "").splitlines()):
        line = _strip_field_prefix(raw_line)
        if not _looks_like_english_ingredient_line(line):
            continue

        candidate_count += 1
        matches = list(AMOUNT_RE.finditer(line))
        if not matches:
            continue

        amount_match = matches[-1]
        name = _ingredient_name_from_line(line, amount_match)
        initial = _ingredient_initial(name)
        if not initial:
            continue

        amount = _normalize_amount(amount_match.group(1), amount_match.group(2))
        ingredients.append(
            {
                "amount": amount,
                "index": index,
                "initial": initial,
                "name": name,
            }
        )

    return ingredients, candidate_count


def _build_initials(ingredients):
    top_items = sorted(
        ingredients,
        key=lambda item: (-item["amount"], item["index"]),
    )[:3]
    return "".join(sorted(item["initial"] for item in top_items))


def _analyze_formula_text(formula_text, has_formula):
    text = str(formula_text or "").strip()
    if not text:
        return {
            "initials": "",
            "status": "no_formula" if has_formula else "empty",
            "message": NO_FORMULA_MESSAGE,
            "ingredients_count": 0,
            "used_count": 0,
        }

    ingredients, candidate_count = _extract_ingredients_from_formula_text(text)
    if ingredients:
        initials = _build_initials(ingredients)
        return {
            "initials": initials,
            "status": "ok",
            "message": "",
            "ingredients_count": len(ingredients),
            "used_count": min(len(ingredients), 3),
        }

    if candidate_count:
        return {
            "initials": "",
            "status": "no_amount",
            "message": NO_AMOUNT_MESSAGE,
            "ingredients_count": candidate_count,
            "used_count": 0,
        }

    return {
        "initials": "",
        "status": "no_formula",
        "message": NO_FORMULA_MESSAGE,
        "ingredients_count": 0,
        "used_count": 0,
    }


def extract_ingredient_initials_from_formula_text(formula_text):
    return _analyze_formula_text(formula_text, has_formula=bool(str(formula_text or "").strip()))[
        "initials"
    ]


def extract_ingredient_initials_from_description_fields(description_fields):
    return extract_ingredient_initials_from_formula_text(
        get_formula_text_from_description_fields(description_fields)
    )


def extract_ingredient_initials_from_text(text):
    return extract_ingredient_initials_from_formula_text(text)


def analyze_ingredient_initials_source(description_fields=None, text=None):
    formula_text = get_formula_text_from_description_fields(description_fields)
    if formula_text:
        field_analysis = _analyze_formula_text(formula_text, has_formula=True)
        if field_analysis["status"] == "ok" or not str(text or "").strip():
            return field_analysis

        text_analysis = _analyze_formula_text(text, has_formula=True)
        if text_analysis["status"] == "ok":
            return text_analysis
        return field_analysis

    if str(text or "").strip():
        return _analyze_formula_text(text, has_formula=False)

    return {
        "initials": "",
        "status": "empty",
        "message": NO_FORMULA_MESSAGE,
        "ingredients_count": 0,
        "used_count": 0,
    }
