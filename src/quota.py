from datetime import datetime

from sqlalchemy import and_, update
from sqlalchemy.exc import IntegrityError

from src.db.models import QuotaSnapshot, UsageStats
from src.db.session import get_session

MAX_DOCS_PER_MONTH = 12  # basic-тариф


def _current_month() -> str:
    # формат: "2025-11"
    return datetime.utcnow().strftime("%Y-%m")


def current_month() -> str:
    """Публичная функция, чтобы использовать в других модулях."""
    return _current_month()


# ===== ЛИМИТ ДОКУМЕНТОВ (Basic) =====


def _get_or_create_quota(session, user_id: int, month: str) -> QuotaSnapshot:
    snapshot = (
        session.query(QuotaSnapshot)
        .filter(QuotaSnapshot.user_id == user_id, QuotaSnapshot.month == month)
        .first()
    )
    if not snapshot:
        snapshot = QuotaSnapshot(user_id=user_id, month=month)
        session.add(snapshot)
        session.flush()
    return snapshot


def get_docs_used(user_id: int) -> int:
    month = _current_month()
    with get_session() as session:
        snapshot = (
            session.query(QuotaSnapshot)
            .filter(
                QuotaSnapshot.user_id == user_id, QuotaSnapshot.month == month
            )
            .first()
        )
        return snapshot.used_docs if snapshot else 0


def can_process_document(user_id: int) -> bool:
    used = get_docs_used(user_id)
    return used < MAX_DOCS_PER_MONTH


def register_document(user_id: int) -> None:
    month = _current_month()
    with get_session() as session:
        snapshot = _get_or_create_quota(session, user_id, month)
        snapshot.used_docs = (snapshot.used_docs or 0) + 1
        session.add(snapshot)


def consume_document_quota(user_id: int) -> bool:
    """
    Атомарно пытается списать 1 документ из месячной квоты.
    Возвращает True, если списание успешно, иначе False.
    """
    month = _current_month()

    with get_session() as session:
        stmt = (
            update(QuotaSnapshot)
            .where(
                and_(
                    QuotaSnapshot.user_id == user_id,
                    QuotaSnapshot.month == month,
                    QuotaSnapshot.used_docs < MAX_DOCS_PER_MONTH,
                )
            )
            .values(used_docs=QuotaSnapshot.used_docs + 1)
        )
        result = session.execute(stmt)
        if result.rowcount and result.rowcount > 0:
            return True

        # Снапшота ещё нет -> создаём первую запись месяца.
        try:
            session.add(
                QuotaSnapshot(user_id=user_id, month=month, used_docs=1)
            )
            session.flush()
            return True
        except IntegrityError:
            # Параллельный запрос уже создал запись - пробуем атомарный апдейт ещё раз.
            session.rollback()
            with get_session() as retry_session:
                retry_result = retry_session.execute(stmt)
                return bool(
                    retry_result.rowcount and retry_result.rowcount > 0
                )


# ===== УЧЁТ СИМВОЛОВ / ТОКЕНОВ =====


def register_usage(input_chars: int, output_chars: int) -> None:
    """Копим статистику по использованным символам за месяц."""
    month = _current_month()
    with get_session() as session:
        stats = session.get(UsageStats, month)
        if not stats:
            stats = UsageStats(month=month, input_chars=0, output_chars=0)
            session.add(stats)
            session.flush()

        stats.input_chars = (stats.input_chars or 0) + input_chars
        stats.output_chars = (stats.output_chars or 0) + output_chars
        session.add(stats)


def get_month_usage(month: str = None) -> tuple[int, int]:
    """Возвращает (input_chars, output_chars) за указанный месяц или текущий."""
    if month is None:
        month = _current_month()

    with get_session() as session:
        stats = session.get(UsageStats, month)
        if not stats:
            return 0, 0
        return int(stats.input_chars or 0), int(stats.output_chars or 0)
