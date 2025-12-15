from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Подхватываем переменные окружения из .env, если они есть.
load_dotenv()


class Base(DeclarativeBase):
    """Базовый класс для ORM-моделей."""


def _build_engine(url: str):
    """
    Создаёт engine с особыми параметрами для SQLite
    (check_same_thread=False нужен для работы в разных корутинах).
    """
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(
        url, echo=False, future=True, connect_args=connect_args
    )


def get_database_url() -> str:
    """
    Возвращает строку подключения из env.
    По умолчанию используем локальный файл SQLite medall.db.
    """
    return os.getenv("DATABASE_URL", "sqlite:///medall.db")


DATABASE_URL = get_database_url()
engine = _build_engine(DATABASE_URL)
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)


@contextmanager
def get_session() -> Iterator[Session]:
    """
    Контекстный менеджер для безопасной работы с сессией:
    коммит при успехе, rollback при ошибке.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
