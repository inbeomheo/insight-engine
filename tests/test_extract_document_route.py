"""Document text extraction API tests."""
from __future__ import annotations

from io import BytesIO
from unittest.mock import patch

from app import create_app

_H = {"Origin": "http://localhost:3000"}
PDF_MIME = "application/pdf"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
DOCUMENT_ONLY_ERROR = "PDF, DOCX, PPTX \ud30c\uc77c\ub9cc \uc5c5\ub85c\ub4dc\ud560 \uc218 \uc788\uc2b5\ub2c8\ub2e4."


def _app_client():
    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False})
    return app, app.test_client()


def _no_auth_patch():
    return patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    )


def _minimal_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n% route validation fixture\n"


def _minimal_zip_bytes() -> bytes:
    return b"PK\x03\x04 route validation fixture\n"


def _doc(text: str, pages: int = 1) -> dict:
    return {
        "title": "sample",
        "content": text,
        "source_type": "document",
        "page_count": pages,
    }


def _upload(client, content: bytes, filename: str = "sample.pdf", content_type: str = PDF_MIME):
    return client.post(
        "/api/extract-document",
        data={"file": (BytesIO(content), filename, content_type)},
        content_type="multipart/form-data",
        headers=_H,
    )


def test_extract_document_missing_file_field_returns_400_korean_message():
    _, client = _app_client()

    with _no_auth_patch():
        resp = client.post(
            "/api/extract-document",
            data={},
            content_type="multipart/form-data",
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "\ubb38\uc11c \ud30c\uc77c\uc744 \uc5c5\ub85c\ub4dc\ud574 \uc8fc\uc138\uc694."


def test_extract_document_pdf_happy_path_returns_text_pages_and_truncation_false():
    _, client = _app_client()
    text = "This is a readable PDF for direct text reuse. " * 3

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc(text, pages=2),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 200
    data = resp.get_json()
    assert "readable PDF" in data["text"]
    assert data["pages"] == 2
    assert data["truncated"] is False


def test_extract_document_docx_happy_path_accepts_zip_magic():
    _, client = _app_client()
    text = "This is readable DOCX content for direct text reuse. " * 3

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc(text, pages=4),
        ),
    ):
        resp = _upload(client, _minimal_zip_bytes(), "sample.docx", DOCX_MIME)

    assert resp.status_code == 200
    data = resp.get_json()
    assert "readable DOCX" in data["text"]
    assert data["pages"] == 4
    assert data["truncated"] is False


def test_extract_document_pptx_happy_path_accepts_zip_magic():
    _, client = _app_client()
    text = "This is readable PPTX slide content for direct text reuse. " * 3

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc(text, pages=7),
        ),
    ):
        resp = _upload(client, _minimal_zip_bytes(), "slides.pptx", PPTX_MIME)

    assert resp.status_code == 200
    data = resp.get_json()
    assert "readable PPTX" in data["text"]
    assert data["pages"] == 7
    assert data["truncated"] is False


def test_extract_document_rejects_unsupported_extension_with_korean_message():
    _, client = _app_client()

    with _no_auth_patch():
        resp = _upload(client, b"not a document", filename="note.txt", content_type="text/plain")

    assert resp.status_code == 400
    assert resp.get_json()["error"] == DOCUMENT_ONLY_ERROR


def test_extract_document_rejects_pdf_wrong_magic_with_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch("services.content.document_ingest_service.extract_from_upload") as mock_extract,
    ):
        resp = _upload(client, b"not a pdf", "sample.pdf", PDF_MIME)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == DOCUMENT_ONLY_ERROR
    mock_extract.assert_not_called()


def test_extract_document_rejects_docx_wrong_magic_with_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch("services.content.document_ingest_service.extract_from_upload") as mock_extract,
    ):
        resp = _upload(client, b"not a zip", "sample.docx", DOCX_MIME)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == DOCUMENT_ONLY_ERROR
    mock_extract.assert_not_called()


def test_extract_document_rejects_pptx_wrong_magic_with_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch("services.content.document_ingest_service.extract_from_upload") as mock_extract,
    ):
        resp = _upload(client, _minimal_pdf_bytes(), "slides.pptx", PPTX_MIME)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == DOCUMENT_ONLY_ERROR
    mock_extract.assert_not_called()


def test_extract_document_rejects_oversized_file_with_limit_message():
    _, client = _app_client()
    oversized = b"%PDF-1.4\n" + (b"A" * 32)

    with _no_auth_patch(), patch("config.DOCUMENT_UPLOAD_MAX_BYTES", 20):
        resp = _upload(client, oversized)

    assert resp.status_code == 400
    assert "\ucd5c\ub300 20\ubc14\uc774\ud2b8" in resp.get_json()["error"]


def test_extract_document_rejects_text_too_short_with_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc("Too short."),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 400
    assert "\ucda9\ubd84\ud55c \ud14d\uc2a4\ud2b8" in resp.get_json()["error"]
    assert "\uc2a4\uce94 \uc774\ubbf8\uc9c0 \ubb38\uc11c" in resp.get_json()["error"]


def test_extract_document_encrypted_pdf_service_error_passthrough():
    _, client = _app_client()
    message = "\uc554\ud638\ud654\ub41c PDF \ud30c\uc77c\uc740 \uc9c0\uc6d0\ud558\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4."

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            side_effect=ValueError(message),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 400
    assert resp.get_json()["error"] == message


def test_extract_document_read_error_sanitizes_internal_detail():
    _, client = _app_client()
    generic = "PDF \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. \ud30c\uc77c\uc774 \uc190\uc0c1\ub418\uc5c8\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4."

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            side_effect=ValueError("PDF \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: EOF marker not found"),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 400
    assert resp.get_json()["error"] == generic
    assert "EOF" not in resp.get_json()["error"]


def test_extract_document_docx_read_error_sanitizes_internal_detail():
    _, client = _app_client()
    generic = "DOCX \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. \ud30c\uc77c\uc774 \uc190\uc0c1\ub418\uc5c8\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4."

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            side_effect=ValueError("DOCX \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: bad zip"),
        ),
    ):
        resp = _upload(client, _minimal_zip_bytes(), "sample.docx", DOCX_MIME)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == generic
    assert "bad zip" not in resp.get_json()["error"]


def test_extract_document_pptx_read_error_sanitizes_internal_detail():
    _, client = _app_client()
    generic = "PPTX \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4. \ud30c\uc77c\uc774 \uc190\uc0c1\ub418\uc5c8\uc744 \uc218 \uc788\uc2b5\ub2c8\ub2e4."

    with (
        _no_auth_patch(),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            side_effect=ValueError("PPTX \ud30c\uc77c\uc744 \uc77d\uc744 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4: missing presentation part"),
        ),
    ):
        resp = _upload(client, _minimal_zip_bytes(), "slides.pptx", PPTX_MIME)

    assert resp.status_code == 400
    assert resp.get_json()["error"] == generic
    assert "missing presentation part" not in resp.get_json()["error"]


def test_extract_document_normalizes_text_while_preserving_paragraphs():
    _, client = _app_client()
    raw = "First   paragraph\tline\r\nstill first.\r\n\r\nSecond\t\tparagraph\n\n\n\nThird    paragraph"

    with (
        _no_auth_patch(),
        patch("config.DIRECT_TEXT_MIN_CHARS", 10),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc(raw),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 200
    text = resp.get_json()["text"]
    assert text == "First paragraph line\nstill first.\n\nSecond paragraph\n\nThird paragraph"
    assert "\r" not in text
    assert "   " not in text
    assert "\t" not in text
    assert "\n\n\n" not in text
    assert "\n\n" in text


def test_extract_document_truncates_at_direct_text_max_chars():
    _, client = _app_client()
    text = "Alpha beta gamma delta " * 20

    with (
        _no_auth_patch(),
        patch("config.DIRECT_TEXT_MIN_CHARS", 10),
        patch("config.DIRECT_TEXT_MAX_CHARS", 80),
        patch(
            "services.content.document_ingest_service.extract_from_upload",
            return_value=_doc(text),
        ),
    ):
        resp = _upload(client, _minimal_pdf_bytes())

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["truncated"] is True
    assert len(data["text"]) == 80
