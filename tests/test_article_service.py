"""article_service 단위 테스트."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from services.content.article_service import MAX_ARTICLE_BYTES, fetch_article


class _FakeResponse:
    def __init__(
        self,
        body: bytes = b"",
        headers: dict | None = None,
        encoding: str = "utf-8",
    ):
        self.status_code = 200
        self.headers = headers or {"Content-Type": "text/html"}
        self.encoding = encoding
        self.content = body
        self.closed = False

    def iter_content(self, chunk_size: int):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]

    def raise_for_status(self):
        return None

    def close(self):
        self.closed = True


def test_fetch_article_extracts_article_tag():
    html = """
    <html>
      <head><meta property="og:title" content="테스트 아티클"></head>
      <body>
        <nav>메뉴</nav>
        <article>
          <p>첫 번째 문단입니다. 충분한 길이의 본문입니다.</p>
          <p>두 번째 문단입니다. 아티클 본문으로 함께 추출됩니다.</p>
        </article>
        <footer>푸터</footer>
      </body>
    </html>
    """.encode()

    with (
        patch("services.content.article_service.is_safe_public_url", return_value=True),
        patch(
            "services.content.article_service.requests.get",
            return_value=_FakeResponse(html),
        ),
    ):
        result = fetch_article("https://example.com/news")

    assert result["title"] == "테스트 아티클"
    assert "첫 번째 문단" in result["text"]
    assert "두 번째 문단" in result["text"]
    assert "메뉴" not in result["text"]
    assert result["source_meta"]["source_type"] == "article"


def test_fetch_article_rejects_file_scheme():
    with pytest.raises(ValueError, match="http 또는 https"):
        fetch_article("file:///etc/passwd")


def test_fetch_article_rejects_private_ip():
    with pytest.raises(ValueError, match="안전하지 않은 URL"):
        fetch_article("http://127.0.0.1/admin")


def test_fetch_article_rejects_oversized_response():
    headers = {
        "Content-Type": "text/html",
        "Content-Length": str(MAX_ARTICLE_BYTES + 1),
    }

    with (
        patch("services.content.article_service.is_safe_public_url", return_value=True),
        patch(
            "services.content.article_service.requests.get",
            return_value=_FakeResponse(b"", headers=headers),
        ),
    ):
        with pytest.raises(ValueError, match="페이지가 너무 큽니다"):
            fetch_article("https://example.com/huge")


def test_fetch_article_detects_euc_kr_meta_charset_without_header_charset():
    korean_text = (
        "한글 본문이 깨지지 않아야 합니다. 메타 charset 기반 자동 감지를 확인합니다. "
        * 3
    )
    html = f"""
    <html>
      <head>
        <meta charset="euc-kr">
        <title>인코딩 테스트</title>
      </head>
      <body><article><p>{korean_text}</p></article></body>
    </html>
    """.encode("euc-kr")

    with (
        patch("services.content.article_service.is_safe_public_url", return_value=True),
        patch(
            "services.content.article_service.requests.get",
            return_value=_FakeResponse(
                html,
                headers={"Content-Type": "text/html"},
                encoding="ISO-8859-1",
            ),
        ),
    ):
        result = fetch_article("https://example.com/euc-kr")

    assert "한글 본문이 깨지지 않아야 합니다" in result["text"]
    assert result["title"] == "인코딩 테스트"


def test_fetch_article_rejects_non_html_content_type():
    with (
        patch("services.content.article_service.is_safe_public_url", return_value=True),
        patch(
            "services.content.article_service.requests.get",
            return_value=_FakeResponse(
                b'{"ok": true}',
                headers={"Content-Type": "application/json"},
            ),
        ),
    ):
        with pytest.raises(ValueError, match="HTML 문서만 가져올 수 있습니다"):
            fetch_article("https://example.com/data.json")
