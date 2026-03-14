"""이메일 뉴스레터 인제스트 서비스 테스트"""
import io
import unittest
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import patch

from services.content.email_ingest_service import parse_email_file, parse_forwarded_email


class _FakeFileStorage:
    """Flask FileStorage 모의 객체"""

    def __init__(self, data: bytes, filename: str = 'test.eml'):
        self._stream = io.BytesIO(data)
        self.filename = filename

    def read(self):
        return self._stream.read()


def _make_eml(subject='테스트 제목', sender='user@example.com',
              body_text='', body_html='', date='Mon, 1 Jan 2024 00:00:00 +0000'):
    """테스트용 .eml 바이트를 생성합니다."""
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['Date'] = date

    if body_text:
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))
    if body_html:
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    return msg.as_bytes()


class TestParseEmailFile(unittest.TestCase):
    """parse_email_file 테스트"""

    def test_plain_text_email(self):
        """plain text 이메일에서 본문과 헤더를 추출합니다."""
        eml = _make_eml(
            subject='뉴스레터 제목',
            sender='news@example.com',
            body_text='이것은 뉴스레터 본문입니다. 충분히 긴 텍스트를 포함합니다.',
        )
        result = parse_email_file(_FakeFileStorage(eml))
        self.assertEqual(result['title'], '뉴스레터 제목')
        self.assertEqual(result['source_type'], 'email')
        self.assertEqual(result['from'], 'news@example.com')
        self.assertIn('뉴스레터 본문', result['content'])

    @patch('services.email_ingest_service.trafilatura.extract')
    def test_html_email_with_trafilatura(self, mock_extract):
        """HTML 이메일에서 trafilatura로 본문을 추출합니다."""
        mock_extract.return_value = '추출된 뉴스레터 본문 내용입니다. 테스트용 충분한 텍스트.'
        eml = _make_eml(
            subject='HTML 뉴스레터',
            body_html='<html><body><p>HTML 본문</p></body></html>',
        )
        result = parse_email_file(_FakeFileStorage(eml))
        self.assertEqual(result['title'], 'HTML 뉴스레터')
        self.assertIn('추출된 뉴스레터', result['content'])

    def test_empty_body_raises_error(self):
        """본문이 없는 이메일은 ValueError를 발생시킵니다."""
        eml = _make_eml(subject='빈 메일', body_text='')
        with self.assertRaises(ValueError):
            parse_email_file(_FakeFileStorage(eml))


class TestParseForwardedEmail(unittest.TestCase):
    """parse_forwarded_email 테스트"""

    def test_korean_headers(self):
        """한국어 헤더가 포함된 포워딩 이메일을 파싱합니다."""
        text = """보낸 사람: sender@example.com
제목: 포워딩된 뉴스레터
날짜: 2024-01-01

이것은 포워딩된 이메일의 본문입니다. 충분히 긴 텍스트를 포함합니다."""
        result = parse_forwarded_email(text)
        self.assertEqual(result['title'], '포워딩된 뉴스레터')
        self.assertEqual(result['from'], 'sender@example.com')
        self.assertIn('포워딩된 이메일의 본문', result['content'])

    def test_english_headers(self):
        """영문 헤더가 포함된 포워딩 이메일을 파싱합니다."""
        text = """From: user@test.com
Subject: Weekly Digest
Date: 2024-01-15

Hello, this is the newsletter body content with enough text."""
        result = parse_forwarded_email(text)
        self.assertEqual(result['title'], 'Weekly Digest')
        self.assertEqual(result['from'], 'user@test.com')

    def test_no_headers(self):
        """헤더 없이 본문만 있는 텍스트도 처리합니다."""
        text = "이것은 그냥 텍스트입니다. 헤더가 없지만 충분히 긴 본문입니다."
        result = parse_forwarded_email(text)
        self.assertEqual(result['title'], '(제목 없음)')
        self.assertIn('텍스트', result['content'])

    def test_short_text_raises_error(self):
        """너무 짧은 텍스트는 ValueError를 발생시킵니다."""
        with self.assertRaises(ValueError):
            parse_forwarded_email('짧음')

    def test_empty_text_raises_error(self):
        """빈 텍스트는 ValueError를 발생시킵니다."""
        with self.assertRaises(ValueError):
            parse_forwarded_email('')


if __name__ == '__main__':
    unittest.main()
