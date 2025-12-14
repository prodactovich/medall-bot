from __future__ import annotations

import re


def strip_markdown_artifacts(text: str) -> str:
    """
    Удаляет или заменяет Markdown-артефакты:
    - убирает заголовки на решётках;
    - убирает жирное/курсивное выделение на звёздочках/подчёркиваниях;
    - заменяет списки на звёздочках на списки с дефисами;
    - убирает одиночные/двойные звёздочки в начале строки.
    """
    if not text:
        return text

    cleaned = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    cleaned = re.sub(r"\*{1,3}(.*?)\*{1,3}", r"\1", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"__([^_]+)__", r"\1", cleaned)
    cleaned = re.sub(r"^\s*\*\s+", "- ", cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r"^\s*\*+\s*", "", cleaned, flags=re.MULTILINE)
    return cleaned


def strip_control_chars(text: str) -> str:
    """
    Убирает непечатные управляющие символы, которые могут прийти от модели
    (например, \x01), но сохраняет переводы строк/табуляции.
    """
    if not text:
        return text
    return "".join(ch for ch in text if ch.isprintable() or ch in "\n\r\t")
