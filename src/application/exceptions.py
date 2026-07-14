from __future__ import annotations


class DocumentAnalysisError(Exception):
    """Base application-level error for document analysis."""


class OcrServiceError(DocumentAnalysisError):
    """OCR provider failed or returned an unusable result."""


class LlmServiceError(DocumentAnalysisError):
    """LLM provider failed or returned an unusable result."""


class MissingPatientContextError(DocumentAnalysisError):
    """Patient action cannot run without previously analyzed document context."""
