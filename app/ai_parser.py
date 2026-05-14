import json
import os
import re

import requests
from dotenv import load_dotenv

from app.app_settings import get_deepseek_api_key
from app.field_library import load_fields
from app.ingredient_parser import analyze_ingredient_initials_source


load_dotenv()

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
SOURCE_MARK_RE = re.compile(r"\[(模板|AI|系统|人工)\]")


def format_compact_date(value):
    text = str(value or "").strip()
    if not text:
        return ""

    digits = re.sub(r"\D", "", text)
    if len(digits) == 8:
        return digits
    return ""


def _normalize_date_fields(data: dict):
    if not isinstance(data, dict):
        return

    for key, value in list(data.items()):
        key_text = str(key or "").lower()
        if key_text.endswith("_date") or key_text in {"date", "order_date"}:
            compact = format_compact_date(value)
            if compact:
                data[key] = compact


def _line_without_source_mark(line: str):
    return SOURCE_MARK_RE.sub("", str(line or "")).strip()


def _insert_source_mark(line: str, source: str):
    text = SOURCE_MARK_RE.sub("", str(line or ""))
    marker = f"[{source}]"
    for sep in ("：", ":"):
        if sep in text:
            prefix, value = text.split(sep, 1)
            return f"{prefix}{sep}{marker} {value.strip()}"
    return f"{marker} {text.strip()}" if text.strip() else ""


def annotate_description_sources(template_text: str, description_text: str):
    template_lines = str(template_text or "").splitlines()
    description_lines = str(description_text or "").splitlines()
    result = []

    for index, line in enumerate(description_lines):
        if not str(line or "").strip():
            result.append(line)
            continue

        template_line = template_lines[index] if index < len(template_lines) else ""
        source = "模板" if _line_without_source_mark(line) == _line_without_source_mark(template_line) else "AI"
        result.append(_insert_source_mark(line, source))

    return "\n".join(result)


def build_prompt(message: str):
    fields = load_fields()

    field_lines = []
    field_keys = []

    for field in fields:
        key = field.get("key", "")
        label = field.get("label", key)
        description = field.get("description", "")

        if not key:
            continue

        field_keys.append(key)
        field_lines.append(f"{key}（{label}）：{description}")

    prompt = f"""
你是一个外贸订单信息提取助手。

请从下面的客户聊天内容中提取订单信息，并返回 JSON。

【字段说明】
{chr(10).join(field_lines)}

【返回要求】
1. 只返回 JSON，不要解释
2. JSON 字段必须使用这些 key：
{field_keys}
3. 没有识别到的字段，值填 null
4. 不要返回 markdown，不要使用 ```json

【客户聊天内容】
{message}
"""

    return prompt, field_keys


def parse_message(message: str):
    api_key = get_deepseek_api_key()
    if not api_key:
        return {
            "error": "没有读取到 DeepSeek API Key，请在配置中心 AI 设置或 .env 中配置"
        }

    prompt, field_keys = build_prompt(message)

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0
        },
        timeout=60
    )

    if response.status_code != 200:
        return {
            "error": "DeepSeek请求失败",
            "status_code": response.status_code,
            "detail": response.text
        }

    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    if content.startswith("```json"):
        content = content.replace("```json", "").replace("```", "").strip()
    elif content.startswith("```"):
        content = content.replace("```", "").strip()

    try:
        parsed = json.loads(content)
    except Exception:
        return {
            "error": "AI返回内容不是标准JSON",
            "raw": content
        }

    for key in field_keys:
        if key not in parsed:
            parsed[key] = None

    _normalize_date_fields(parsed)

    return parsed


def _line_key(line: str):
    text = str(line or "")
    for sep in ("：", ":"):
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return ""


FORMULA_FIELD_KEYS = ("配方", "配方要求", "Formula", "Ingredients")


def _is_formula_key(key: str):
    key_text = str(key or "").strip()
    return key_text in FORMULA_FIELD_KEYS or key_text.lower() in {"formula", "ingredients"}


def _looks_like_extra_chinese_field(line: str, key: str):
    text = str(line or "").lstrip()
    if text.startswith(("(", "（")):
        return False
    return bool(key and re.search(r"[\u4e00-\u9fff]", key))


def _formula_alias_block(ai_by_key: dict):
    for formula_key, block in ai_by_key.items():
        if not _is_formula_key(formula_key):
            continue
        if block:
            return block
    return ""


def _replace_first_line_key(block: str, template_line: str):
    lines = str(block or "").splitlines()
    if not lines:
        return block

    template_key = _line_key(template_line)
    if not template_key:
        return block

    separator = "：" if "：" in template_line else ":"
    first_line = lines[0]
    for sep in ("：", ":"):
        if sep in first_line:
            first_value = first_line.split(sep, 1)[1]
            lines[0] = f"{template_key}{separator}{first_value}"
            return "\n".join(lines).rstrip()

    lines[0] = f"{template_key}{separator}"
    return "\n".join(lines).rstrip()


def constrain_description_to_template(template: str, ai_text: str):
    template_lines = str(template or "").splitlines()
    ai_lines = str(ai_text or "").splitlines()
    template_keys = {
        _line_key(line)
        for line in template_lines
        if _line_key(line)
    }

    ai_by_key = {}
    for index, line in enumerate(ai_lines):
        key = _line_key(line)
        if key and key not in ai_by_key:
            if _is_formula_key(key):
                block = [line]
                for next_line in ai_lines[index + 1:]:
                    next_key = _line_key(next_line)
                    if (
                        next_key
                        and not _is_formula_key(next_key)
                        and (next_key in template_keys or _looks_like_extra_chinese_field(next_line, next_key))
                    ):
                        break
                    block.append(next_line)
                ai_by_key[key] = "\n".join(block).rstrip()
            else:
                ai_by_key[key] = line

    result = []
    for template_line in template_lines:
        key = _line_key(template_line)
        if not key:
            result.append(template_line)
            continue

        ai_line = ai_by_key.get(key)
        if not ai_line and _is_formula_key(key):
            ai_line = _formula_alias_block(ai_by_key)
        if not ai_line:
            result.append(template_line)
            continue

        if _is_formula_key(key):
            ai_line = _replace_first_line_key(ai_line, template_line)

        if template_line.strip() != f"{key}：" and template_line.strip() != f"{key}:" and ai_line.strip() in (f"{key}：", f"{key}:"):
            result.append(template_line)
            continue

        result.append(ai_line)

    return "\n".join(result)


def _line_separator(line: str):
    text = str(line or "")
    for sep in ("：", ":"):
        if sep in text:
            return sep
    return ""


def _line_value(line: str):
    text = str(line or "")
    sep = _line_separator(text)
    if not sep:
        return ""
    return text.split(sep, 1)[1].strip()


def _render_description_line(field_title: str, separator: str, source: str, value: str = ""):
    marker = f"[{source}]"
    value_text = str(value or "").strip()
    if value_text:
        return f"{field_title}{separator}{marker} {value_text}"
    return f"{field_title}{separator}{marker}"


def render_description_from_fields(template_text, description_fields):
    if not isinstance(description_fields, dict) or not description_fields:
        return ""

    rendered_lines = []
    has_ai_value = False

    for template_line in str(template_text or "").splitlines():
        if not str(template_line or "").strip():
            rendered_lines.append(template_line)
            continue

        field_title = _line_key(template_line)
        separator = _line_separator(template_line)
        if not field_title or not separator:
            rendered_lines.append(template_line)
            continue

        raw_value = description_fields.get(field_title)
        value = "" if raw_value is None else str(raw_value).strip()

        if value:
            has_ai_value = True
            if _is_formula_key(field_title) and "\n" in value:
                rendered_lines.append(_render_description_line(field_title, separator, "AI"))
                rendered_lines.extend(value.splitlines())
            else:
                rendered_lines.append(_render_description_line(field_title, separator, "AI", value))
            continue

        rendered_lines.append(
            _render_description_line(field_title, separator, "模板", _line_value(template_line))
        )

    if not has_ai_value:
        return ""

    return "\n".join(rendered_lines)


def _render_description_placeholders(description_template: str, order_data: dict):
    source = "" if description_template is None else str(description_template)
    values = order_data if isinstance(order_data, dict) else {}

    def replace_placeholder(match):
        key = match.group(1).strip()
        value = values.get(key)
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\{([^{}]+)\}", replace_placeholder, source)


DESCRIPTION_FIELDS_MARKER = "===DESCRIPTION_FIELDS==="


def parse_description_fields(ai_output):
    text = str(ai_output or "")
    if DESCRIPTION_FIELDS_MARKER not in text:
        return {}

    json_text = text.split(DESCRIPTION_FIELDS_MARKER, 1)[1].strip()
    if json_text.startswith("```"):
        lines = json_text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        json_text = "\n".join(lines).strip()

    start = json_text.find("{")
    if start < 0:
        return {}

    try:
        parsed, _ = json.JSONDecoder().raw_decode(json_text[start:])
    except Exception:
        return {}

    if not isinstance(parsed, dict):
        return {}

    cleaned = {}
    for key, value in parsed.items():
        if value is None:
            continue
        key_text = str(key or "").strip()
        if not key_text:
            continue
        if isinstance(value, str):
            value_text = value.strip()
        else:
            value_text = json.dumps(value, ensure_ascii=False).strip()
        if value_text:
            cleaned[key_text] = value_text
    return cleaned


def _split_description_output(ai_output):
    text = str(ai_output or "").strip()
    if DESCRIPTION_FIELDS_MARKER not in text:
        return text, {}
    description_text = text.split(DESCRIPTION_FIELDS_MARKER, 1)[0].rstrip()
    return description_text, parse_description_fields(text)


def _filter_description_fields_to_template(description_template: str, description_fields: dict):
    if not isinstance(description_fields, dict):
        return {}

    template_keys = {
        _line_key(line)
        for line in str(description_template or "").splitlines()
        if _line_key(line)
    }
    if not template_keys:
        return {}

    return {
        key: value
        for key, value in description_fields.items()
        if key in template_keys
    }


def generate_description_from_message(message: str, description_template: str, order_data: dict):
    api_key = get_deepseek_api_key()
    if not api_key:
        raise RuntimeError("没有读取到 DeepSeek API Key，请在配置中心 AI 设置或 .env 中配置")

    if not str(message or "").strip():
        raise ValueError("message不能为空，产品描述需要客户聊天内容才能 AI 生成")

    clean_data = order_data if isinstance(order_data, dict) else {}
    rendered_template = _render_description_placeholders(description_template, clean_data)
    data_text = json.dumps(clean_data, ensure_ascii=False, indent=2)

    prompt = f"""
你是一个外贸订单产品描述填写助手。

你不是简单复制模板。你的任务是认真阅读客户聊天记录，把能对应的信息主动填写到产品描述模板的对应词条中。

【要求】
1. 必须严格使用下方产品描述模板中的词条。
2. 不允许新增模板中没有的项目。
3. 不允许删除模板中的项目。
4. 保留模板原有行顺序、默认文字、空行、中文标点和整体格式。
5. 聊天记录中明确出现的信息，必须尽量填入最合适的词条后面。
6. 聊天记录未提到的信息，保留模板默认文字。
7. 如果模板某一项原本为空，聊天也没提到，则保持为空，不要编造。
8. 模板中的 {{字段key}} 占位符可以先用订单字段替换。
9. 最终输出纯文本，不要 JSON，不要 markdown。

【信息匹配规则】
- 颜色、瓶子颜色、胶囊颜色、软糖颜色、color 等信息，填入“颜色”“形状、大小和颜色”“包装尺寸和要求”等相关词条。
- 口味、flavor、taste、strawberry、mint、lemon、orange、berry 等中英文口味，填入“口味”相关词条。
- 60粒/瓶、1000瓶、20片/管、15g/袋、500 bags、1000 bottles 等数量规格，填入“包装数量和规格”或“包装方式、数量和规格”。
- label、标签、贴纸、客户设计、client design、customer design 等，填入“是否贴标签”“谁设计制作标签”“标签材质和工艺要求”。
- bottle、jar、bag、stick、tube、瓶、罐、袋、条、管等包装形式，填入“包装方式”或“包装尺寸和要求”相关词条。
- formula、配方、ingredients、成分等，填入“配方”。
- capsule、softgel、gummy、powder、drop、tablet、effervescent tablet 等英文产品形式也要识别，并填入剂型、形状或相关描述词条。
- 如果聊天内容和已解析订单字段都提供了同一信息，优先使用更具体、更完整的内容。

【配方/配方要求/Formula/Ingredients 双语格式】
当模板中出现“配方”“配方要求”“Formula”或“Ingredients”时，必须按下面格式输出：
1. 不要使用项目符号。
2. 不要使用表格。
3. 不要使用 markdown。
4. 不要输出“中文：”或“English：”。
5. 每个成分输出两行：第一行英文，保留 mg、g、ml 等英文单位格式；第二行中文，使用“毫克”“克”“毫升”等中文单位。
6. 每个成分之间空一行。
7. 如果聊天记录只提供英文配方，必须保留英文原文，并补充中文翻译行。
8. 如果聊天记录只提供中文配方，必须补充英文翻译行。
9. 如果聊天记录已经包含中英文，则整理成英文一行、中文一行的上下对应格式。
10. 剂量、单位、括号内容必须尽量保留。
11. 不允许编造聊天记录中没有的成分。
12. 不允许只输出英文，也不允许只输出中文。
13. 不允许遗漏聊天记录中明确出现的配方成分。
14. Serving Size、serving size、每份用量、建议食用量不是配方成分，不能混入配方成分列表；如果模板中有对应字段，可以写入对应字段。
15. 如果有总含量说明，也按英文一行、中文一行输出在配方末尾。
16. description_fields 中如果返回“配方”“配方要求”“Formula”或“Ingredients”，字段值也必须使用同样的中英双语格式，并用换行保留“英文行/中文行/空行”的结构。

配方格式示例：
配方要求：
300 mg New Zealand Green-Lipped Mussel Oil (Perna canaliculus oil) lipid extract
300毫克新西兰绿唇贻贝油（Perna canaliculus油）脂质提取物

199.55 mg organic extra virgin olive oil
199.55毫克有机特级初榨橄榄油

0.45 mg organic vitamin E
0.45毫克有机维生素E

(Total content per softgel capsule: 500 mg liquid)
（每粒软胶囊总含量：500毫克；毛重需要做到700mg）

英文配方输入时的输出示例：
Magnesium (as magnesium bisglycinate chelate 500 mg) 70mg
镁（双甘氨酸镁螯合物500毫克）70毫克

L-Theanine 200mg
L-茶氨酸200毫克

Ashwagandha (Withaniasomnifera) Extract (root) 300mg
南非醉茄（Withania somnifera）提取物（根）300毫克

【示例】
聊天：客户要草莓味软糖，小熊形状，60粒/瓶，1000瓶，客户自己设计标签。
模板：
软糖形状、大小和颜色：
软糖口味：
包装方式、数量和规格：
是否贴标签：
谁设计制作标签：
输出：
软糖形状、大小和颜色：小熊形状
软糖口味：草莓味
包装方式、数量和规格：1000瓶，60粒/瓶
是否贴标签：是
谁设计制作标签：客户自己设计

【已解析订单字段】
{data_text}

【客户聊天内容】
{message}

Additional structured output requirement:
The earlier plain-text-only rule applies to the product description section only.
After the complete product description text, append this marker and one JSON object:
===DESCRIPTION_FIELDS===
{{
  "template field title": "recognized value"
}}
Rules for DESCRIPTION_FIELDS:
1. JSON keys must be exact field titles from the product description template below.
2. Do not return fields that were not recognized.
3. Do not return null values.
4. Do not add fields that are not in the template.
5. Do not wrap the JSON in markdown fences.
6. If a returned field is 配方, 配方要求, Formula, or Ingredients, its JSON string value must keep the same bilingual formula format: English line, Chinese line, blank line between ingredients.

【产品描述模板】
{rendered_template}
"""

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0
        },
        timeout=60
    )

    if response.status_code != 200:
        raise RuntimeError(f"DeepSeek请求失败：{response.status_code} {response.text}")

    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    description_text, description_fields = _split_description_output(content)
    description_fields = _filter_description_fields_to_template(rendered_template, description_fields)

    rendered_from_fields = ""
    if description_fields:
        try:
            rendered_from_fields = render_description_from_fields(rendered_template, description_fields)
        except Exception:
            rendered_from_fields = ""

    if rendered_from_fields.strip():
        final_description_text = rendered_from_fields
    else:
        constrained = constrain_description_to_template(rendered_template, description_text)
        final_description_text = annotate_description_sources(rendered_template, constrained)

    ingredient_analysis = analyze_ingredient_initials_source(
        description_fields=description_fields,
        text=final_description_text,
    )

    return {
        "description_text": final_description_text,
        "description_fields": description_fields,
        "ingredient_initials": ingredient_analysis["initials"],
        "ingredient_initials_status": ingredient_analysis["status"],
        "ingredient_initials_message": ingredient_analysis["message"],
    }


def fill_description_from_message(message: str, template: str, data=None):
    try:
        return generate_description_from_message(message, template, data)
    except Exception as e:
        return {
            "error": str(e)
        }
