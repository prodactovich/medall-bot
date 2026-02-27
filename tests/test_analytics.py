from domain.analytics import _sanitize


def test_sanitize_redacts_sensitive_text_fields() -> None:
    payload = {
        "request_text": "very sensitive text",
        "nested": {"ocr_text": "patient pii"},
        "ok": "small",
    }

    sanitized = _sanitize(payload)

    assert str(sanitized["request_text"]).startswith("<redacted:")
    assert str(sanitized["nested"]["ocr_text"]).startswith("<redacted:")
    assert sanitized["ok"] == "small"


def test_sanitize_masks_long_free_text() -> None:
    payload = {"note": "x" * 300}

    sanitized = _sanitize(payload)

    assert str(sanitized["note"]).startswith("<redacted:")
