from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from math import ceil
from typing import Deque, Dict, Tuple

# Глобальный лимит параллельных OCR-операций.
OCR_MAX_CONCURRENCY = max(1, int(os.getenv("OCR_MAX_CONCURRENCY", "3")))
OCR_SEMAPHORE = asyncio.Semaphore(OCR_MAX_CONCURRENCY)


def check_rate_limit(
    context,
    *,
    user_id: int,
    channel: str,
    limit: int,
    window_seconds: int,
) -> Tuple[bool, int]:
    """
    Простой in-memory sliding window rate limiter.
    Возвращает:
    - allowed: можно ли обработать запрос;
    - retry_after: через сколько секунд можно повторить (если blocked).
    """
    now = time.monotonic()
    bot_data = context.application.bot_data
    buckets: Dict[str, Deque[float]] = bot_data.setdefault("rate_limits", {})
    key = f"{channel}:{user_id}"
    bucket = buckets.setdefault(key, deque())

    while bucket and (now - bucket[0]) > window_seconds:
        bucket.popleft()

    if len(bucket) >= limit:
        retry_after = max(1, ceil(window_seconds - (now - bucket[0])))
        return False, retry_after

    bucket.append(now)
    return True, 0
