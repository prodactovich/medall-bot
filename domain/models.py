from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

from .enums import DocumentType, PlanCode, RequestStatus, RequestType, RoleCode


@dataclass(frozen=True)
class PlanLimits:
    max_messages_per_day: Optional[int]
    max_docs_per_day: Optional[int]
    max_essays_per_day: Optional[int]
    max_tokens_per_day: Optional[int] = None  # None = без лимита


@dataclass(frozen=True)
class Plan:
    id: int
    code: PlanCode
    name: str
    limits: PlanLimits


@dataclass
class User:
    id: int
    telegram_id: int
    role: RoleCode
    plan: PlanCode
    created_at: datetime
    updated_at: datetime


@dataclass
class Subscription:
    id: int
    user_id: int
    plan: PlanCode
    start_date: datetime
    end_date: Optional[datetime]
    is_active: bool
    auto_renew: bool
    payment_id: Optional[str] = None


@dataclass
class QuotaSnapshot:
    user_id: int
    date: date  # UTC day
    used_messages: int = 0
    used_docs: int = 0
    used_essays: int = 0
    used_tokens: int = 0


@dataclass
class Document:
    id: int
    user_id: int
    telegram_file_id: str
    doc_type: DocumentType
    created_at: datetime


@dataclass
class Request:
    id: int
    user_id: int
    role: RoleCode
    plan: PlanCode
    request_type: RequestType
    status: RequestStatus
    request_text: str
    response_text: Optional[str]
    tokens_used: int
    created_at: datetime
    document_id: Optional[int] = None


@dataclass
class LogEntry:
    id: int
    user_id: Optional[int]
    log_type: str
    message: str
    created_at: datetime
    metadata: Optional[dict] = None
