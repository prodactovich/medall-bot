import asyncio
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from src.ai_client import ask_deepseek
from src.handlers.context import build_role_description
from src.handlers.roles import get_user_plan
from src.nlp_utils import (
    build_ai_input,
    detect_doc_type,
    detect_red_flags,
    detect_user_emotion,
)
from src.quota import (
    MAX_DOCS_PER_MONTH,
    can_process_document,
    register_document,
)
from src.ui.messages import monthly_docs_limit
from src.vision_client import image_to_text

TEMP_DIR = "tmp"
os.makedirs(TEMP_DIR, exist_ok=True)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    user = update.effective_user
    user_id = user.id if user else None

    # лимит basic-тарифа
    if user_id is not None and not can_process_document(user_id):
        await message.reply_text(monthly_docs_limit(MAX_DOCS_PER_MONTH))
        return

    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.UPLOAD_PHOTO,
    )

    photo = message.photo[-1]
    file = await photo.get_file()
    file_path = os.path.join(TEMP_DIR, f"{file.file_unique_id}.jpg")
    await file.download_to_drive(file_path)

    try:
        text = await asyncio.to_thread(image_to_text, file_path, "rus")

        if not text.strip():
            await message.reply_text(
                "Не получилось разобрать текст с изображения.\n"
                "Попробуйте сделать фото ближе, при хорошем освещении — "
                "я постараюсь помочь ещё раз."
            )
            return

        if user_id is not None:
            register_document(user_id)

        history = context.user_data.get("docs_history", [])
        history.append(text)
        context.user_data["docs_history"] = history

        doc_type = detect_doc_type(text)
        emotion = detect_user_emotion(text)
        flags = detect_red_flags(text)
        profile = context.user_data.get("profile_type")
        mode = context.user_data.get("mode")
        plan = get_user_plan(context)
        role_desc = build_role_description(profile, mode, plan, context)

        ai_input = build_ai_input(
            raw_text=text,
            doc_type=doc_type,
            user_role=role_desc,
            emotion=emotion,
            flags=flags,
        )

        await context.bot.send_chat_action(
            chat_id=message.chat_id,
            action=ChatAction.TYPING,
        )

        usage_info: dict = {}
        explanation = await ask_deepseek(
            ai_input,
            role=role_desc,
            mode=mode or "",
            doc_type=doc_type,
            emotion=emotion,
            red_flags=flags,
            usage_tracker=usage_info,
            plan=plan,
        )

        reply_text = (
            f"{explanation}\n\n"
            "Если нужно, можно прислать ещё один документ или задать уточняющий вопрос."
        )

        await message.reply_text(reply_text)

    except Exception as e:
        print(f"OCR/DeepSeek error: {e}")
        await message.reply_text(
            "Не удалось обработать изображение. Попробуйте, пожалуйста, чуть позже."
        )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


photo_handler = MessageHandler(filters.PHOTO, handle_photo)
