"""R89: /api/version에 started_at (서버 시작 시간 ISO 8601) 테스트."""
import unittest
from datetime import datetime, timezone

from app import create_app


class TestVersionStartedAt(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_started_at_exists(self):
        """응답에 started_at 필드 포함."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIn('started_at', data)

    def test_started_at_is_string(self):
        """started_at은 문자열."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        self.assertIsInstance(data['started_at'], str)

    def test_started_at_is_iso8601(self):
        """started_at이 ISO 8601 형식으로 파싱 가능."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        parsed = datetime.fromisoformat(data['started_at'])
        self.assertIsNotNone(parsed)

    def test_started_at_in_past(self):
        """started_at이 현재보다 과거."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        started = datetime.fromisoformat(data['started_at'])
        now = datetime.now(timezone.utc)
        self.assertLessEqual(started, now)

    def test_started_at_contains_timezone(self):
        """started_at에 타임존 정보 포함 (+00:00 등)."""
        resp = self.client.get('/api/version')
        data = resp.get_json()
        parsed = datetime.fromisoformat(data['started_at'])
        self.assertIsNotNone(parsed.tzinfo)


if __name__ == '__main__':
    unittest.main()
