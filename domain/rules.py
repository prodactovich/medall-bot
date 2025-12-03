from __future__ import annotations

from .enums import RequestType
from .models import Plan, QuotaSnapshot


def can_consume(
    plan: Plan,
    quota: QuotaSnapshot,
    request_type: RequestType,
    tokens: int = 0,
) -> bool:
    """
    Проверка, можно ли списать лимит по типу запроса и токенам.
    """
    limits = plan.limits

    if (
        request_type == RequestType.TEXT
        and limits.max_messages_per_day is not None
    ):
        if quota.used_messages >= limits.max_messages_per_day:
            return False

    if (
        request_type == RequestType.PHOTO
        and limits.max_docs_per_day is not None
    ):
        if quota.used_docs >= limits.max_docs_per_day:
            return False

    if (
        request_type == RequestType.ESSAY
        and limits.max_essays_per_day is not None
    ):
        if quota.used_essays >= limits.max_essays_per_day:
            return False

    if limits.max_tokens_per_day is not None:
        if quota.used_tokens + tokens > limits.max_tokens_per_day:
            return False

    return True


def consume(
    quota: QuotaSnapshot,
    request_type: RequestType,
    tokens: int = 0,
) -> QuotaSnapshot:
    """
    Возвращает новый snapshot с обновлёнными счетчиками.
    Не мутируем исходный объект.
    """
    updated = QuotaSnapshot(**vars(quota))

    if request_type == RequestType.TEXT:
        updated.used_messages += 1
    elif request_type == RequestType.PHOTO:
        updated.used_docs += 1
    elif request_type == RequestType.ESSAY:
        updated.used_essays += 1

    updated.used_tokens += tokens
    return updated
