from __future__ import annotations

from typing import Any, Dict

from src.db.models import UserRuntimeState
from src.db.session import get_session
from src.handlers.roles import PLAN_BASIC, PLAN_PRO

# Базовые лимиты по планам (на пользователя в рамках runtime-state).
PLAN_LIMITS: Dict[str, Dict[str, Any]] = {
    PLAN_BASIC: {
        "docs": 10,
        "deep": 2,
    },
    PLAN_PRO: {
        "docs": None,
        "deep": None,
    },
}


def get_limits(plan: str) -> Dict[str, Any]:
    """Возвращает лимиты для указанного плана."""
    return PLAN_LIMITS.get(plan, PLAN_LIMITS[PLAN_BASIC])


def _load_or_create_usage_state(session, user_id: int) -> UserRuntimeState:
    state = session.get(UserRuntimeState, user_id)
    if not state:
        state = UserRuntimeState(
            user_id=user_id,
            scenario_messages=[],
        )
        session.add(state)
        session.flush()
    return state


def ensure_usage(user_id: int | None) -> Dict[str, int]:
    """Возвращает persisted usage из БД."""
    if user_id is None:
        return {"docs_used": 0, "deep_used": 0}

    with get_session() as session:
        state = _load_or_create_usage_state(session, user_id)
        return {
            "docs_used": int(state.docs_used or 0),
            "deep_used": int(state.deep_used or 0),
        }


def inc_usage(user_id: int | None, *, deep: bool) -> Dict[str, int]:
    """Инкрементирует usage в БД и возвращает актуальные счётчики."""
    if user_id is None:
        usage = {"docs_used": 1, "deep_used": 1 if deep else 0}
        return usage

    with get_session() as session:
        state = _load_or_create_usage_state(session, user_id)
        state.docs_used = int(state.docs_used or 0) + 1
        if deep:
            state.deep_used = int(state.deep_used or 0) + 1
        session.add(state)
        return {
            "docs_used": int(state.docs_used or 0),
            "deep_used": int(state.deep_used or 0),
        }
