"""이메일 뉴스레터 → 콘텐츠 변환 서비스

.eml 파일 또는 포워딩된 이메일 텍스트에서 콘텐츠를 추출합니다.
"""
import email
import logging
import re
from email.header import decode_header
from typing import Any, Dict

import trafilatura

logger = logging.getLogger(__name__)


def parse_email_file(file_storage: Any) -> Dict:
    """업로드된 .eml 파일에서 제목, 본문, 발신자, 날짜를 추출합니다.

    Args:
        file_storage: Flask request.files의 FileStorage 객체

    Returns:
        {"title": str, "content": str, "source_type": "email",
         "from": str, "date": str}

    Raises:
        ValueError: 본문을 추출할 수 없는 경우
    """
    raw_bytes = file_storage.read()
    msg = email.message_from_bytes(raw_bytes)

    # 헤더 추출
    subject = _decode_header_value(msg.get('Subject', ''))
    sender = _decode_header_value(msg.get('From', ''))
    date_str = msg.get('Date', '')

    # 본문 추출 (HTML 우선 → plain text 폴백)
    body_text = _extract_body(msg)
    if not body_text or len(body_text.strip()) < 10:
        raise ValueError('이메일에서 본문을 추출할 수 없습니다.')

    return {
        'title': subject or '(제목 없음)',
        'content': body_text,
        'source_type': 'email',
        'from': sender,
        'date': date_str,
    }


def parse_forwarded_email(raw_text: str) -> Dict:
    """포워딩된 이메일 텍스트에서 헤더와 본문을 파싱합니다.

    From/Subject/Date 패턴을 찾아 헤더를 추출하고, 나머지를 본문으로 처리합니다.

    Args:
        raw_text: 포워딩된 이메일 전체 텍스트

    Returns:
        {"title": str, "content": str, "source_type": "email",
         "from": str, "date": str}

    Raises:
        ValueError: 텍스트가 비어있거나 너무 짧은 경우
    """
    if not raw_text or len(raw_text.strip()) < 10:
        raise ValueError('이메일 텍스트가 너무 짧습니다.')

    lines = raw_text.strip().split('\n')
    subject, sender, date_str, body_start = _parse_forwarded_headers(lines)

    body_text = '\n'.join(lines[body_start:]).strip()
    if not body_text:
        body_text = raw_text.strip()

    return {
        'title': subject or '(제목 없음)',
        'content': body_text,
        'source_type': 'email',
        'from': sender,
        'date': date_str,
    }


# 헤더 패턴: (매칭 정규식, 제거용 정규식, 결과 필드명)
_HEADER_PATTERNS = [
    (r'^(From|보낸\s*사람|발신자)\s*[:：]', 'sender'),
    (r'^(Subject|제목)\s*[:：]', 'subject'),
    (r'^(Date|날짜|보낸\s*날짜)\s*[:：]', 'date'),
]


def _parse_forwarded_headers(lines: list) -> tuple:
    """포워딩 이메일 상단에서 From/Subject/Date 헤더를 추출합니다."""
    subject = ''
    sender = ''
    date_str = ''
    body_start = 0

    header_end = min(len(lines), 20)
    for i, line in enumerate(lines[:header_end]):
        stripped = line.strip()
        for pattern, field in _HEADER_PATTERNS:
            if re.match(pattern, stripped, re.IGNORECASE):
                value = re.sub(pattern + r'\s*', '', stripped, flags=re.IGNORECASE)
                if field == 'sender':
                    sender = value
                elif field == 'subject':
                    subject = value
                else:
                    date_str = value
                body_start = max(body_start, i + 1)
                break

    return subject, sender, date_str, body_start


def _decode_header_value(value: str) -> str:
    """이메일 헤더의 인코딩된 값을 디코딩합니다."""
    if not value:
        return ''
    parts = decode_header(value)
    decoded = []
    for part, charset in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(charset or 'utf-8', errors='replace'))
        else:
            decoded.append(part)
    return ' '.join(decoded)


def _extract_body(msg: email.message.Message) -> str:
    """이메일 메시지에서 본문 텍스트를 추출합니다.

    HTML 파트가 있으면 trafilatura로 본문 추출, 없으면 plain text 사용.
    """
    html_body = ''
    text_body = ''

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == 'text/html' and not html_body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    html_body = payload.decode(charset, errors='replace')
            elif content_type == 'text/plain' and not text_body:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    text_body = payload.decode(charset, errors='replace')
    else:
        content_type = msg.get_content_type()
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or 'utf-8'
            decoded = payload.decode(charset, errors='replace')
            if content_type == 'text/html':
                html_body = decoded
            else:
                text_body = decoded

    # HTML 본문이 있으면 trafilatura로 텍스트 추출
    if html_body:
        extracted = trafilatura.extract(html_body, include_tables=True, include_links=False)
        if extracted and len(extracted.strip()) > 10:
            return extracted

    # plain text 폴백
    return text_body
