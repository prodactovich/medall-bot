from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DocumentSource = Literal["text", "file"]


@dataclass(frozen=True)
class DocumentAnalysisInput:
    source: DocumentSource
    user_id: int | None
    session_id: str
    request_id: str
    role: str | None
    mode: str | None
    plan: str
    role_description: str
    text: str = ""
    file_path: str | None = None
    ocr_language: str = "rus"
    current_summary: str | None = None


@dataclass(frozen=True)
class SafetyAssessment:
    red_flags: list[str] = field(default_factory=list)
    urgency_level: Literal["unknown", "routine", "urgent"] = "unknown"


@dataclass(frozen=True)
class DocumentAnalysisResult:
    source_text: str
    prompt_chars: int
    doc_type: str
    emotion: str | None
    safety: SafetyAssessment
    explanation: str
    next_24h_plan: str = ""
    questions_for_doctor: str = ""
    usage: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0


@dataclass(frozen=True)
class PatientActionInput:
    user_id: int
    session_id: str
    request_id: str
    action: str
    scenario_mode: str
    plan: str
    role_description: str


@dataclass(frozen=True)
class PatientActionResult:
    answer: str
    usage: dict[str, Any] = field(default_factory=dict)
