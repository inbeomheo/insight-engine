import unittest
from unittest.mock import patch


class TestRoutesSmoke(unittest.TestCase):
    def setUp(self):
        from app import create_app

        self.app = create_app({
            'TESTING': True,
        })
        self.client = self.app.test_client()

    def tearDown(self):
        pass

    def test_generate_web_smoke(self):
        """YouTube URL로 /generate 엔드포인트 테스트"""
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>', 'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}}
        fake_transcript = {'text': '테스트 자막 내용', 'source': 'api'}

        def fake_create_content(content, model, style_prompt=None, return_prompt=False, modifiers=None):
            if return_prompt:
                return fake_result, 'PROMPT'
            return fake_result

        with patch('services.supabase_service.is_supabase_enabled', return_value=False), \
             patch('routes.blog_routes.content_service.is_youtube_url', return_value=True), \
             patch('routes.blog_routes.content_service.get_video_id', return_value='test123'), \
             patch('routes.blog_routes.content_service.get_content_title', return_value='테스트 영상 제목'), \
             patch('routes.blog_routes.content_service.get_transcript', return_value=fake_transcript), \
             patch('routes.blog_routes.content_service.get_top_comments', return_value=['댓글1', '댓글2']), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t), \
             patch('routes.blog_routes.ai_service.create_content', side_effect=fake_create_content):
            res = self.client.post('/generate', json={
                'url': 'https://www.youtube.com/watch?v=test123',
                'model': 'gpt-4o-mini',
                'style': 'blog_seo',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('content', data)
            self.assertIn('html', data)

    def test_regenerate_smoke_json(self):
        """기존 콘텐츠로 /regenerate 엔드포인트 테스트"""
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>'}
        with patch('services.supabase_service.is_supabase_enabled', return_value=False), \
             patch('routes.blog_routes.ai_service.create_content', return_value=(fake_result, 'PROMPT2')):
            res = self.client.post('/regenerate', json={
                'content': 'ORIGINAL CONTENT',
                'model': 'gpt-4o-mini',
                'style': 'blog_seo',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('content', data)
            self.assertIn('html', data)

    def test_generate_batch_smoke(self):
        """배치 처리 /generate-batch 엔드포인트 테스트"""
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>'}
        fake_transcript = {'text': '테스트 자막', 'source': 'api'}
        with patch('services.supabase_service.is_supabase_enabled', return_value=False), \
             patch('routes.blog_routes.content_service.is_youtube_url', return_value=True), \
             patch('routes.blog_routes.content_service.get_video_id', return_value='test123'), \
             patch('routes.blog_routes.content_service.get_content_title', return_value='TITLE'), \
             patch('routes.blog_routes.content_service.get_transcript', return_value=fake_transcript), \
             patch('routes.blog_routes.content_service.get_top_comments', return_value=['댓글']), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t), \
             patch('routes.blog_routes.ai_service.create_content', return_value=(fake_result, 'PROMPT')):
            res = self.client.post('/generate-batch', json={
                'urls': ['https://www.youtube.com/watch?v=a', 'https://www.youtube.com/watch?v=b'],
                'model': 'gpt-4o-mini',
                'style': 'summary',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('results', data)
            self.assertEqual(len(data['results']), 2)

    def test_user_history_api_requires_auth(self):
        """히스토리 API가 인증을 요구하는지 확인"""
        with patch('services.supabase_service.is_supabase_enabled', return_value=True):
            res = self.client.get('/api/user/history')
            self.assertEqual(res.status_code, 401)
            data = res.get_json()
            self.assertIn('error', data)

    def test_user_history_api_no_auth_mode(self):
        """Supabase 비활성화 시 히스토리 API 동작"""
        fake_histories = [
            {'report_id': 'r1', 'url': 'http://test.com', 'title': 'Test', 'style': 'summary',
             'html': '<p>test</p>', 'content': 'test', 'created_at': '2025-01-01T00:00:00'}
        ]
        with patch('services.supabase_service.is_supabase_enabled', return_value=False), \
             patch('routes.auth_routes.get_histories', return_value=fake_histories):
            res = self.client.get('/api/user/history')
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('histories', data)


if __name__ == '__main__':
    unittest.main()
