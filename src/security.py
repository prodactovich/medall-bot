from __future__ import annotations

import asyncio
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Deque, Dict, Tuple

from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError

from src.db.models import RateLimitBucket
from src.db.session import get_session

# Глобальный лимит параллельных OCR-операций.
OCR_MAX_CONCURRENCY = max(1, int(os.getenv("OCR_MAX_CONCURRENCY", "3")))
OCR_SEMAPHORE = asyncio.Semaphore(OCR_MAX_CONCURRENCY)


def cleanup_rate_limit_buckets() -> int:
    """
    Удаляет просроченные rate-limit buckets.
    Возвращает количество удалённых строк.
    """
    now = datetime.now(timezone.utc)
    with get_session() as session:
        result = session.execute(
            delete(RateLimitBucket).where(RateLimitBucket.expires_at <= now)
        )
        return int(result.rowcount or 0)


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
    key = f"{channel}:{user_id}"
    now = datetime.now(timezone.utc)

    try:
        with get_session() as session:
            bucket = session.get(RateLimitBucket, key)

            # TTL-окно истекло или записи нет -> начинаем новое окно.
            if not bucket or bucket.expires_at <= now:
                expires_at = now + timedelta(seconds=window_seconds)
                if not bucket:
                    session.add(
                        RateLimitBucket(
                            key=key,
                            count=1,
                            expires_at=expires_at,
                        )
                    )
                else:
                    bucket.count = 1
                    bucket.expires_at = expires_at
                    session.add(bucket)
                return True, 0

            if bucket.count >= limit:
                retry_after = max(
                    1, ceil((bucket.expires_at - now).total_seconds())
                )
                return False, retry_after

            bucket.count += 1
            session.add(bucket)
            return True, 0
    except IntegrityError:
        # Редкий race на создании bucket: повторяем один раз.
        with get_session() as retry_session:
            bucket = retry_session.get(RateLimitBucket, key)
            if not bucket or bucket.expires_at <= now:
                expires_at = now + timedelta(seconds=window_seconds)
                if not bucket:
                    retry_session.add(
                        RateLimitBucket(
                            key=key,
                            count=1,
                            expires_at=expires_at,
                        )
                    )
                else:
                    bucket.count = 1
                    bucket.expires_at = expires_at
                    retry_session.add(bucket)
                return True, 0

            if bucket.count >= limit:
                retry_after = max(
                    1, ceil((bucket.expires_at - now).total_seconds())
                )
                return False, retry_after

            bucket.count += 1
            retry_session.add(bucket)
            return True, 0
    except Exception:
        # Fallback: не блокируем трафик полностью при временных проблемах БД.
        now_mono = time.monotonic()
        bot_data = context.application.bot_data
        buckets: Dict[str, Deque[float]] = bot_data.setdefault(
            "rate_limits_fallback",
            {},
        )
        bucket = buckets.setdefault(key, deque())
        while bucket and (now_mono - bucket[0]) > window_seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = max(1, ceil(window_seconds - (now_mono - bucket[0])))
            return False, retry_after
        bucket.append(now_mono)
        return True, 0
