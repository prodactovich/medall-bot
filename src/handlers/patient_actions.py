from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from domain.analytics import ensure_session_id, new_request_id
from src.application.defaults import get_patient_action_service
from src.application.dto import PatientActionInput
from src.application.exceptions import (
    DocumentAnalysisError,
    MissingPatientContextError,
)
from src.handlers.context import build_role_description
from src.services.patient_context import (
    hydrate_from_user_data,
    set_current_scenario,
    set_profile_type,
)
from src.services.patient_prompts import (
    NO_PATIENT_CONTEXT_MESSAGE,
)


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

    request_id = new_request_id()
    session_id = ensure_session_id(context)
    plan_obj = context.user_data.get("plan", "basic")
    plan = getattr(plan_obj, "value", plan_obj) or "basic"
    role_desc = build_role_description("patient", scenario_mode, plan, context)

    if update.effective_chat:
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action=ChatAction.TYPING,
            )
        except Exception:
            pass

    try:
        result = await get_patient_action_service().run(
            PatientActionInput(
                user_id=user_id,
                session_id=session_id,
                request_id=request_id,
                action=action,
                scenario_mode=scenario_mode,
                plan=plan,
                role_description=role_desc,
            )
        )
    except MissingPatientContextError:
        await message.reply_text(NO_PATIENT_CONTEXT_MESSAGE)
        return
    except DocumentAnalysisError as e:
        print(f"Patient action error: {e}")
        await message.reply_text(
            "Не удалось обработать запрос. Попробуйте ещё раз чуть позже."
        )
        return

    answer = result.answer
    context.user_data["last_ai_breakdown"] = answer

    await message.reply_text(answer)
