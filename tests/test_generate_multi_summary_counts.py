"""R72: /api/generate-multi 응답에 success_count / fail_count 요약 필드 테스트"""
import unittest
from unittest.mock import patch

from app import create_app


class TestGenerateMultiSummaryCounts(unittest.TestCase):
    """generate-multi 응답의 success_count, fail_count 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    # -- helpers --
    def _post_multi(self, styles, mock_create_side_effect):
        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False), \
             patch('services.core.ai_service.create_content', side_effect=mock_create_side_effect), \
             patch('routes.advanced_routes._fetch_youtube_content',
                   return_value=('자막', None, None, [], 'api', None)), \
             patch('routes.advanced_routes.content_service') as mock_cs:
            mock_cs.is_youtube_url.return_value = True
            mock_cs.get_video_id.return_value = 'v123'
            mock_cs.get_content_title.return_value = '테스트'
            mock_cs.truncate_text.side_effect = lambda t, m: t
            with self.app.app_context():
                self.app.config['STYLE_PROMPTS'] = {s: s for s in styles}
            return self.client.post('/api/generate-multi', json={
                'url': 'https://www.youtube.com/watch?v=v123',
                'styles': styles,
            }, headers={'Origin': 'http://localhost:3000'})

    # -- tests --
    def test_all_success(self):
        """모두 성공 시 success_count == 스타일 수, fail_count == 0"""
        ok = {'title': 't', 'content': 'c', 'html': '<p>c</p>'}
        resp = self._post_multi(['summary', 'blog_seo'], lambda *a, **kw: dict(ok))
        data = resp.get_json()
        self.assertEqual(data['success_count'], 2)
        self.assertEqual(data['fail_count'], 0)

    def test_all_fail(self):
        """모두 실패 시 success_count == 0, fail_count == 스타일 수"""
        resp = self._post_multi(
            ['summary', 'blog_seo'],
            self._always_raise,
        )
        data = resp.get_json()
        self.assertEqual(data['success_count'], 0)
        self.assertEqual(data['fail_count'], 2)

    def test_partial_fail(self):
        """부분 실패 시 각각 정확한 카운트"""
        call_count = {'n': 0}

        def _alternate(*a, **kw):
            call_count['n'] += 1
            if call_count['n'] % 2 == 0:
                raise RuntimeError('실패')
            return {'title': 't', 'content': 'c', 'html': '<p>c</p>'}

        resp = self._post_multi(['s1', 's2'], _alternate)
        data = resp.get_json()
        self.assertEqual(data['success_count'] + data['fail_count'], 2)
        self.assertGreaterEqual(data['success_count'], 1)
        self.assertGreaterEqual(data['fail_count'], 0)

    def test_single_style_success(self):
        """단일 스타일 성공"""
        ok = {'title': 't', 'content': 'c', 'html': '<p>c</p>'}
        resp = self._post_multi(['summary'], lambda *a, **kw: dict(ok))
        data = resp.get_json()
        self.assertEqual(data['success_count'], 1)
        self.assertEqual(data['fail_count'], 0)

    def test_counts_are_integers(self):
        """카운트 필드가 정수 타입"""
        ok = {'title': 't', 'content': 'c', 'html': '<p>c</p>'}
        resp = self._post_multi(['summary'], lambda *a, **kw: dict(ok))
        data = resp.get_json()
        self.assertIsInstance(data['success_count'], int)
        self.assertIsInstance(data['fail_count'], int)

    @staticmethod
    def _always_raise(*a, **kw):
        raise RuntimeError('AI 호출 실패')


if __name__ == '__main__':
    unittest.main()
