"""RAG 파일 파서 격리 경계 회귀 테스트."""
import os
from unittest.mock import patch

import pytest

from services.rag.chunker import extract_text_from_file


def test_pdf_uses_document_ingest_worker_contract_and_cleans_temp_file():
    observed_path = None

    def safe_extract(path, mime_type):
        nonlocal observed_path
        observed_path = path
        assert mime_type == "application/pdf"
        assert os.path.exists(path)
        assert oct(os.stat(path).st_mode & 0o777) == "0o600"
        with open(path, "rb") as pdf_file:
            assert pdf_file.read() == b"%PDF-safe-test"
        return {"content": "격리된 PDF 텍스트"}

    with patch(
        "services.content.document_ingest_service.extract_text",
        side_effect=safe_extract,
    ) as extract:
        result = extract_text_from_file(b"%PDF-safe-test", "notes.pdf")

    assert result == "격리된 PDF 텍스트"
    extract.assert_called_once()
    assert observed_path is not None
    assert not os.path.exists(observed_path)


def test_pdf_parser_failure_always_cleans_temp_file():
    observed_path = None

    def fail_extract(path, _mime_type):
        nonlocal observed_path
        observed_path = path
        raise ValueError("PDF 처리 시간이 허용 한도를 초과합니다.")

    with patch(
        "services.content.document_ingest_service.extract_text",
        side_effect=fail_extract,
    ), pytest.raises(ValueError, match="처리 시간"):
        extract_text_from_file(b"%PDF-timeout", "timeout.pdf")

    assert observed_path is not None
    assert not os.path.exists(observed_path)
