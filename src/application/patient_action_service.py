from __future__ import annotations

from domain.analytics import track
from src.application.dto import PatientActionInput, PatientActionResult
from src.application.exceptions import (
    LlmServiceError,
    MissingPatientContextError,
)
from src.application.ports import LlmProvider
from src.services.patient_context import (
    append_scenario_message,
    build_patient_context,
    set_last_ai_breakdown,
)
from src.services.patient_prompts import build_patient_action_prompt
from src.text_cleaning import strip_control_chars, strip_markdown_artifacts


class PatientActionService:
    def __init__(self, *, llm_provider: LlmProvider) -> None:
        self._llm_provider = llm_provider

    async def run(
        self, action_input: PatientActionInput
    ) -> PatientActionResult:
        patient_context = build_patient_context(action_input.user_id)
        if not patient_context:
            raise MissingPatientContextError(
                "Нет контекста предыдущего медицинского документа."
            )

        prompt = build_patient_action_prompt(
            action_input.action,
            patient_context,
        )

        append_scenario_message(
            action_input.user_id,
            scenario=action_input.scenario_mode,
            author="user",
            text=f"[patient_action:{action_input.action}]",
        )

        usage: dict = {}
        try:
            answer = await self._llm_provider.generate_explanation(
                prompt,
                role=action_input.role_description,
                mode=action_input.scenario_mode,
                doc_type="медицинский документ",
                emotion=None,
                red_flags=[],
                usage_tracker=usage,
                plan=action_input.plan,
            )
        except LlmServiceError:
            raise
        except Exception as exc:
            raise LlmServiceError(
                "Не удалось получить ответ от интеллектуального модуля."
            ) from exc

        answer = strip_markdown_artifacts(answer)
        answer = strip_control_chars(answer)
        if not answer.strip():
            raise LlmServiceError(
                "Интеллектуальный модуль вернул пустой ответ."
            )

        set_last_ai_breakdown(action_input.user_id, answer)
        append_scenario_message(
            action_input.user_id,
            scenario=action_input.scenario_mode,
            author="assistant",
            text=answer,
        )

        track(
            "patient_action_generated",
            user_id=action_input.user_id,
            session_id=action_input.session_id,
            request_id=action_input.request_id,
            action=action_input.action,
            mode=action_input.scenario_mode,
            plan=action_input.plan,
            usage=usage,
        )
        return PatientActionResult(answer=answer, usage=usage)
