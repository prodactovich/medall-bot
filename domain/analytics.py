from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from src.db.models import EventLog
    from src.db.session import get_session
except Exception:
    # База может быть недоступна (например, в раннем MVP или на тестах)
    EventLog = None
    get_session = None

LOG_PATH = Path(__file__).resolve().parent / "analytics.jsonl"


def _now_ms() -> int:
    return int(time.time() * 1000)


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
    payload: Dict[str, Any] = {
        "ts": _now_ms(),
        "event": event,
        "user_id": user_id,
        "session_id": session_id,
    }
    payload.update(fields)
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
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
                        payload=fields or {},
                    )
                )
        except Exception:
            # Не блокируем приложение, если БД временно недоступна
            pass
