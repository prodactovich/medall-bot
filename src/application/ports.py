from __future__ import annotations

from typing import Any, Protocol

from src.application.dto import DocumentAnalysisInput, DocumentAnalysisResult


class OcrProvider(Protocol):
    async def extract_text(self, file_path: str, language: str = "rus") -> str:
        """Extract plain text from a file."""


class LlmProvider(Protocol):
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
        """Generate a patient-friendly explanation."""


class AnalysisEventSink(Protocol):
    def document_sent(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        doc_type: str,
        input_chars: int,
        red_flags: list[str],
    ) -> None:
        """Persist a document-sent analytics event."""

    def explanation_generated(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
    ) -> None:
        """Persist an explanation-generated analytics event."""


class AnalysisStateRepository(Protocol):
    def save_user_document(
        self,
        analysis_input: DocumentAnalysisInput,
        *,
        text: str,
        scenario: str,
    ) -> None:
        """Persist incoming document context for later patient actions."""

    def save_analysis_result(
        self,
        analysis_input: DocumentAnalysisInput,
        result: DocumentAnalysisResult,
        *,
        scenario: str,
    ) -> None:
        """Persist generated explanation context."""
