import os
import requests
from dotenv import load_dotenv

from app.config import get_enabled_fields

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def build_prompt(message: str):
    fields = get_enabled_fields()

    field_desc = []

    for key, field in fields.items():
        label = field.get("label", key)
        description = field.get("description", "")

        field_desc.append(f"{key}（{label}）：{description}")

    prompt = f"""
你是一个外贸订单信息提取助手。

请从下面的客户聊天内容中提取订单信息，并返回 JSON。

字段说明：
{chr(10).join(field_desc)}

要求：
1. 只返回 JSON
2. key 必须使用字段 key
3. 没有的信息可以不返回

客户内容：
{message}
"""

    return prompt


def parse_customer_text(message: str) -> dict:
    """
    调用 DeepSeek 进行 AI 解析
    """

    if not DEEPSEEK_API_KEY:
        raise Exception("未配置 DEEPSEEK_API_KEY")

    prompt = build_prompt(message)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你是一个信息提取助手"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    response = requests.post(DEEPSEEK_URL, headers=headers, json=data)

    if response.status_code != 200:
        raise Exception(f"DeepSeek API错误: {response.text}")

    result = response.json()

    content = result["choices"][0]["message"]["content"]

    # 尝试解析 JSON
    try:
        import json
        return json.loads(content)
    except Exception:
        # 如果 AI 没返回标准 JSON，就原样返回
        return {
            "raw": content
        }
