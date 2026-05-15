from fastapi import APIRouter

from app.ai_parser import generate_description_from_message, parse_message
from app.chat_preprocessor import preprocess_chat_text
from app.description_template_manager import get_description_template
from app.logger import get_logger
from app.template_manager import get_profile


router = APIRouter()
logger = get_logger(__name__)


@router.post("/api/generate-description")
def api_generate_description(data: dict):
    try:
        logger.info("Product description generation started")
        template_name = str(data.get("template_name") or "").strip()
        profile_id = str(data.get("profile_id") or "").strip()

        if not template_name and profile_id:
            profile = get_profile(profile_id)
            settings = profile.get("description_settings", {}) if profile else {}
            template_name = str(settings.get("template_name") or "").strip()

        if not template_name:
            logger.warning("Product description generation rejected: empty template_name")
            return {"success": False, "error": "template_name cannot be empty"}

        template = get_description_template(template_name)
        order_data = data.get("data", {})
        message = str(data.get("message") or "").strip()

        if not message:
            logger.warning("Product description generation rejected: empty message")
            return {"success": False, "error": "message不能为空，产品描述需要客户聊天内容才能 AI 生成"}

        description_result = generate_description_from_message(message, template, order_data)
        logger.info("Product description generation succeeded: template=%s message_length=%s", template_name, len(message))

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
        logger.exception("Product description generation failed")
        return {"success": False, "error": str(e)}


@router.post("/api/parse")
def api_parse(data: dict):
    try:
        logger.info("AI parse started")
        message = data.get("chat_text")
        if message is None:
            message = data.get("message", "")
        message = str(message or "")

        if not message.strip():
            logger.warning("AI parse rejected: empty message")
            return {"success": False, "error": "message不能为空"}

        chat_preprocess = preprocess_chat_text(message)
        clean_message = str(chat_preprocess.get("clean_text") or "").strip()
        preprocess_payload = {
            "stats": chat_preprocess.get("stats") or {},
            "removed_lines": chat_preprocess.get("removed_lines") or [],
        }
        if not clean_message:
            logger.warning("AI parse rejected: clean message is empty")
            return {
                "success": False,
                "error": "message 清洗后为空，无法解析",
                "chat_preprocess": preprocess_payload,
            }

        parsed = parse_message(clean_message)
        if isinstance(parsed, dict) and parsed.get("error"):
            logger.error("AI parse failed: %s", parsed.get("error"))
        else:
            logger.info(
                "AI parse succeeded: raw_lines=%s clean_lines=%s removed_lines=%s",
                preprocess_payload.get("stats", {}).get("raw_lines"),
                preprocess_payload.get("stats", {}).get("clean_lines"),
                preprocess_payload.get("stats", {}).get("removed_lines"),
            )

        return {
            "success": True,
            "data": parsed,
            "chat_preprocess": preprocess_payload,
        }

    except Exception as e:
        logger.exception("AI parse failed")
        return {"success": False, "error": str(e)}
