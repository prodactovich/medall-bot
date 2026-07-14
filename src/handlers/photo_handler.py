import asyncio
import os

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from domain.analytics import ensure_session_id, new_request_id
from src.application.defaults import get_document_analysis_service
from src.application.dto import DocumentAnalysisInput
from src.application.exceptions import DocumentAnalysisError, OcrServiceError
from src.handlers.context import build_role_description
from src.handlers.roles import get_user_plan
from src.quota import (
    MAX_DOCS_PER_MONTH,
    consume_document_quota,
    consume_ocr_bonus_document,
    get_ocr_bonus_state,
    restore_document_quota,
    restore_ocr_bonus_document,
)
from src.security import check_rate_limit
from src.services.patient_context import (
    set_current_scenario,
    set_profile_type,
)
from src.ui.messages import monthly_docs_limit


async def _typing_keeper(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    stop_event: asyncio.Event,
) -> None:
    """Периодически шлём статус 'печатает', пока идёт обработка фото."""
    try:
        while not stop_event.is_set():
            try:
                await context.bot.send_chat_action(
                    chat_id=chat_id, action=ChatAction.TYPING
                )
            except Exception:
                return
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=4)
            except asyncio.TimeoutError:
                continue
    finally:
        stop_event.set()


TEMP_DIR = "tmp"
os.makedirs(TEMP_DIR, exist_ok=True)
MAX_PHOTO_BYTES = 10 * 1024 * 1024
PHOTO_RATE_LIMIT_PER_MIN = 6


async def handle_photo(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    message = update.message
    if not message:
        return
    typing_stop: asyncio.Event | None = None
    typing_task: asyncio.Task | None = None

    request_id = new_request_id()
    session_id = ensure_session_id(context)
    user_id = update.effective_user.id if update.effective_user else None

    if user_id is not None:
        allowed, retry_after = check_rate_limit(
            context,
            user_id=user_id,
            channel="photo",
            limit=PHOTO_RATE_LIMIT_PER_MIN,
            window_seconds=60,
        )
        if not allowed:
            await message.reply_text(
                "Слишком много фото за короткое время.\n"
                f"Попробуйте снова через {retry_after} сек."
            )
            return

    bonus_left = 0
    bonus_granted = False
    used_bonus = False
    used_main_quota = False
    file_path: str | None = None

    photo = message.photo[-1]
    if photo.file_size and photo.file_size > MAX_PHOTO_BYTES:
        await message.reply_text(
            "Файл слишком большой для обработки.\n"
            "Пожалуйста, отправьте изображение до 10 МБ."
        )
        return

    # Списываем квоту только после базовой валидации файла.
    if user_id is not None:
        bonus_left, bonus_granted = get_ocr_bonus_state(user_id)
        if bonus_left > 0 and consume_ocr_bonus_document(user_id):
            used_bonus = True
        elif not consume_document_quota(user_id):
            bonus_hint = (
                "Вы можете получить ещё 2 OCR-разбора бесплатно.\n"
                "Напишите отзыв в формате:\n"
                "Отзыв: ваш текст"
            )
            if bonus_granted and bonus_left == 0:
                bonus_hint = "Бонус за отзыв в этом месяце уже использован."
            await message.reply_text(
                monthly_docs_limit(MAX_DOCS_PER_MONTH) + "\n\n" + bonus_hint
            )
            return
        else:
            used_main_quota = True

    await context.bot.send_chat_action(
        chat_id=message.chat_id,
        action=ChatAction.UPLOAD_PHOTO,
    )

    if message.chat_id:
        typing_stop = asyncio.Event()
        typing_task = asyncio.create_task(
            _typing_keeper(context, message.chat_id, typing_stop)
        )

    file = await photo.get_file()
    file_path = os.path.join(TEMP_DIR, f"{file.file_unique_id}.jpg")
    await file.download_to_drive(file_path)

    try:
        profile = context.user_data.get("profile_type")
        mode = context.user_data.get("mode")
        plan = get_user_plan(context)
        role_desc = build_role_description(profile, mode, plan, context)

        if user_id is not None and profile == "patient":
            scenario = mode or "patient_photo"
            set_profile_type(user_id, profile)
            set_current_scenario(user_id, scenario)

        await context.bot.send_chat_action(
            chat_id=message.chat_id,
            action=ChatAction.TYPING,
        )

        result = await get_document_analysis_service().analyze(
            DocumentAnalysisInput(
                source="file",
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                role=profile,
                mode=mode,
                plan=str(plan),
                role_description=role_desc,
                file_path=file_path,
                ocr_language="rus",
                current_summary=context.user_data.get("last_document_summary"),
            )
        )

        explanation_clean = result.explanation
        history = context.user_data.get("docs_history", [])
        history.append(result.source_text[:500])
        context.user_data["docs_history"] = history

        if user_id is not None and profile == "patient":
            summary = explanation_clean[:500]
            context.user_data["last_document_text"] = result.source_text
            context.user_data["last_ai_breakdown"] = explanation_clean
            context.user_data["last_document_summary"] = summary

        reply_text = (
            f"{explanation_clean}\n\n"
            "Если нужно, можно прислать ещё один документ или задать уточняющий вопрос."
        )

        await message.reply_text(reply_text)

    except OcrServiceError as e:
        if used_bonus and user_id is not None:
            restore_ocr_bonus_document(user_id)
            used_bonus = False
        elif used_main_quota and user_id is not None:
            restore_document_quota(user_id)
            used_main_quota = False
        print(f"OCR error: {e}")
        await message.reply_text(
            "Не получилось разобрать текст с изображения.\n"
            "Попробуйте сделать фото ближе, при хорошем освещении — "
            "я постараюсь помочь ещё раз."
        )
    except DocumentAnalysisError as e:
        if used_bonus and user_id is not None:
            restore_ocr_bonus_document(user_id)
            used_bonus = False
        elif used_main_quota and user_id is not None:
            restore_document_quota(user_id)
            used_main_quota = False
        print(f"Document analysis error: {e}")
        await message.reply_text(
            "Не удалось обработать изображение. Попробуйте, пожалуйста, чуть позже."
        )
    except Exception as e:
        if used_bonus and user_id is not None:
            # Возвращаем бонусный слот, если обработка не состоялась.
            restore_ocr_bonus_document(user_id)
            used_bonus = False
        elif used_main_quota and user_id is not None:
            restore_document_quota(user_id)
            used_main_quota = False
        print(f"OCR/DeepSeek error: {e}")
        await message.reply_text(
            "Не удалось обработать изображение. Попробуйте, пожалуйста, чуть позже."
        )
    finally:
        if typing_stop:
            typing_stop.set()
        if typing_task:
            await typing_task
        if file_path:
            try:
                os.remove(file_path)
            except OSError:
                pass


photo_handler = MessageHandler(
    filters.ChatType.PRIVATE & filters.PHOTO, handle_photo
)
