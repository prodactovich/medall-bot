"""
Разовая инициализация БД: создаёт таблицы согласно ORM-моделям.
Использует DATABASE_URL из .env (по умолчанию sqlite:///medall.db).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Добавляем корень проекта в sys.path, чтобы работали импорты src.*
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.db.session import Base, engine  # noqa: E402


def main() -> None:
    Base.metadata.create_all(engine)
    print("Tables created")


if __name__ == "__main__":
    main()
