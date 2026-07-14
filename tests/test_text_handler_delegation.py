from __future__ import annotations

import asyncio
from types import SimpleNamespace

from src.application.dto import DocumentAnalysisResult, SafetyAssessment
from src.handlers import text_handler


class FakeService:
    def __init__(self) -> None:
        self.inputs = []

    async def analyze(self, analysis_input):
        self.inputs.append(analysis_input)
        return DocumentAnalysisResult(
            source_text=analysis_input.text,
            prompt_chars=120,
            doc_type="неопределённый тип меддокумента",
            emotion="neutral",
            safety=SafetyAssessment(),
            explanation="Ответ из application service",
        )


class FakeMessage:
    def __init__(self, text: str) -> None:
        self.text = text
        self.replies: list[str] = []

    async def reply_text(self, text: str, **kwargs) -> None:
        self.replies.append(text)


class FakeBot:
    async def send_chat_action(self, **kwargs) -> None:
        return None


def test_text_handler_delegates_document_analysis(monkeypatch) -> None:
    service = FakeService()
    message = FakeMessage("Плановый анализ крови")
    update = SimpleNamespace(
        message=message,
        effective_user=SimpleNamespace(id=42),
        effective_chat=SimpleNamespace(id=100),
    )
    context = SimpleNamespace(
        user_data={
            "profile_type": "patient",
            "mode": "patient_explain_document",
            "plan": "basic",
        },
        application=SimpleNamespace(bot_data={}),
        bot=FakeBot(),
    )

    monkeypatch.setattr(
        text_handler,
        "get_document_analysis_service",
        lambda: service,
    )
    monkeypatch.setattr(
        text_handler,
        "check_rate_limit",
        lambda *args, **kwargs: (True, 0),
    )
    monkeypatch.setattr(
        text_handler,
        "ensure_usage",
        lambda user_id: {"docs_used": 0, "deep_used": 0},
    )
    monkeypatch.setattr(
        text_handler,
        "inc_usage",
        lambda user_id, deep: {"docs_used": 1, "deep_used": 0},
    )
    monkeypatch.setattr(
        text_handler,
        "set_profile_type",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        text_handler,
        "set_current_scenario",
        lambda *args, **kwargs: None,
    )

    asyncio.run(text_handler.handle_message(update, context))

    assert len(service.inputs) == 1
    assert service.inputs[0].text == "Плановый анализ крови"
    assert service.inputs[0].source == "text"
    assert "Ответ из application service" in message.replies
