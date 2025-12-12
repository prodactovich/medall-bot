import asyncio
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from src.ai_client import ask_deepseek
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
        await message.reply_text(
            f"📊 Лимит обработки документов на этот месяц исчерпан.\n\n"
            f"Сейчас в базовом тарифе доступно до {MAX_DOCS_PER_MONTH} документов "
            f"в месяц на одного пользователя.\n"
            "Расширенный Pro-тариф пока в разработке."
        )
        return

    # показываем processing фото
    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.UPLOAD_PHOTO,
    )

    # Берём самое большое фото
    photo = message.photo[-1]
    file = await photo.get_file()
    file_path = os.path.join(TEMP_DIR, f"{file.file_unique_id}.jpg")
    await file.download_to_drive(file_path)

    try:
        # OCR в отдельном потоке
        text = await asyncio.to_thread(image_to_text, file_path, "rus")

        if not text.strip():
            await message.reply_text(
                "Не получилось разобрать текст с изображения 😔\n"
                "Попробуйте сделать фото ближе, при хорошем освещении — я постараюсь помочь ещё раз."
            )
            return

        if user_id is not None:
            register_document(user_id)

        # сохраняем распознанный текст в историю
        history = context.user_data.get("docs_history", [])
        history.append(text)
        context.user_data["docs_history"] = history

        # Анализируем распознанный текст как документ
        doc_type = detect_doc_type(text)
        emotion = detect_user_emotion(text)
        flags = detect_red_flags(text)
        user_role = context.user_data.get("role")

        ai_input = build_ai_input(
            raw_text=text,
            doc_type=doc_type,
            user_role=user_role,
            emotion=emotion,
            flags=flags,
        )

        await context.bot.send_chat_action(
            chat_id=message.chat_id,
            action=ChatAction.TYPING,
        )

        explanation = await asyncio.awaited(ask_deepseek, ai_input)

        reply_text = (
            f"{explanation}\n\n"
            "Если нужно, можно прислать ещё один документ или задать уточняющий вопрос 🧾"
        )

        await message.reply_text(
            reply_text,
            parse_mode="Markdown",
        )

    except Exception as e:
        print(f"OCR/DeepSeek error: {e}")
        await message.reply_text(
            "⚠️ Не удалось обработать изображение. Попробуйте, пожалуйста, чуть позже."
        )
    finally:
        try:
            os.remove(file_path)
        except OSError:
            pass


photo_handler = MessageHandler(filters.PHOTO, handle_photo)
