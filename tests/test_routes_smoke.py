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
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>'}
        with patch('routes.blog_routes.content_service.is_youtube_url', return_value=True), \
             patch('routes.blog_routes.content_service.get_video_id', return_value='test123'), \
             patch('routes.blog_routes.content_service.get_transcript', return_value='테스트 자막 내용'), \
             patch('routes.blog_routes.content_service.get_top_comments', return_value=['댓글1', '댓글2']), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t), \
             patch('routes.blog_routes.ai_service.create_content', return_value=(fake_result, 'PROMPT')):
            res = self.client.post('/generate', json={
                'url': 'https://www.youtube.com/watch?v=test123',
                'model': 'gpt-4o-mini',
                'style': 'blog',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('content', data)
            self.assertIn('html', data)

    def test_regenerate_smoke_json(self):
        """기존 콘텐츠로 /regenerate 엔드포인트 테스트"""
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>'}
        with patch('routes.blog_routes.ai_service.create_content', return_value=(fake_result, 'PROMPT2')):
            res = self.client.post('/regenerate', json={
                'content': 'ORIGINAL CONTENT',
                'model': 'gpt-4o-mini',
                'style': 'seo',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertIn('content', data)
            self.assertIn('html', data)

    def test_generate_batch_smoke(self):
        """배치 처리 /generate-batch 엔드포인트 테스트"""
        fake_result = {'title': 'TT', 'content': 'X', 'html': '<p>X</p>'}
        with patch('routes.blog_routes.content_service.is_youtube_url', return_value=True), \
             patch('routes.blog_routes.content_service.get_video_id', return_value='test123'), \
             patch('routes.blog_routes.content_service.get_content_title', return_value='TITLE'), \
             patch('routes.blog_routes.content_service.get_transcript', return_value='테스트 자막'), \
             patch('routes.blog_routes.content_service.get_top_comments', return_value=['댓글']), \
             patch('routes.blog_routes.content_service.truncate_text', side_effect=lambda t, _max: t), \
             patch('routes.blog_routes.ai_service.create_content', return_value=(fake_result, 'PROMPT')):
            res = self.client.post('/generate-batch', json={
                'urls': ['https://www.youtube.com/watch?v=a', 'https://www.youtube.com/watch?v=b'],
                'model': 'gpt-4o-mini',
                'style': 'news',
                'apiKey': 'test-api-key'
            })
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get('success'))
            self.assertIn('results', data)
            self.assertEqual(len(data['results']), 2)


if __name__ == '__main__':
    unittest.main()
