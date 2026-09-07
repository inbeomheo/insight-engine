"""AI 생성 응답에 내부 프롬프트 메타데이터가 노출되지 않는지 검증."""
import unittest
from unittest.mock import patch, MagicMock


class TestPromptPrivacy(unittest.TestCase):
    """프롬프트 본문과 길이를 클라이언트에 반환하지 않음."""

    def test_prompt_metadata_removed_from_save_and_respond(self):
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
        self.assertNotIn('prompt', data)
        self.assertNotIn('prompt_length', data)

    def test_prompt_metadata_absent_when_no_prompt(self):
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
        self.assertNotIn('prompt', data)
        self.assertNotIn('prompt_length', data)


if __name__ == '__main__':
    unittest.main()
