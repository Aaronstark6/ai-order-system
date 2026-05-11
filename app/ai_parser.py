import json
import os
import re

import requests
from dotenv import load_dotenv

from app.field_library import load_fields


load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def build_prompt(message: str):
    fields = load_fields()

    field_lines = []
    field_keys = []

    for field in fields:
        if field.get("enabled", True) is False:
            continue

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
    if not DEEPSEEK_API_KEY:
        return {
            "error": "没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件"
        }

    prompt, field_keys = build_prompt(message)

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
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

    return parsed


def _line_key(line: str):
    text = str(line or "")
    for sep in ("：", ":"):
        if sep in text:
            return text.split(sep, 1)[0].strip()
    return ""


def _is_formula_key(key: str):
    return key in ("配方", "配方要求")


def _looks_like_extra_chinese_field(line: str, key: str):
    text = str(line or "").lstrip()
    if text.startswith(("(", "（")):
        return False
    return bool(key and re.search(r"[\u4e00-\u9fff]", key))


def _formula_alias_block(ai_by_key: dict):
    for formula_key in ("配方", "配方要求"):
        block = ai_by_key.get(formula_key)
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


def generate_description_from_message(message: str, description_template: str, order_data: dict):
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件")

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

【配方/配方要求格式】
当模板中出现“配方”或“配方要求”时，必须按下面格式输出：
1. 不要使用项目符号。
2. 不要使用表格。
3. 不要使用 markdown。
4. 不要输出“中文：”或“English：”。
5. 每个成分输出两行：第一行英文，保留 mg、g、ml 等英文单位格式；第二行中文，使用“毫克”“克”“毫升”等中文单位。
6. 每个成分之间空一行。
7. 如果聊天记录只提供英文配方，则翻译中文行。
8. 如果聊天记录只提供中文配方，则翻译英文行。
9. 如果聊天记录已经包含中英文，则整理成英文一行、中文一行的上下对应格式。
10. 剂量、单位、括号内容必须尽量保留。
11. 不允许编造聊天记录中没有的成分。
12. 如果有总含量说明，也按英文一行、中文一行输出在配方末尾。

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

【产品描述模板】
{rendered_template}
"""

    response = requests.post(
        DEEPSEEK_URL,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
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

    return constrain_description_to_template(rendered_template, content)


def fill_description_from_message(message: str, template: str, data=None):
    try:
        return {
            "description_text": generate_description_from_message(message, template, data)
        }
    except Exception as e:
        return {
            "error": str(e)
        }
