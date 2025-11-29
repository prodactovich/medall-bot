import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "medall.db")
MAX_DOCS_PER_MONTH = 12  # basic-тариф


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    # таблица лимитов по документам
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS user_quota (
            user_id INTEGER NOT NULL,
            month   TEXT    NOT NULL,
            docs_used INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, month)
        )
        """
    )
    # таблица общей статистики использования символов
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_stats (
            month TEXT PRIMARY KEY,
            input_chars INTEGER NOT NULL DEFAULT 0,
            output_chars INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    return conn


def _current_month() -> str:
    # формат: "2025-11"
    return datetime.utcnow().strftime("%Y-%m")


def current_month() -> str:
    """Публичная функция, чтобы использовать в других модулях."""
    return _current_month()


# ===== ЛИМИТ ДОКУМЕНТОВ (Basic) =====

def get_docs_used(user_id: int) -> int:
    month = _current_month()
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT docs_used FROM user_quota WHERE user_id=? AND month=?",
            (user_id, month),
        )
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def can_process_document(user_id: int) -> bool:
    used = get_docs_used(user_id)
    return used < MAX_DOCS_PER_MONTH


def register_document(user_id: int) -> None:
    month = _current_month()
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT docs_used FROM user_quota WHERE user_id=? AND month=?",
            (user_id, month),
        )
        row = cur.fetchone()

        if row:
            docs_used = row[0] + 1
            conn.execute(
                "UPDATE user_quota SET docs_used=? WHERE user_id=? AND month=?",
                (docs_used, user_id, month),
            )
        else:
            docs_used = 1
            conn.execute(
                "INSERT INTO user_quota (user_id, month, docs_used) VALUES (?, ?, ?)",
                (user_id, month, docs_used),
            )

        conn.commit()
    finally:
        conn.close()


# ===== УЧЁТ СИМВОЛОВ / ТОКЕНОВ =====

def register_usage(input_chars: int, output_chars: int) -> None:
    """Копим статистику по использованным символам за месяц."""
    month = _current_month()
    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT input_chars, output_chars FROM usage_stats WHERE month=?",
            (month,),
        )
        row = cur.fetchone()

        if row:
            in_chars = row[0] + input_chars
            out_chars = row[1] + output_chars
            conn.execute(
                "UPDATE usage_stats "
                "SET input_chars=?, output_chars=? "
                "WHERE month=?",
                (in_chars, out_chars, month),
            )
        else:
            conn.execute(
                "INSERT INTO usage_stats (month, input_chars, output_chars) "
                "VALUES (?, ?, ?)",
                (month, input_chars, output_chars),
            )

        conn.commit()
    finally:
        conn.close()


def get_month_usage(month: str = None) -> tuple[int, int]:
    """Возвращает (input_chars, output_chars) за указанный месяц или текущий."""
    if month is None:
        month = _current_month()

    conn = _get_conn()
    try:
        cur = conn.execute(
            "SELECT input_chars, output_chars FROM usage_stats WHERE month=?",
            (month,),
        )
        row = cur.fetchone()
        if not row:
            return 0, 0
        return int(row[0]), int(row[1])
    finally:
        conn.close()