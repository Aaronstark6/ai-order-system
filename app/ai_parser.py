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
1. 保留模板原有行顺序、标题、换行和整体格式。
2. 能从聊天内容或订单字段明确判断的内容，填写到对应标题后面。
3. 不确定或没有提到的内容保持空白，不要编造。
4. 模板中的 {{字段key}} 占位符可以先用订单字段替换。
5. 只返回补全后的产品描述正文，不要解释，不要使用 markdown。

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
        "description_text": content
    }
