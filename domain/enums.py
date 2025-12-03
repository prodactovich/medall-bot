from enum import StrEnum


class RoleCode(StrEnum):
    PATIENT = "patient"
    DOCTOR = "doctor"
    STUDENT = "student"


class PlanCode(StrEnum):
    BASIC = "basic"
    PLUS = "plus"
    PRO = "pro"


class RequestType(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    ESSAY = "essay"
    GUIDELINE = "guideline"
    TRANSLATION = "translation"


class RequestStatus(StrEnum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"


class DocumentType(StrEnum):
    LAB = "lab"
    URINE = "urine"
    HORMONE = "hormone"
    TUMOR = "tumor_marker"
    IMAGE = "image"
    OTHER = "other"
