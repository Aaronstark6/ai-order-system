import json
import os

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
            return text.split(sep, 1)[0].strip() + sep
    return ""


def constrain_description_to_template(template: str, ai_text: str):
    template_lines = str(template or "").splitlines()
    ai_lines = str(ai_text or "").splitlines()

    ai_by_key = {}
    for line in ai_lines:
        key = _line_key(line)
        if key and key not in ai_by_key:
            ai_by_key[key] = line

    result = []
    for template_line in template_lines:
        key = _line_key(template_line)
        if not key:
            result.append(template_line)
            continue

        ai_line = ai_by_key.get(key)
        if not ai_line:
            result.append(template_line)
            continue

        if template_line.strip() != key and ai_line.strip() == key:
            result.append(template_line)
            continue

        result.append(ai_line)

    return "\n".join(result)


def fill_description_from_message(message: str, template: str, data=None):
    if not DEEPSEEK_API_KEY:
        return {
            "error": "没有读取到 DEEPSEEK_API_KEY，请检查 .env 文件"
        }

    order_data = data if isinstance(data, dict) else {}
    data_text = json.dumps(order_data, ensure_ascii=False, indent=2)

    prompt = f"""
你是一个外贸订单产品描述填写助手。

请根据客户聊天内容和已解析的订单字段，补全下面的产品描述模板。

【要求】
1. 必须严格使用下方产品描述模板中的词条。
2. 不允许新增模板中没有的项目。
3. 不允许删除模板中的项目。
4. 保留模板原有行顺序、默认文字、空行、中文标点和整体格式。
5. 聊天记录中明确提到的信息，填入对应词条后面。
6. 聊天记录未提到的信息，保留模板默认文字。
7. 如果模板某一项原本为空，聊天也没提到，则保持为空。
8. 模板中的 {{字段key}} 占位符可以先用订单字段替换。
9. 最终输出纯文本，不要 JSON，不要 markdown。

【已解析订单字段】
{data_text}

【客户聊天内容】
{message}

【产品描述模板】
{template}
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
        return {
            "error": "DeepSeek请求失败",
            "status_code": response.status_code,
            "detail": response.text
        }

    result = response.json()
    content = result["choices"][0]["message"]["content"].strip()

    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    return {
        "description_text": constrain_description_to_template(template, content)
    }
