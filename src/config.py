import os

from dotenv import load_dotenv

load_dotenv()


def _normalize_db_url(url: str | None) -> str | None:
    """Railway provides postgresql:// but SQLAlchemy+psycopg3 needs postgresql+psycopg://."""
    if url and url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
OCR_SPACE_API_KEY = os.getenv("OCR_SPACE_API_KEY")
REQUIRE_OCR_API = os.getenv("REQUIRE_OCR_API", "true").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
INTRO_VIDEO_PATH = os.getenv("INTRO_VIDEO_PATH", "")
INTRO_VIDEO_CAPTION = os.getenv("INTRO_VIDEO_CAPTION", "")
DATABASE_URL = _normalize_db_url(os.getenv("DATABASE_URL"))


def validate_runtime_config() -> None:
    """Fail-fast проверка обязательных переменных окружения."""
    missing: list[str] = []

    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")

    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")

    if REQUIRE_OCR_API and not OCR_SPACE_API_KEY:
        missing.append("OCR_SPACE_API_KEY")

    if not DATABASE_URL:
        missing.append("DATABASE_URL")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
