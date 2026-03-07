"""email_ingest_service 단위 테스트"""
import unittest

from services.email_ingest_service import parse_forwarded_email, _decode_header_value


class TestDecodeHeaderValue(unittest.TestCase):

    def test_plain_text(self):
        self.assertEqual(_decode_header_value('Hello'), 'Hello')

    def test_empty(self):
        self.assertEqual(_decode_header_value(''), '')


class TestParseForwardedEmail(unittest.TestCase):

    def test_basic(self):
        """기본 포워딩 이메일 파싱"""
        raw = 'From: sender@test.com\nSubject: 테스트 제목\nDate: 2026-01-01\n\n본문 내용입니다.'
        result = parse_forwarded_email(raw)
        self.assertEqual(result['title'], '테스트 제목')
        self.assertEqual(result['from'], 'sender@test.com')
        self.assertIn('본문', result['content'])
        self.assertEqual(result['source_type'], 'email')

    def test_korean_headers(self):
        """한국어 헤더 파싱"""
        raw = '보낸 사람: alice@test.com\n제목: 한국어 제목\n날짜: 2026-03-08\n\n내용입니다.'
        result = parse_forwarded_email(raw)
        self.assertEqual(result['title'], '한국어 제목')
        self.assertEqual(result['from'], 'alice@test.com')

    def test_no_headers(self):
        """헤더 없는 텍스트"""
        raw = '이것은 그냥 일반 텍스트입니다. 헤더가 없습니다.'
        result = parse_forwarded_email(raw)
        self.assertEqual(result['title'], '(제목 없음)')
        self.assertIn('일반 텍스트', result['content'])

    def test_empty_raises(self):
        """빈 텍스트"""
        with self.assertRaises(ValueError):
            parse_forwarded_email('')

    def test_too_short_raises(self):
        """너무 짧은 텍스트"""
        with self.assertRaises(ValueError):
            parse_forwarded_email('짧음')

    def test_body_after_headers(self):
        """헤더 이후 본문만 추출"""
        raw = 'Subject: 제목\nFrom: a@b.com\n\n여기부터 본문입니다.\n두 번째 줄.'
        result = parse_forwarded_email(raw)
        self.assertIn('여기부터 본문', result['content'])


if __name__ == '__main__':
    unittest.main()
