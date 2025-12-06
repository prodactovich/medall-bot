from __future__ import annotations

import time

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from domain.analytics import ensure_session_id, new_request_id, track
from src.ai_client import ask_deepseek
from src.handlers.context import build_role_description
from src.handlers.roles import get_user_plan
from src.limits import ensure_usage, get_limits, inc_usage
from src.nlp_utils import (
    build_ai_input,
    detect_doc_type,
    detect_red_flags,
    detect_user_emotion,
)
from src.ui.messages import deep_limit_reached, docs_limit_reached


def _is_deep_mode(profile: str | None, mode: str | None) -> bool:
    """
    Какие режимы считаем <глубокими> для лимитов.
    Пока жёстко: глубокий анализ пациента, при желании можно добавить ещё.
    """
    if profile == "patient" and mode == "patient_deep":
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

    user_text = update.message.text.strip()
    if not user_text:
        return

    profile = context.user_data.get("profile_type")
    mode = context.user_data.get("mode")
    plan = get_user_plan(context)

    if profile is None:
        await update.message.reply_text(
            "Чтобы я мог правильно подстроиться под вас, "
            "сначала выберите роль через /start."
        )
        return

    # трекинг идентификаторов
    request_id = new_request_id()
    session_id = ensure_session_id(context)
    user_id = update.effective_user.id if update.effective_user else None
    t0 = time.perf_counter()

    limits = get_limits(plan)
    usage = ensure_usage(context)

    docs_cap = limits.get("docs")
    if docs_cap is not None and usage["docs_used"] >= docs_cap:
        await update.message.reply_text(docs_limit_reached())
        return

    if _is_deep_mode(profile, mode):
        deep_cap = limits.get("deep")
        if deep_cap is not None and usage["deep_used"] >= deep_cap:
            await update.message.reply_text(deep_limit_reached())
            return

    doc_type = detect_doc_type(user_text)
    emotion = detect_user_emotion(user_text)
    red_flags = detect_red_flags(user_text)

    role_desc = build_role_description(profile, mode, plan, context)

    ai_input = build_ai_input(
        raw_text=user_text,
        doc_type=doc_type,
        user_role=role_desc,
        emotion=emotion,
        flags=red_flags,
    )

    usage_info: dict = {}

    track(
        "document_sent",
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        role=profile,
        mode=mode,
        plan=plan,
        request_type="text",
        doc_type=doc_type,
        input_chars=len(user_text),
        red_flags=red_flags,
    )

    answer = await ask_deepseek(
        ai_input,
        role=role_desc,
        mode=mode or "",
        doc_type=doc_type,
        emotion=emotion,
        red_flags=red_flags,
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
        output_chars=len(answer),
        red_flags=red_flags,
        usage=usage_info,
        latency_ms=latency_ms,
    )

    history = context.user_data.setdefault("docs_history", [])
    history.append(user_text[:500])

    inc_usage(usage, deep=_is_deep_mode(profile, mode))

    app_usage = context.application.bot_data.setdefault(
        "usage",
        {"prompt_chars": 0, "completion_chars": 0},
    )
    app_usage["prompt_chars"] += len(ai_input)
    app_usage["completion_chars"] += len(answer)

    print(
        f"[USAGE] plan={plan}, profile={profile}, mode={mode}, "
        f"docs_used={usage['docs_used']}, deep_used={usage['deep_used']}, "
        f"prompt_chars={app_usage['prompt_chars']}, "
        f"completion_chars={app_usage['completion_chars']}"
    )

    await update.message.reply_text(answer)


text_handler = MessageHandler(
    filters.TEXT & ~filters.COMMAND,
    handle_message,
)
