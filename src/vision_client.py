import os
import requests

OCR_API_KEY = os.getenv("OCR_SPACE_API_KEY")
OCR_URL = "https://api.ocr.space/parse/image"


def image_to_text(file_path: str, language: str = "rus") -> str:
    """
    Отправляет изображение или PDF в OCR.Space и возвращает распознанный текст.
    language: 'rus' для русского, 'eng' для английского и т.п.
    """
    if not OCR_API_KEY:
        raise RuntimeError("OCR_SPACE_API_KEY не задан в .env")

    with open(file_path, "rb") as f:
        files = {"file": f}
        data = {
            "apikey": OCR_API_KEY,
            "language": language,
            "isOverlayRequired": False,
        }

        resp = requests.post(OCR_URL, files=files, data=data, timeout=60)
        resp.raise_for_status()
        result = resp.json()

    parsed_results = result.get("ParsedResults") or []
    if not parsed_results:
        return ""

    full_text = "\n\n".join(item.get("ParsedText", "") for item in parsed_results)
    return full_text.strip()
