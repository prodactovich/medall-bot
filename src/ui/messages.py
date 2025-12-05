from __future__ import annotations

from typing import Optional


def docs_limit_reached() -> str:
    return (
        "Вы использовали доступный лимит разборов для вашего уровня "
        "подписки.\n\n"
        "Можно продолжать пользоваться базовыми функциями или открыть "
        "MedAll PLUS / PRO в разделе подписки."
    )


def deep_limit_reached() -> str:
    return (
        "Лимит глубоких разборов в текущем уровне подписки исчерпан.\n\n"
        "Вы можете переключиться в режим тезисного объяснения или "
        "рассмотреть подключение MedAll PRO для расширенного анализа."
    )


def monthly_docs_limit(max_docs: int) -> str:
    return (
        "⚠️ Лимит обработки документов на этот месяц исчерпан.\n\n"
        f"Сейчас в базовом тарифе доступно до {max_docs} документов "
        "в месяц на одного пользователя.\n"
        "Расширенный Pro-тариф пока в разработке."
    )


def history_empty() -> str:
    return "История пока пуста. Вы ещё не отправляли документы."


def history_header() -> str:
    return "📜 История последних запросов:"


def plan_chosen(msg: str, plan_name: str, extra: Optional[str] = None) -> str:
    suffix = f"\n{extra}" if extra else ""
    return f"{msg} {plan_name}.{suffix}\nНастройки учтены."


def start_greeting() -> str:
    return (
        "Здравствуйте, я MedAll 🤖\n"
        "AI-ассистент для работы с медицинской информацией.\n\n"
        "Кто вы сейчас и как мне лучше подстроиться под вас?"
    )
