from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp

from src.prompts import build_system_prompt

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = os.getenv(
    "DEEPSEEK_URL",
    "https://api.siliconflow.cn/v1/chat/completions",
)
DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-ai/DeepSeek-V3",
)


async def ask_deepseek(
    content: str,
    *,
    role: Optional[str] = None,
    mode: Optional[str] = None,
    doc_type: Optional[str] = None,
    emotion: Optional[str] = None,
    red_flags: Optional[List[str]] = None,
    usage_tracker: Optional[Dict[str, Any]] = None,
    plan: str = "basic",
) -> str:
    """
    Вызов DeepSeek с учётом:
    - роли/режима пользователя (пациент/врач/студент);
    - плана подписки (basic / plus / pro);
    - типа документа, эмоций и возможных красных флагов.
    """

    if not DEEPSEEK_API_KEY:
        return (
            "Извините, интеллектуальный модуль временно недоступен "
            "(не задан ключ API)."
        )

    system_prompt = build_system_prompt(
        role_desc=role,
        mode=mode,
        plan=plan,
        doc_type=doc_type,
        emotion=emotion,
        red_flags=red_flags,
    )

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content},
        ],
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    timeout = aiohttp.ClientTimeout(total=75, connect=15)
    max_attempts = 3

    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for attempt in range(1, max_attempts + 1):
                try:
                    async with session.post(
                        DEEPSEEK_URL,
                        json=payload,
                        headers=headers,
                    ) as resp:
                        resp.raise_for_status()
                        data = await resp.json()
                        break
                except (aiohttp.ClientError, asyncio.TimeoutError):
                    if attempt == max_attempts:
                        raise
                    await asyncio.sleep(2**attempt)
    except aiohttp.ClientResponseError as e:
        return (
            "DeepSeek вернул ошибку при обработке запроса. " f"Код: {e.status}"
        )
    except Exception as e:
        return (
            "Произошла сетевая ошибка при обращении к ИИ. "
            "Попробуйте ещё раз или проверьте интернет/прокси. "
            f"Детали: {e}"
        )

    try:
        answer = data["choices"][0]["message"]["content"]
    except Exception:
        return "Не удалось корректно разобрать ответ от модели."

    if usage_tracker is not None:
        usage = data.get("usage") or {}
        usage_tracker.update(usage)

    return answer
