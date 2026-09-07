"""article_service 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.content.article_service import (
    MAX_ARTICLE_BYTES,
    _get_from_resolved_url,
    fetch_article,
)
from utils.url_safety import ResolvedPublicURL


_PUBLIC_TARGET = ResolvedPublicURL(
    scheme='https',
    hostname='example.com',
    port=443,
    ip='93.184.216.34',
    request_target='/news',
    host_header='example.com',
)


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
        patch("services.content.article_service.resolve_public_url", return_value=_PUBLIC_TARGET),
        patch(
            "services.content.article_service._get_from_resolved_url",
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
        patch("services.content.article_service.resolve_public_url", return_value=_PUBLIC_TARGET),
        patch(
            "services.content.article_service._get_from_resolved_url",
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
        patch("services.content.article_service.resolve_public_url", return_value=_PUBLIC_TARGET),
        patch(
            "services.content.article_service._get_from_resolved_url",
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
        patch("services.content.article_service.resolve_public_url", return_value=_PUBLIC_TARGET),
        patch(
            "services.content.article_service._get_from_resolved_url",
            return_value=_FakeResponse(
                b'{"ok": true}',
                headers={"Content-Type": "application/json"},
            ),
        ),
    ):
        with pytest.raises(ValueError, match="HTML 문서만 가져올 수 있습니다"):
            fetch_article("https://example.com/data.json")


def test_fetch_article_connects_to_the_ip_returned_by_final_dns_validation():
    html = (
        b'<html><body><article><p>'
        + b'public article body ' * 5
        + b'</p></article></body></html>'
    )
    rebound_safe_target = ResolvedPublicURL(
        scheme='http',
        hostname='rebind.example',
        port=80,
        ip='203.0.113.10',
        request_target='/article',
        host_header='rebind.example',
    )

    with (
        patch("services.content.article_service.is_safe_public_url", return_value=True),
        patch(
            "services.content.article_service.resolve_public_url",
            return_value=rebound_safe_target,
        ),
        patch(
            "services.content.article_service._get_from_resolved_url",
            return_value=_FakeResponse(html),
        ) as get_resolved,
    ):
        fetch_article('http://rebind.example/article')

    assert get_resolved.call_args.args[0].ip == '203.0.113.10'


def test_synthetic_requests_response_iter_content_uses_buffered_body():
    """실제 requests.Response가 raw=None이어도 iter_content가 동작합니다."""
    target = ResolvedPublicURL(
        scheme='http',
        hostname='example.com',
        port=80,
        ip='93.184.216.34',
        request_target='/article',
        host_header='example.com',
    )
    body = b'<html><body>buffered article</body></html>'
    raw_response = MagicMock(
        status=200,
        reason='OK',
        getheaders=MagicMock(return_value=[('Content-Type', 'text/html')]),
        read=MagicMock(return_value=body),
    )
    connection = MagicMock()
    connection.getresponse.return_value = raw_response
    sock = MagicMock()

    with (
        patch('services.content.article_service._connect_to_ip', return_value=sock),
        patch(
            'services.content.article_service.http.client.HTTPConnection',
            return_value=connection,
        ),
    ):
        response = _get_from_resolved_url(target, {}, (1, 2))

    assert response.raw is None
    assert b''.join(response.iter_content(chunk_size=7)) == body
    assert response._content_consumed is True
