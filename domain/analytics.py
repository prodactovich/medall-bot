from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

try:
    from src.db.models import EventLog
    from src.db.session import get_session
except Exception:
    # База может быть недоступна (например, в раннем MVP или на тестах)
    EventLog = None
    get_session = None

LOG_PATH = Path(__file__).resolve().parent / "analytics.jsonl"
LOG_MAX_BYTES = int(os.getenv("ANALYTICS_LOG_MAX_BYTES", "5242880"))
REDACT_KEYS = {
    "text",
    "raw_text",
    "request_text",
    "response_text",
    "content",
    "ai_input",
    "document_text",
    "ocr_text",
    "review_text",
}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mask(value: str) -> str:
    return f"<redacted:{len(value)}>"


def _sanitize(obj: Any, path: Iterable[str] = ()) -> Any:
    """Удаляем потенциально чувствительный контент из аналитических payload."""
    if isinstance(obj, dict):
        result: Dict[str, Any] = {}
        for key, value in obj.items():
            key_l = str(key).lower()
            if key_l in REDACT_KEYS or key_l.endswith("_text"):
                result[key] = _mask(str(value))
            else:
                result[key] = _sanitize(value, (*path, str(key)))
        return result

    if isinstance(obj, list):
        return [_sanitize(x, path) for x in obj]

    if isinstance(obj, tuple):
        return tuple(_sanitize(x, path) for x in obj)

    if isinstance(obj, str):
        # В логах не храним длинные свободные строки.
        if len(obj) > 256:
            return _mask(obj)
        return obj

    return obj


def _rotate_if_needed() -> None:
    try:
        if LOG_PATH.exists() and LOG_PATH.stat().st_size > LOG_MAX_BYTES:
            backup = LOG_PATH.with_suffix(".jsonl.1")
            if backup.exists():
                backup.unlink()
            LOG_PATH.replace(backup)
    except Exception:
        pass


def new_request_id() -> str:
    return str(uuid.uuid4())


def ensure_session_id(context) -> str:
    sid = context.user_data.get("session_id")
    if not sid:
        sid = str(uuid.uuid4())
        context.user_data["session_id"] = sid
    return sid


def track(
    event: str,
    *,
    user_id: Optional[int] = None,
    session_id: str = "",
    **fields: Any,
) -> None:
    safe_fields = _sanitize(fields or {})
    payload: Dict[str, Any] = {
        "ts": _now_ms(),
        "event": event,
        "user_id": user_id,
        "session_id": session_id,
    }
    payload.update(safe_fields)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        _rotate_if_needed()
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # Логирование не должно ломать бота
        pass

    # Пишем дублирующую запись в БД, если доступен слой данных
    if EventLog and get_session:
        try:
            with get_session() as session:
                session.add(
                    EventLog(
                        event=event,
                        user_id=user_id,
                        session_id=session_id,
                        payload=safe_fields,
                    )
                )
        except Exception:
            # Не блокируем приложение, если БД временно недоступна
            pass
