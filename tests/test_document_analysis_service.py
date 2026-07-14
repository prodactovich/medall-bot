from __future__ import annotations

import asyncio

import pytest

from src.application.document_analysis_service import DocumentAnalysisService
from src.application.dto import DocumentAnalysisInput
from src.application.exceptions import LlmServiceError, OcrServiceError


class FakeLlmProvider:
    def __init__(self, answer: str = "Понятное объяснение") -> None:
        self.answer = answer
        self.calls: list[str] = []

    async def generate_explanation(self, content: str, **kwargs) -> str:
        self.calls.append(content)
        kwargs["usage_tracker"].update({"total_tokens": 10})
        return self.answer


class FailingLlmProvider(FakeLlmProvider):
    async def generate_explanation(self, content: str, **kwargs) -> str:
        raise RuntimeError("llm unavailable")


class FakeOcrProvider:
    def __init__(self, text: str = "Гемоглобин 130") -> None:
        self.text = text

    async def extract_text(self, file_path: str, language: str = "rus") -> str:
        return self.text


class FailingOcrProvider:
    async def extract_text(self, file_path: str, language: str = "rus") -> str:
        raise RuntimeError("ocr unavailable")


def _input(**overrides) -> DocumentAnalysisInput:
    values = {
        "source": "text",
        "user_id": 123,
        "session_id": "session-1",
        "request_id": "request-1",
        "role": "patient",
        "mode": "patient_explain_document",
        "plan": "basic",
        "role_description": "patient role",
        "text": "Гемоглобин 130, жалоб нет",
    }
    values.update(overrides)
    return DocumentAnalysisInput(**values)


def test_successful_analysis_returns_structured_result() -> None:
    llm = FakeLlmProvider()
    service = DocumentAnalysisService(llm_provider=llm)

    result = asyncio.run(service.analyze(_input()))

    assert result.explanation == "Понятное объяснение"
    assert result.source_text == "Гемоглобин 130, жалоб нет"
    assert result.doc_type == "анализ крови"
    assert result.prompt_chars > len(result.source_text)
    assert result.usage == {"total_tokens": 10}
    assert llm.calls


def test_ocr_error_is_application_exception() -> None:
    service = DocumentAnalysisService(
        llm_provider=FakeLlmProvider(),
        ocr_provider=FailingOcrProvider(),
    )

    with pytest.raises(OcrServiceError):
        asyncio.run(
            service.analyze(
                _input(source="file", text="", file_path="document.jpg")
            )
        )


def test_llm_error_is_application_exception() -> None:
    service = DocumentAnalysisService(llm_provider=FailingLlmProvider())

    with pytest.raises(LlmServiceError):
        asyncio.run(service.analyze(_input()))


def test_safety_unknown_when_no_red_flags_detected() -> None:
    service = DocumentAnalysisService(llm_provider=FakeLlmProvider())

    result = asyncio.run(
        service.analyze(_input(text="Плановый осмотр, жалоб нет"))
    )

    assert result.safety.urgency_level == "unknown"
    assert result.safety.red_flags == []
