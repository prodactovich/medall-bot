from __future__ import annotations

from typing import Any, Dict

from src.handlers.roles import PLAN_BASIC, PLAN_PLUS, PLAN_PRO

# Базовые лимиты по планам (на сессию пользователя)
PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    PLAN_BASIC: {
        "docs": 10,  # сколько запросов к ИИ за сессию
        "deep": 2,  # сколько глубоких разборов (patient_deep) за сессию
    },
    PLAN_PLUS: {
        "docs": 50,
        "deep": 9999,
    },
    PLAN_PRO: {
        "docs": None,  # None = без ограничений
        "deep": None,
    },
}


def get_limits(plan: str) -> Dict[str, Any]:
    """Возвращает лимиты для указанного плана."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_BASIC])


def ensure_usage(context) -> Dict[str, int]:
    """Гарантирует наличие счётчиков usage в user_data."""
    return context.user_data.setdefault(
        "usage",
        {"docs_used": 0, "deep_used": 0},
    )


def inc_usage(usage: Dict[str, int], *, deep: bool) -> None:
    usage["docs_used"] += 1
    if deep:
        usage["deep_used"] += 1
