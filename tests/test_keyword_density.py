"""R45: /api/content/stats keyword_density 필드 테스트."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestKeywordDensity(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_keyword_density_field_exists(self, _m):
        """keyword_density 필드가 응답에 포함된다."""
        resp = self.client.post(
            '/api/content/stats',
            json={'content': '파이썬 프로그래밍 파이썬 개발 파이썬 코딩'},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('keyword_density', data)
        self.assertIsInstance(data['keyword_density'], list)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_keyword_density_top_keyword(self, _m):
        """가장 빈번한 키워드가 첫 번째로 온다."""
        content = ' '.join(['머신러닝'] * 10 + ['딥러닝'] * 5 + ['데이터'] * 3)
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=_HEADERS,
        )
        data = resp.get_json()
        kd = data['keyword_density']
        self.assertGreater(len(kd), 0)
        self.assertEqual(kd[0]['keyword'], '머신러닝')
        self.assertEqual(kd[0]['count'], 10)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_keyword_density_max_5(self, _m):
        """키워드는 최대 5개까지 반환된다."""
        words = [f'키워드{i}' for i in range(20)]
        content = ' '.join(words * 2)
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=_HEADERS,
        )
        data = resp.get_json()
        self.assertLessEqual(len(data['keyword_density']), 5)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_keyword_density_excludes_stopwords(self, _m):
        """불용어(은/는/이/가 등)가 keyword_density에 포함되지 않는다."""
        content = '이 은 는 가 를 의 에 the a an is are for of and'
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers=_HEADERS,
        )
        data = resp.get_json()
        # 모두 불용어이거나 1글자이므로 빈 리스트여야 함
        self.assertEqual(len(data['keyword_density']), 0)


if __name__ == '__main__':
    unittest.main()
