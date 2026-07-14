from __future__ import annotations

import time

from src.application.dto import (
    DocumentAnalysisInput,
    DocumentAnalysisResult,
    SafetyAssessment,
)
from src.application.exceptions import LlmServiceError, OcrServiceError
from src.application.ports import (
    AnalysisEventSink,
    AnalysisStateRepository,
    LlmProvider,
    OcrProvider,
)
from src.nlp_utils import (
    build_ai_input,
    detect_doc_type,
    detect_red_flags,
    detect_user_emotion,
)
from src.text_cleaning import strip_control_chars, strip_markdown_artifacts


class NullAnalysisEventSink:
    def document_sent(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        doc_type: str,
        input_chars: int,
        red_flags: list[str],
    ) -> None:
        return None

    def explanation_generated(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
    ) -> None:
        return None


class NullAnalysisStateRepository:
    def save_user_document(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        text: str,
        scenario: str,
    ) -> None:
        return None

    def save_analysis_result(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
        *,
        scenario: str,
    ) -> None:
        return None


class DocumentAnalysisService:
    def __init__(
        self,
        *,
        llm_provider: LlmProvider,
        ocr_provider: OcrProvider | None = None,
        event_sink: AnalysisEventSink | None = None,
        state_repository: AnalysisStateRepository | None = None,
    ) -> None:
        self._llm_provider = llm_provider
        self._ocr_provider = ocr_provider
        self._event_sink = event_sink or NullAnalysisEventSink()
        self._state_repository = (
            state_repository or NullAnalysisStateRepository()
        )

    async def analyze(
        self, analysis_input: DocumentAnalysisInput
    ) -> DocumentAnalysisResult:
        t0 = time.perf_counter()
        source_text = await self._get_source_text(analysis_input)

        doc_type = detect_doc_type(source_text)
        emotion = detect_user_emotion(source_text)
        red_flags = detect_red_flags(source_text)
        safety = self._assess_safety(red_flags)
        scenario = (
            analysis_input.mode or f"{analysis_input.role or 'user'}_text"
        )

        self._state_repository.save_user_document(
            analysis_input,
            text=source_text,
            scenario=scenario,
        )

        self._event_sink.document_sent(
            analysis_input,
            doc_type=doc_type,
            input_chars=len(source_text),
            red_flags=red_flags,
        )

        ai_input = build_ai_input(
            raw_text=source_text,
            doc_type=doc_type,
            user_role=analysis_input.role_description,
            emotion=emotion,
            flags=red_flags,
        )

        usage: dict = {}
        try:
            explanation = await self._llm_provider.generate_explanation(
                ai_input,
                role=analysis_input.role_description,
                mode=analysis_input.mode or "",
                doc_type=doc_type,
                emotion=emotion,
                red_flags=red_flags,
                usage_tracker=usage,
                plan=analysis_input.plan,
            )
        except LlmServiceError:
            raise
        except Exception as exc:
            raise LlmServiceError(
                "Не удалось получить ответ от интеллектуального модуля."
            ) from exc

        explanation = strip_markdown_artifacts(explanation)
        explanation = strip_control_chars(explanation)
        if not explanation.strip():
            raise LlmServiceError(
                "Интеллектуальный модуль вернул пустой ответ."
            )

        result = DocumentAnalysisResult(
            source_text=source_text,
            prompt_chars=len(ai_input),
            doc_type=doc_type,
            emotion=emotion,
            safety=safety,
            explanation=explanation,
            usage=usage,
            latency_ms=int((time.perf_counter() - t0) * 1000),
        )

        self._state_repository.save_analysis_result(
            analysis_input,
            result,
            scenario=scenario,
        )
        self._event_sink.explanation_generated(analysis_input, result)
        return result

    async def _get_source_text(
        self, analysis_input: DocumentAnalysisInput
    ) -> str:
        if analysis_input.source == "text":
            text = analysis_input.text.strip()
            if not text:
                raise OcrServiceError("Документ не содержит текста.")
            return text

        if not analysis_input.file_path:
            raise OcrServiceError("Не передан файл для OCR-разбора.")
        if self._ocr_provider is None:
            raise OcrServiceError("OCR-провайдер не настроен.")

        try:
            text = await self._ocr_provider.extract_text(
                analysis_input.file_path,
                analysis_input.ocr_language,
            )
        except OcrServiceError:
            raise
        except Exception as exc:
            raise OcrServiceError(
                "Не удалось извлечь текст из документа."
            ) from exc

        text = text.strip()
        if not text:
            raise OcrServiceError("Не удалось разобрать текст с изображения.")
        return text

    def _assess_safety(self, red_flags: list[str]) -> SafetyAssessment:
        if red_flags:
            return SafetyAssessment(
                red_flags=red_flags,
                urgency_level="urgent",
            )
        return SafetyAssessment(red_flags=[], urgency_level="unknown")
