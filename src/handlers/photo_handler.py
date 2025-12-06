import asyncio
import os
import time

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from domain.analytics import ensure_session_id, new_request_id, track
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
    can_process_document,
    register_document,
)
from src.vision_client import image_to_text

TEMP_DIR = "tmp"
os.makedirs(TEMP_DIR, exist_ok=True)


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    # идентификаторы и замер времени
    request_id = new_request_id()
    session_id = ensure_session_id(context)
    user_id = update.effective_user.id if update.effective_user else None
    t0 = time.perf_counter()

    # лимит basic-тарифа
    if user_id is not None and not can_process_document(user_id):
        await message.reply_text(
            "Лимит обработки документов на этот месяц исчерпан."
        )
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

        track(
            "document_sent",
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            role=profile,
            mode=mode,
            plan=plan,
            request_type="photo",
            doc_type=doc_type,
            input_chars=len(text),
            red_flags=flags,
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

        latency_ms = int((time.perf_counter() - t0) * 1000)
        track(
            "explanation_generated",
            user_id=user_id,
            session_id=session_id,
            request_id=request_id,
            role=profile,
            mode=mode,
            plan=plan,
            doc_type=doc_type,
            input_chars=len(ai_input),
            output_chars=len(explanation),
            red_flags=flags,
            usage=usage_info,
            latency_ms=latency_ms,
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
