from __future__ import annotations

import asyncio
from typing import Any

from domain.analytics import track
from src.ai_client import ask_deepseek
from src.application.document_analysis_service import DocumentAnalysisService
from src.application.dto import DocumentAnalysisInput, DocumentAnalysisResult
from src.application.exceptions import LlmServiceError, OcrServiceError
from src.application.patient_action_service import PatientActionService
from src.application.ports import LlmProvider, OcrProvider
from src.security import OCR_SEMAPHORE
from src.services.patient_context import (
    append_scenario_message,
    set_document_summary,
    set_document_text,
    set_last_ai_breakdown,
    set_profile_type,
)
from src.vision_client import image_to_text


class CurrentOcrProvider(OcrProvider):
    async def extract_text(self, file_path: str, language: str = "rus") -> str:
        try:
            async with OCR_SEMAPHORE:
                return await asyncio.to_thread(
                    image_to_text, file_path, language
                )
        except Exception as exc:
            raise OcrServiceError(
                "Не удалось извлечь текст из документа."
            ) from exc


class CurrentLlmProvider(LlmProvider):
    async def generate_explanation(
        self,
        content: str,
        *,
        role: str | None,
        mode: str | None,
        doc_type: str | None,
        emotion: str | None,
        red_flags: list[str],
        usage_tracker: dict[str, Any],
        plan: str,
    ) -> str:
        answer = await ask_deepseek(
            content,
            role=role,
            mode=mode,
            doc_type=doc_type,
            emotion=emotion,
            red_flags=red_flags,
            usage_tracker=usage_tracker,
            plan=plan,
        )
        if not answer.strip():
            raise LlmServiceError(
                "Интеллектуальный модуль вернул пустой ответ."
            )
        return answer


class CurrentAnalysisEventSink:
    def document_sent(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        doc_type: str,
        input_chars: int,
        red_flags: list[str],
    ) -> None:
        track(
            "document_sent",
            user_id=analysis_input.user_id,
            session_id=analysis_input.session_id,
            request_id=analysis_input.request_id,
            role=analysis_input.role,
            mode=analysis_input.mode,
            plan=analysis_input.plan,
            request_type=analysis_input.source,
            doc_type=doc_type,
            input_chars=input_chars,
            red_flags=red_flags,
        )

    def explanation_generated(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
    ) -> None:
        track(
            "explanation_generated",
            user_id=analysis_input.user_id,
            session_id=analysis_input.session_id,
            request_id=analysis_input.request_id,
            role=analysis_input.role,
            mode=analysis_input.mode,
            plan=analysis_input.plan,
            doc_type=result.doc_type,
            input_chars=result.prompt_chars,
            output_chars=len(result.explanation),
            red_flags=result.safety.red_flags,
            usage=result.usage,
            latency_ms=result.latency_ms,
        )


class CurrentAnalysisStateRepository:
    def save_user_document(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        text: str,
        scenario: str,
    ) -> None:
        if analysis_input.user_id is None or analysis_input.role != "patient":
            return
        set_profile_type(analysis_input.user_id, analysis_input.role)
        set_document_text(
            analysis_input.user_id,
            text,
            summary=analysis_input.current_summary,
        )
        append_scenario_message(
            analysis_input.user_id,
            scenario=scenario,
            author="user",
            text=text,
        )

    def save_analysis_result(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
        *,
        scenario: str,
    ) -> None:
        if analysis_input.user_id is None or analysis_input.role != "patient":
            return
        set_last_ai_breakdown(analysis_input.user_id, result.explanation)
        set_document_summary(analysis_input.user_id, result.explanation[:500])
        append_scenario_message(
            analysis_input.user_id,
            scenario=scenario,
            author="assistant",
            text=result.explanation,
        )


_default_service: DocumentAnalysisService | None = None
_default_patient_action_service: PatientActionService | None = None


def get_document_analysis_service() -> DocumentAnalysisService:
    global _default_service
    if _default_service is None:
        _default_service = DocumentAnalysisService(
            llm_provider=CurrentLlmProvider(),
            ocr_provider=CurrentOcrProvider(),
            event_sink=CurrentAnalysisEventSink(),
            state_repository=CurrentAnalysisStateRepository(),
        )
    return _default_service


def get_patient_action_service() -> PatientActionService:
    global _default_patient_action_service
    if _default_patient_action_service is None:
        _default_patient_action_service = PatientActionService(
            llm_provider=CurrentLlmProvider(),
        )
    return _default_patient_action_service
