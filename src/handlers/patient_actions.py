from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from domain.analytics import ensure_session_id, new_request_id, track
from src.ai_client import ask_deepseek
from src.handlers.context import build_role_description
from src.services.patient_context import (
    append_scenario_message,
    build_patient_context,
    hydrate_from_user_data,
    set_current_scenario,
    set_last_ai_breakdown,
    set_profile_type,
)
from src.services.patient_prompts import (
    NO_PATIENT_CONTEXT_MESSAGE,
    build_patient_action_prompt,
)
from src.text_cleaning import strip_control_chars, strip_markdown_artifacts


async def run_patient_action(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    action: str,
    scenario_mode: str,
) -> None:
    message = update.message
    user = update.effective_user
    if not message or not user:
        return

    user_id = user.id
    context.user_data["mode"] = scenario_mode
    context.user_data["profile_type"] = "patient"
    set_profile_type(user_id, "patient")
    set_current_scenario(user_id, scenario_mode)
    hydrate_from_user_data(user_id, context.user_data)

    patient_context = build_patient_context(user_id)
    if not patient_context:
        await message.reply_text(NO_PATIENT_CONTEXT_MESSAGE)
        return

    request_id = new_request_id()
    session_id = ensure_session_id(context)
    plan_obj = context.user_data.get("plan", "basic")
    plan = getattr(plan_obj, "value", plan_obj) or "basic"
    role_desc = build_role_description("patient", scenario_mode, plan, context)

    prompt = build_patient_action_prompt(action, patient_context)

    append_scenario_message(
        user_id,
        scenario=scenario_mode,
        author="user",
        text=f"[patient_action:{action}]",
    )

    if update.effective_chat:
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

    usage_info: dict = {}
    answer = await ask_deepseek(
        prompt,
        role=role_desc,
        mode=scenario_mode,
        doc_type="медицинский документ",
        usage_tracker=usage_info,
        plan=plan,
    )
    answer = strip_markdown_artifacts(answer)
    answer = strip_control_chars(answer)
    if not answer.strip():
        answer = (
            "Не смог сформировать ответ. Попробуйте, пожалуйста, ещё раз "
            "или переформулируйте запрос."
        )

    context.user_data["last_ai_breakdown"] = answer
    set_last_ai_breakdown(user_id, answer)
    append_scenario_message(
        user_id,
        scenario=scenario_mode,
        author="assistant",
        text=answer,
    )

    track(
        "patient_action_generated",
        user_id=user_id,
        session_id=session_id,
        request_id=request_id,
        action=action,
        mode=scenario_mode,
        plan=plan,
        usage=usage_info,
    )

    await message.reply_text(answer)
