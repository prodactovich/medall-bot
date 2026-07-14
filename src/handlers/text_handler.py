from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, MessageHandler, filters

from domain.analytics import ensure_session_id, new_request_id, track
from src.application.defaults import get_document_analysis_service
from src.application.dto import DocumentAnalysisInput
from src.application.exceptions import DocumentAnalysisError
from src.handlers import roles
from src.handlers.context import build_role_description
from src.handlers.roles import get_user_plan
from src.limits import ensure_usage, get_limits, inc_usage
from src.quota import (
    MAX_DOCS_PER_MONTH,
    get_docs_used,
    get_ocr_bonus_state,
    grant_ocr_bonus_for_feedback,
)
from src.security import check_rate_limit
from src.services.patient_context import (
    set_current_scenario,
    set_profile_type,
)
from src.ui.buttons import (
    BTN_BACK_FROM_SUBSCRIPTION,
    BTN_BACK_TO_ROLE,
    BTN_PATIENT_CHANGE_ROLE,
    BTN_PLAN_BASIC,
    BTN_PLAN_PREMIUM,
    BTN_SUBSCRIPTION,
    DOC_BTN_DRUGS,
    DOC_BTN_FOREIGN,
    DOC_BTN_GUIDELINES,
    DOC_BTN_PATIENT_EXPL,
    DOC_BTN_SUPPORT,
    DOCTOR_SPECIALTIES,
    PAT_BTN_24H_PLAN,
    PAT_BTN_EXPLAIN_DOC,
    PAT_BTN_QUESTIONS,
    PAT_BTN_URGENCY,
    ROLE_ABOUT,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STUDENT,
    ST_BTN_ESSAY,
    ST_BTN_EXPLAIN,
    ST_BTN_SUPPORT,
    ST_BTN_TESTS,
    ST_BTN_TRAIN,
)
from src.ui.messages import deep_limit_reached, docs_limit_reached

MAX_TEXT_CHARS = 12_000
TEXT_RATE_LIMIT_PER_MIN = 12
BONUS_OCR_DOCS = 2
FEEDBACK_PREFIXES = ("отзыв:", "feedback:")
UNDERSTOOD_MARKERS = (
    "понятно",
    "теперь понятно",
    "ясно",
    "спасибо, понятно",
    "понял",
    "поняла",
)


def _is_understanding_signal(text: str) -> bool:
    t = (text or "").lower().strip(" .,!?:;")
    return any(marker in t for marker in UNDERSTOOD_MARKERS)


def _is_clarifying_question(text: str) -> bool:
    t = (text or "").lower()
    if "?" in t:
        return True
    starters = (
        "а если",
        "что это значит",
        "правильно ли",
        "как понять",
        "это нормально",
    )
    return any(t.startswith(prefix) for prefix in starters)


async def _maybe_grant_ocr_bonus_for_feedback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> bool:
    if not update.message or not update.message.text:
        return False

    user_text = update.message.text.strip()
    lower = user_text.lower()
    if not any(lower.startswith(prefix) for prefix in FEEDBACK_PREFIXES):
        return False

    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return False

    feedback_body = (
        user_text.split(":", 1)[1].strip() if ":" in user_text else ""
    )
    if len(feedback_body) < 20:
        await update.message.reply_text(
            "Чтобы получить бонус, отзыв должен быть чуть подробнее "
            "(минимум 20 символов после 'Отзыв:')."
        )
        return True

    bonus_left, bonus_granted = get_ocr_bonus_state(user_id)
    if bonus_granted:
        if bonus_left > 0:
            await update.message.reply_text(
                f"Спасибо, бонус уже активен. Осталось OCR-разборов: {bonus_left}."
            )
        else:
            await update.message.reply_text(
                "Спасибо, бонус за отзыв в этом месяце уже был использован."
            )
        return True

    used_docs = get_docs_used(user_id)
    if used_docs < MAX_DOCS_PER_MONTH:
        await update.message.reply_text(
            "Бонус за отзыв активируется после исчерпания месячного OCR-лимита."
        )
        return True

    granted = grant_ocr_bonus_for_feedback(user_id, BONUS_OCR_DOCS)
    if not granted:
        await update.message.reply_text(
            "Сейчас не удалось выдать бонус. Попробуйте отправить отзыв ещё раз."
        )
        return True

    track(
        "feedback_submitted",
        user_id=user_id,
        session_id=ensure_session_id(context),
        review_length=len(feedback_body),
        bonus_docs=BONUS_OCR_DOCS,
    )

    await update.message.reply_text(
        "Спасибо за отзыв. Бонус активирован: +2 OCR-разбора в этом месяце."
    )
    return True


async def _route_keyboard_buttons(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> bool:
    """Фолбэк: руками вызываем обработчики кнопок, если regex-фильтры не сработали."""
    if not update.message or not update.message.text:
        return False

    text = update.message.text

    if text in (ROLE_PATIENT, ROLE_STUDENT, ROLE_DOCTOR, ROLE_ABOUT):
        await roles.handle_role_choice(update, context)
        return True

    if text in DOCTOR_SPECIALTIES:
        await roles.handle_doctor_specialty(update, context)
        return True

    if text in (BTN_BACK_TO_ROLE, BTN_PATIENT_CHANGE_ROLE):
        await roles.handle_back_to_role(update, context)
        return True
    if text == BTN_BACK_FROM_SUBSCRIPTION:
        await roles.handle_back_from_subscription(update, context)
        return True

    if text in (
        PAT_BTN_EXPLAIN_DOC,
        PAT_BTN_URGENCY,
        PAT_BTN_24H_PLAN,
        PAT_BTN_QUESTIONS,
    ):
        await roles.handle_patient_menu_button(update, context)
        return True

    if text in (
        DOC_BTN_GUIDELINES,
        DOC_BTN_DRUGS,
        DOC_BTN_PATIENT_EXPL,
        DOC_BTN_FOREIGN,
        DOC_BTN_SUPPORT,
    ):
        await roles.handle_doctor_menu_button(update, context)
        return True

    if text in (
        ST_BTN_EXPLAIN,
        ST_BTN_TRAIN,
        ST_BTN_TESTS,
        ST_BTN_ESSAY,
        ST_BTN_SUPPORT,
    ):
        await roles.handle_student_menu_button(update, context)
        return True

    if text == BTN_SUBSCRIPTION:
        await roles.show_subscription(update, context)
        return True

    if text in (BTN_PLAN_BASIC, BTN_PLAN_PREMIUM):
        await roles.handle_plan_choice(update, context)
        return True

    return False


def _is_deep_mode(profile: str | None, mode: str | None) -> bool:
    """
    Какие режимы считаем <глубокими> для лимитов.
    Пока жёстко: глубокий анализ пациента, при желании можно добавить ещё.
    """
    if profile == "patient" and mode in (
        "patient_urgency_check",
        "patient_next_24h_plan",
    ):
        return True
    # сюда можно добавить doctor_guidelines, doctor_foreign и т.п.
    return False


async def handle_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Главный обработчик текстовых сообщений.
    - проверяем роль;
    - учитываем план и лимиты;
    - определяем doc_type/эмоции/red_flags;
    - вызываем DeepSeek с контекстом роли/плана/режима;
    - обновляем историю и usage.
    """
    if not update.message or not update.message.text:
        return

    # Если это была кнопка клавиатуры, но regex-фильтры не поймали её (из-за emoji),
    # пробуем руками перевести в соответствующий handler.
    routed = await _route_keyboard_buttons(update, context)
    if routed:
        return

    if await _maybe_grant_ocr_bonus_for_feedback(update, context):
        return

    user_text = update.message.text.strip()
    if not user_text:
        return
    if len(user_text) > MAX_TEXT_CHARS:
        await update.message.reply_text(
            "Сообщение слишком длинное для безопасной обработки.\n"
            f"Пожалуйста, сократите текст до {MAX_TEXT_CHARS} символов."
        )
        return

    profile = context.user_data.get("profile_type")
    mode = context.user_data.get("mode")
    plan = get_user_plan(context)
    user_id = update.effective_user.id if update.effective_user else None

    if profile is None:
        await update.message.reply_text(
            "Чтобы я мог правильно подстроиться под вас, "
            "сначала выберите роль через /start."
        )
        return

    if user_id is not None and profile == "patient":
        set_profile_type(user_id, profile)
        session_id = ensure_session_id(context)
        if _is_understanding_signal(user_text):
            track(
                "understood_confirmed",
                user_id=user_id,
                session_id=session_id,
                role=profile,
                mode=mode,
                plan=plan,
            )
            await update.message.reply_text(
                "Отлично, рад, что стало понятнее. "
                "Если захотите, разберём следующий документ."
            )
            return

        scenario = mode or "patient_text"
        set_current_scenario(user_id, scenario)

        if context.user_data.get(
            "last_ai_breakdown"
        ) and _is_clarifying_question(user_text):
            track(
                "clarifying_question_asked",
                user_id=user_id,
                session_id=session_id,
                role=profile,
                mode=mode,
                plan=plan,
            )

    # трекинг идентификаторов
    request_id = new_request_id()
    session_id = ensure_session_id(context)

    if user_id is not None:
        allowed, retry_after = check_rate_limit(
            context,
            user_id=user_id,
            channel="text",
            limit=TEXT_RATE_LIMIT_PER_MIN,
            window_seconds=60,
        )
        if not allowed:
            await update.message.reply_text(
                "Слишком много запросов за короткое время.\n"
                f"Попробуйте снова через {retry_after} сек."
            )
            return

    limits = get_limits(plan)
    usage = ensure_usage(user_id)

    docs_cap = limits.get("docs")
    if docs_cap is not None and usage["docs_used"] >= docs_cap:
        await update.message.reply_text(docs_limit_reached())
        return

    if _is_deep_mode(profile, mode):
        deep_cap = limits.get("deep")
        if deep_cap is not None and usage["deep_used"] >= deep_cap:
            await update.message.reply_text(deep_limit_reached())
            return

    role_desc = build_role_description(profile, mode, plan, context)

    if update.effective_chat:
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

    # Сообщаем пользователю, что идёт генерация ответа.
    try:
        await update.message.reply_text(
            "Генерирую ответ, это может занять некоторое время ... ⏳"
        )
    except Exception:
        pass

    try:
        result = await get_document_analysis_service().analyze(
            DocumentAnalysisInput(
                source="text",
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                role=profile,
                mode=mode,
                plan=str(plan),
                role_description=role_desc,
                text=user_text,
                current_summary=context.user_data.get("last_document_summary"),
            )
        )
    except DocumentAnalysisError as e:
        print(f"Document analysis error: {e}")
        await update.message.reply_text(
            "Не удалось обработать запрос. Попробуйте ещё раз чуть позже."
        )
        return
    except Exception as e:
        print(f"Unexpected document analysis error: {e}")
        await update.message.reply_text(
            "Не удалось обработать запрос. Попробуйте ещё раз чуть позже."
        )
        return

    answer = result.explanation

    history = context.user_data.setdefault("docs_history", [])
    history.append(result.source_text[:500])

    if user_id is not None and profile == "patient":
        summary = answer[:500]
        context.user_data["last_document_text"] = result.source_text
        context.user_data["last_ai_breakdown"] = answer
        context.user_data["last_document_summary"] = summary

    usage = inc_usage(user_id, deep=_is_deep_mode(profile, mode))

    app_usage = context.application.bot_data.setdefault(
        "usage",
        {"prompt_chars": 0, "completion_chars": 0},
    )
    app_usage["prompt_chars"] += result.prompt_chars
    app_usage["completion_chars"] += len(answer)

    print(
        f"[USAGE] plan={plan}, profile={profile}, mode={mode}, "
        f"docs_used={usage['docs_used']}, deep_used={usage['deep_used']}, "
        f"prompt_chars={app_usage['prompt_chars']}, "
        f"completion_chars={app_usage['completion_chars']}"
    )

    await update.message.reply_text(answer)


text_handler = MessageHandler(
    filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
    handle_message,
)
