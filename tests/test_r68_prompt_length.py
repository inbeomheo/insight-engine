"""R68: /generate 응답에 prompt_length 필드 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestPromptLength(unittest.TestCase):
    """prompt_length가 generate 응답의 모든 경로에 포함되는지 검증."""

    def test_prompt_length_in_save_and_respond(self):
        """_save_and_respond 응답에 prompt_length가 포함된다."""
        from routes.generation_helpers import _save_and_respond
        from app import create_app

        app = create_app()
        app.config['TESTING'] = True

        mock_result = {
            'title': '테스트 제목',
            'content': '테스트 내용',
            'html': '<p>테스트</p>',
            'usage': {'input_tokens': 10, 'output_tokens': 20},
        }

        used_prompt = '이것은 테스트 프롬프트입니다. 충분히 긴 프롬프트.'

        with app.test_request_context():
            from flask import g
            g.user_id = None

            with patch.object(app, 'ai_cache', create=True) as mock_cache:
                mock_cache.put = MagicMock()

                resp = _save_and_respond(
                    result=dict(mock_result),
                    used_prompt=used_prompt,
                    comment_result=None,
                    cache_key='test-key',
                    video_id='test123',
                    params={'model': 'test-model', 'style': 'summary', 'modifiers': {}},
                    url='https://youtube.com/watch?v=test123',
                    youtube_title='테스트 영상',
                    raw_transcript='자막 텍스트',
                    transcript_source='youtube-transcript-api',
                    comments=None,
                    start_time=0,
                    transcript_segments=None,
                )

        data = resp.get_json()
        self.assertIn('prompt_length', data)
        self.assertEqual(data['prompt_length'], len(used_prompt))

    def test_prompt_length_zero_when_no_prompt(self):
        """used_prompt가 None일 때 prompt_length는 0."""
        from routes.generation_helpers import _save_and_respond
        from app import create_app

        app = create_app()
        app.config['TESTING'] = True

        mock_result = {
            'title': '제목',
            'content': '내용',
            'html': '<p>내용</p>',
            'usage': {},
        }

        with app.test_request_context():
            from flask import g
            g.user_id = None

            with patch.object(app, 'ai_cache', create=True) as mock_cache:
                mock_cache.put = MagicMock()

                resp = _save_and_respond(
                    result=dict(mock_result),
                    used_prompt=None,
                    comment_result=None,
                    cache_key='test-key',
                    video_id='vid123',
                    params={'model': 'test', 'style': 'summary', 'modifiers': {}},
                    url='https://youtube.com/watch?v=vid123',
                    youtube_title='제목',
                    raw_transcript='자막',
                    transcript_source='test',
                    comments=None,
                    start_time=0,
                    transcript_segments=None,
                )

        data = resp.get_json()
        self.assertEqual(data['prompt_length'], 0)


if __name__ == '__main__':
    unittest.main()
