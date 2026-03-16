"""콘텐츠 통계 API — 문단 수, 헤딩 수 확장 필드 테스트."""
import unittest
from unittest.mock import patch

from app import create_app


class TestContentStatsExtended(unittest.TestCase):
    """POST /api/content/stats 의 paragraph_count, heading_count 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        self.headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:3000',
        }

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_paragraph_count(self, _mock_sb):
        """빈 줄로 구분된 문단 수를 반환한다."""
        content = "첫 번째 문단입니다.\n\n두 번째 문단입니다.\n\n세 번째 문단입니다."
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['paragraph_count'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_heading_count(self, _mock_sb):
        """마크다운 헤딩(#) 수를 반환한다."""
        content = "# 제목\n\n본문입니다.\n\n## 소제목1\n\n내용.\n\n### 소제목2\n\n내용."
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=self.headers,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['heading_count'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_no_headings(self, _mock_sb):
        """헤딩이 없으면 0을 반환한다."""
        content = "일반 텍스트만 있는 콘텐츠입니다."
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=self.headers,
        )
        data = resp.get_json()
        self.assertEqual(data['heading_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_single_paragraph(self, _mock_sb):
        """문단이 하나면 1을 반환한다."""
        content = "한 문단만 있는 텍스트."
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=self.headers,
        )
        data = resp.get_json()
        self.assertEqual(data['paragraph_count'], 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_existing_fields_preserved(self, _mock_sb):
        """기존 필드(char_count 등)가 여전히 존재한다."""
        content = "테스트 콘텐츠입니다."
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=self.headers,
        )
        data = resp.get_json()
        for key in ('char_count', 'word_count', 'sentence_count',
                     'reading_time_min', 'avg_sentence_length'):
            self.assertIn(key, data)


if __name__ == '__main__':
    unittest.main()
