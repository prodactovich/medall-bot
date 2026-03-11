from __future__ import annotations

from collections import deque
from typing import Any, Deque, Dict, Optional

MAX_SCENARIO_MESSAGES = 8

_PATIENT_CONTEXT_STORE: Dict[int, Dict[str, Any]] = {}


def _ensure_user_state(user_id: int) -> Dict[str, Any]:
    return _PATIENT_CONTEXT_STORE.setdefault(
        user_id,
        {
            "last_document_text": "",
            "last_ai_breakdown": "",
            "document_summary": "",
            "current_scenario": "",
            "scenario_messages": deque(maxlen=MAX_SCENARIO_MESSAGES),
        },
    )


def set_current_scenario(user_id: int, scenario: str) -> None:
    state = _ensure_user_state(user_id)
    state["current_scenario"] = scenario or ""


def set_document_text(
    user_id: int,
    text: str,
    *,
    summary: Optional[str] = None,
) -> None:
    state = _ensure_user_state(user_id)
    state["last_document_text"] = (text or "").strip()
    if summary is not None:
        state["document_summary"] = summary.strip()


def set_document_summary(user_id: int, summary: str) -> None:
    state = _ensure_user_state(user_id)
    state["document_summary"] = (summary or "").strip()


def set_last_ai_breakdown(user_id: int, text: str) -> None:
    state = _ensure_user_state(user_id)
    state["last_ai_breakdown"] = (text or "").strip()


def append_scenario_message(
    user_id: int,
    *,
    scenario: str,
    author: str,
    text: str,
) -> None:
    state = _ensure_user_state(user_id)
    messages: Deque[Dict[str, str]] = state["scenario_messages"]
    messages.append(
        {
            "scenario": scenario or "",
            "author": author,
            "text": (text or "").strip(),
        }
    )


def hydrate_from_user_data(user_id: int, user_data: Dict[str, Any]) -> None:
    state = _ensure_user_state(user_id)

    last_doc = (user_data.get("last_document_text") or "").strip()
    if last_doc:
        state["last_document_text"] = last_doc

    last_ai = (user_data.get("last_ai_breakdown") or "").strip()
    if last_ai:
        state["last_ai_breakdown"] = last_ai

    summary = (user_data.get("last_document_summary") or "").strip()
    if summary:
        state["document_summary"] = summary

    current_mode = (user_data.get("mode") or "").strip()
    if current_mode:
        state["current_scenario"] = current_mode


def build_patient_context(user_id: int) -> Optional[Dict[str, Any]]:
    state = _PATIENT_CONTEXT_STORE.get(user_id)
    if not state:
        return None

    last_document_text = (state.get("last_document_text") or "").strip()
    last_ai_breakdown = (state.get("last_ai_breakdown") or "").strip()
    document_summary = (state.get("document_summary") or "").strip()
    current_scenario = (state.get("current_scenario") or "").strip()

    if not any((last_document_text, last_ai_breakdown, document_summary)):
        return None

    scenario_messages = state.get("scenario_messages") or deque()
    recent_messages = [
        item
        for item in scenario_messages
        if item.get("scenario") == current_scenario
    ][-MAX_SCENARIO_MESSAGES:]
    if not recent_messages:
        recent_messages = list(scenario_messages)[-MAX_SCENARIO_MESSAGES:]

    return {
        "last_document_text": last_document_text,
        "last_ai_breakdown": last_ai_breakdown,
        "document_summary": document_summary,
        "current_scenario": current_scenario,
        "recent_messages": recent_messages,
    }
