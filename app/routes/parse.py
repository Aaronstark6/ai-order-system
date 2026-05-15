from fastapi import APIRouter

from app.ai_parser import generate_description_from_message, parse_message
from app.chat_preprocessor import preprocess_chat_text
from app.description_template_manager import get_description_template
from app.template_manager import get_profile


router = APIRouter()


@router.post("/api/generate-description")
def api_generate_description(data: dict):
    try:
        template_name = str(data.get("template_name") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()

        if not template_name and profile_id:
            profile = get_profile(profile_id)
            settings = profile.get("description_settings", {}) if profile else {}
            template_name = str(settings.get("template_name") or "").strip()

        if not template_name:
            return {"success": False, "error": "template_name cannot be empty"}

        template = get_description_template(template_name)
        order_data = data.get("data", {})
        message = str(data.get("message") or "").strip()

        if not message:
            return {"success": False, "error": "message不能为空，产品描述需要客户聊天内容才能 AI 生成"}

        description_result = generate_description_from_message(message, template, order_data)

        return {
            "success": True,
            "template_name": template_name,
            "used_ai": True,
            "description_text": description_result.get("description_text", ""),
            "description_fields": description_result.get("description_fields", {}),
            "ingredient_initials": description_result.get("ingredient_initials", ""),
            "ingredient_initials_status": description_result.get("ingredient_initials_status", ""),
            "ingredient_initials_message": description_result.get("ingredient_initials_message", ""),
            "debug_message_length": len(message),
            "debug_template_length": len(template),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/api/parse")
def api_parse(data: dict):
    try:
        message = data.get("chat_text")
        if message is None:
            message = data.get("message", "")
        message = str(message or "")

        if not message.strip():
            return {"success": False, "error": "message不能为空"}

        chat_preprocess = preprocess_chat_text(message)
        clean_message = str(chat_preprocess.get("clean_text") or "").strip()
        preprocess_payload = {
            "stats": chat_preprocess.get("stats") or {},
            "removed_lines": chat_preprocess.get("removed_lines") or [],
        }
        if not clean_message:
            return {
                "success": False,
                "error": "message 清洗后为空，无法解析",
                "chat_preprocess": preprocess_payload,
            }

        return {
            "success": True,
            "data": parse_message(clean_message),
            "chat_preprocess": preprocess_payload,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
