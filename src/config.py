import os

from dotenv import load_dotenv

load_dotenv()

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


def validate_runtime_config() -> None:
    """Fail-fast проверка обязательных переменных окружения."""
    missing: list[str] = []

    if not TELEGRAM_TOKEN:
        missing.append("TELEGRAM_TOKEN")

    if not DEEPSEEK_API_KEY:
        missing.append("DEEPSEEK_API_KEY")

    if REQUIRE_OCR_API and not OCR_SPACE_API_KEY:
        missing.append("OCR_SPACE_API_KEY")

    if not os.getenv("DATABASE_URL"):
        missing.append("DATABASE_URL")

    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
