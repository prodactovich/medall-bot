from __future__ import annotations

from typing import Any, Dict

NO_PATIENT_CONTEXT_MESSAGE = (
    "Сначала отправьте медицинский документ, анализ или заключение, "
    "чтобы я мог сформировать ответ по вашей ситуации."
)


def _format_recent_messages(context: Dict[str, Any]) -> str:
    rows = []
    for msg in context.get("recent_messages", []):
        author = "Пациент" if msg.get("author") == "user" else "Ассистент"
        text = (msg.get("text") or "").replace("\n", " ").strip()
        if text:
            rows.append(f"- {author}: {text[:400]}")
    return "\n".join(rows) if rows else "Нет сообщений в текущем сценарии."


def _base_safety_instructions() -> str:
    return (
        "Пиши простым русским языком для пациента.\n"
        "Не ставь диагноз.\n"
        "Не назначай лечение, дозировки или препараты.\n"
        "Не заменяй очный приём врача.\n"
        "Ответ должен быть структурированным, спокойным и безопасным.\n"
        "Не перегружай ответ: 4 коротких блока, до 8-10 пунктов всего.\n"
        "В начале добавь коротко: это не диагноз и не замена очного врача.\n"
        "Если видишь потенциальные риски, укажи, когда нужно срочно обратиться за медицинской помощью."
    )


def build_explain_document_prompt(context: Dict[str, Any]) -> str:
    return (
        "Сценарий: explain_document.\n"
        "Задача: расшифруй документ понятным языком.\n"
        f"{_base_safety_instructions()}\n\n"
        "Формат ответа:\n"
        "- Что показывает документ (1-2 предложения)\n"
        "- Что выглядит спокойно\n"
        "- Что требует внимания\n"
        "- Что обсудить с врачом на приёме\n\n"
        f"Текст документа:\n{context.get('last_document_text') or 'Нет данных.'}\n\n"
        f"Предыдущий AI-разбор:\n{context.get('last_ai_breakdown') or 'Нет данных.'}\n\n"
        f"Summary документа:\n{context.get('document_summary') or 'Нет данных.'}\n\n"
        f"Последние сообщения текущего сценария:\n{_format_recent_messages(context)}"
    )


def build_urgency_check_prompt(context: Dict[str, Any]) -> str:
    return (
        "Сценарий: urgency_check.\n"
        "Задача: объясни, похоже ли это на срочную ситуацию или нет.\n"
        f"{_base_safety_instructions()}\n\n"
        "Формат ответа:\n"
        "- Краткий вывод: срочно / не срочно / недостаточно данных\n"
        "- Почему так (простыми словами, 2-4 пункта)\n"
        "- Опасные признаки, при которых нельзя ждать\n"
        "- Что сделать сейчас до связи с врачом\n\n"
        f"Текст документа:\n{context.get('last_document_text') or 'Нет данных.'}\n\n"
        f"Предыдущий AI-разбор:\n{context.get('last_ai_breakdown') or 'Нет данных.'}\n\n"
        f"Summary документа:\n{context.get('document_summary') or 'Нет данных.'}\n\n"
        f"Последние сообщения текущего сценария:\n{_format_recent_messages(context)}"
    )


def build_next_24h_plan_prompt(context: Dict[str, Any]) -> str:
    return (
        "Сценарий: next_24h_plan.\n"
        "Задача: сформируй безопасный и реалистичный план на ближайшие 24 часа.\n"
        f"{_base_safety_instructions()}\n\n"
        "Формат ответа:\n"
        "- Шаги на ближайшие 1-2 часа\n"
        "- Шаги на оставшийся день\n"
        "- Что наблюдать по самочувствию\n"
        "- Когда обращаться за срочной помощью\n\n"
        f"Текст документа:\n{context.get('last_document_text') or 'Нет данных.'}\n\n"
        f"Предыдущий AI-разбор:\n{context.get('last_ai_breakdown') or 'Нет данных.'}\n\n"
        f"Summary документа:\n{context.get('document_summary') or 'Нет данных.'}\n\n"
        f"Последние сообщения текущего сценария:\n{_format_recent_messages(context)}"
    )


def build_questions_for_doctor_prompt(context: Dict[str, Any]) -> str:
    return (
        "Сценарий: questions_for_doctor.\n"
        "Задача: подготовь вопросы, которые пациенту полезно задать врачу на приёме.\n"
        f"{_base_safety_instructions()}\n\n"
        "Формат ответа:\n"
        "- 6-10 приоритетных вопросов к врачу\n"
        "- Какие документы/данные взять с собой\n"
        "- Как коротко и понятно описать жалобы на приёме\n\n"
        f"Текст документа:\n{context.get('last_document_text') or 'Нет данных.'}\n\n"
        f"Предыдущий AI-разбор:\n{context.get('last_ai_breakdown') or 'Нет данных.'}\n\n"
        f"Summary документа:\n{context.get('document_summary') or 'Нет данных.'}\n\n"
        f"Последние сообщения текущего сценария:\n{_format_recent_messages(context)}"
    )


def build_patient_action_prompt(action: str, context: Dict[str, Any]) -> str:
    builders = {
        "explain_document": build_explain_document_prompt,
        "urgency_check": build_urgency_check_prompt,
        "next_24h_plan": build_next_24h_plan_prompt,
        "questions_for_doctor": build_questions_for_doctor_prompt,
    }
    builder = builders.get(action, build_explain_document_prompt)
    return builder(context)
