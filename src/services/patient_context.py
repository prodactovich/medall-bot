from __future__ import annotations

from typing import Any, Dict, Optional

from src.db.models import UserRuntimeState
from src.db.session import get_session

MAX_SCENARIO_MESSAGES = 8


def _load_or_create_state(session, user_id: int) -> UserRuntimeState:
    state = session.get(UserRuntimeState, user_id)
    if not state:
        state = UserRuntimeState(
            user_id=user_id,
            scenario_messages=[],
        )
        session.add(state)
        session.flush()
    return state


def set_current_scenario(user_id: int, scenario: str) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        state.current_mode = scenario or ""
        session.add(state)


def set_document_text(
    user_id: int,
    text: str,
    *,
    summary: Optional[str] = None,
) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        state.last_document_text = (text or "").strip()
        if summary is not None:
            state.last_document_summary = summary.strip()
        session.add(state)


def set_document_summary(user_id: int, summary: str) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        state.last_document_summary = (summary or "").strip()
        session.add(state)


def set_last_ai_breakdown(user_id: int, text: str) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        state.last_ai_breakdown = (text or "").strip()
        session.add(state)


def set_profile_type(user_id: int, profile_type: str | None) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        state.profile_type = profile_type
        session.add(state)


def append_scenario_message(
    user_id: int,
    *,
    scenario: str,
    author: str,
    text: str,
) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)
        messages = list(state.scenario_messages or [])
        messages.append(
            {
                "scenario": scenario or "",
                "author": author,
                "text": (text or "").strip(),
            }
        )
        state.scenario_messages = messages[-MAX_SCENARIO_MESSAGES:]
        session.add(state)


def hydrate_from_user_data(user_id: int, user_data: Dict[str, Any]) -> None:
    with get_session() as session:
        state = _load_or_create_state(session, user_id)

        last_doc = (user_data.get("last_document_text") or "").strip()
        if last_doc:
            state.last_document_text = last_doc

        last_ai = (user_data.get("last_ai_breakdown") or "").strip()
        if last_ai:
            state.last_ai_breakdown = last_ai

        summary = (user_data.get("last_document_summary") or "").strip()
        if summary:
            state.last_document_summary = summary

        current_mode = (user_data.get("mode") or "").strip()
        if current_mode:
            state.current_mode = current_mode

        profile_type = (user_data.get("profile_type") or "").strip()
        if profile_type:
            state.profile_type = profile_type

        session.add(state)


def build_patient_context(user_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as session:
        state = session.get(UserRuntimeState, user_id)
        if not state:
            return None

        last_document_text = (state.last_document_text or "").strip()
        last_ai_breakdown = (state.last_ai_breakdown or "").strip()
        document_summary = (state.last_document_summary or "").strip()
        current_scenario = (state.current_mode or "").strip()

        if not any((last_document_text, last_ai_breakdown, document_summary)):
            return None

        scenario_messages = list(state.scenario_messages or [])
        recent_messages = [
            item
            for item in scenario_messages
            if item.get("scenario") == current_scenario
        ][-MAX_SCENARIO_MESSAGES:]
        if not recent_messages:
            recent_messages = scenario_messages[-MAX_SCENARIO_MESSAGES:]

        return {
            "last_document_text": last_document_text,
            "last_ai_breakdown": last_ai_breakdown,
            "document_summary": document_summary,
            "current_scenario": current_scenario,
            "recent_messages": recent_messages,
        }
