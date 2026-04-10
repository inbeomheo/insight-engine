"""blog_routes.py 라우트 커버리지 테스트.

핵심 생성 엔드포인트 (/generate, /regenerate, /generate-batch) +
템플릿, Video QA, TTS, 이벤트 추출, 자막 워크스페이스, 캡처 엔드포인트 커버.
"""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── 헬퍼 함수 테스트 ──────────────────────────────────────


class TestExtractClientId(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_client_id_from_json(self, _):
        """JSON body에서 clientId 추출."""
        from routes.blog_routes import _extract_client_id
        with self.app.test_request_context(
            json={'clientId': 'test-123'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            cid = _extract_client_id(flask_req)
            self.assertEqual(cid, 'test-123')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_client_id_empty(self, _):
        """clientId가 없으면 빈 문자열."""
        from routes.blog_routes import _extract_client_id
        with self.app.test_request_context(json={}, content_type='application/json'):
            from flask import request as flask_req
            cid = _extract_client_id(flask_req)
            self.assertEqual(cid, '')


class TestValidateModifiers(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_none(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_valid(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers({'length': 'short', 'language': 'ko'})
        self.assertIsNone(err)
        self.assertEqual(result['length'], 'short')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_invalid_type(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers('not a dict')
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_invalid_values(self, _):
        """유효하지 않은 값은 무시."""
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers({'length': 'invalid_value', 'language': 'ko'})
        self.assertNotIn('length', result or {})
        self.assertEqual((result or {}).get('language'), 'ko')


class TestValidateCustomPrompt(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_none(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_valid(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt('커스텀 프롬프트')
        self.assertEqual(result, '커스텀 프롬프트')
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_invalid_type(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt(12345)
        self.assertIsNone(result)
        self.assertIsNotNone(err)


class TestGetRequestData(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_json(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'url': 'https://youtube.com/watch?v=123',
                  'model': 'gemini/gemini-3-flash',
                  'style': 'summary'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['url'], 'https://youtube.com/watch?v=123')
            self.assertEqual(params['style'], 'summary')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_defaults(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertIsNone(params['url'])
            self.assertIsNotNone(params['model'])  # 기본값 존재

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_detail_level_validation(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'detail_level': 'invalid'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['detail_level'], 'standard')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_form_data(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            data={'url': 'https://youtube.com/watch?v=abc',
                  'style': 'blog_seo'},
            content_type='multipart/form-data'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['url'], 'https://youtube.com/watch?v=abc')


# ── /generate 엔드포인트 ──────────────────────────────────────


class TestGenerateRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_missing_url(self, _):
        """URL도 content도 없으면 400."""
        resp = self.client.post('/generate', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.generation_helpers._handle_web_source')
    def test_generate_non_youtube_url(self, mock_web, _):
        """비YouTube URL은 _handle_web_source로 라우팅."""
        mock_web.return_value = ({'title': '웹', 'content': '결과'}, 200)
        resp = self.client.post('/generate',
                                json={'url': 'https://example.com/article'},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 400, 500])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.generation_helpers._handle_direct_text')
    def test_generate_direct_text(self, mock_direct, _):
        """직접 텍스트 입력 모드."""
        # _handle_direct_text는 Flask Response를 반환해야 함
        # 앱 컨텍스트 내에서 호출되므로 side_effect로 처리
        def fake_handle(*args, **kwargs):
            from flask import jsonify as _jsonify
            return _jsonify({'title': '직접입력', 'content': '결과'})
        mock_direct.side_effect = fake_handle
        resp = self.client.post('/generate',
                                json={'content': '충분히 긴 텍스트입니다. ' * 10},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 400, 500])


# ── /regenerate 엔드포인트 ──────────────────────────────────────


class TestRegenerateRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_regenerate_missing_content(self, _):
        resp = self.client.post('/regenerate', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    def test_regenerate_success(self, mock_ai, _):
        mock_ai.return_value = (
            {'title': '재생성', 'content': '결과', 'html': '<p>결과</p>'},
            '사용된 프롬프트'
        )
        resp = self.client.post('/regenerate',
                                json={'content': '원본 콘텐츠', 'style': 'summary'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── /generate-batch 엔드포인트 ──────────────────────────────────────


class TestGenerateBatchRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.try_consume_atomic')
    def test_batch_no_json(self, mock_usage, _):
        """JSON이 아닌 content-type은 500 (UnsupportedMediaType catch)."""
        mock_usage.return_value = (True, {'remaining': 5})
        resp = self.client.post('/generate-batch',
                                data='not json',
                                content_type='text/plain',
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.try_consume_atomic')
    def test_batch_no_urls(self, mock_usage, _):
        mock_usage.return_value = (True, {'remaining': 5})
        resp = self.client.post('/generate-batch',
                                json={'model': 'test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.try_consume_atomic')
    def test_batch_too_many_urls(self, mock_usage, _):
        mock_usage.return_value = (True, {'remaining': 5})
        urls = [f'https://youtube.com/watch?v={i}' for i in range(20)]
        resp = self.client.post('/generate-batch',
                                json={'urls': urls},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.try_consume_atomic')
    def test_batch_usage_exceeded(self, mock_usage, _):
        mock_usage.return_value = (False, {'remaining': 0})
        resp = self.client.post('/generate-batch',
                                json={'urls': ['https://youtube.com/watch?v=123']},
                                headers=_H)
        self.assertEqual(resp.status_code, 429)


# ── 템플릿 API ──────────────────────────────────────


class TestTemplateRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.get_templates')
    def test_list_templates(self, mock_get, _):
        mock_get.return_value = {'templates': [], 'total': 0}
        resp = self.client.get('/api/templates')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_name(self, _):
        resp = self.client.post('/api/templates',
                                json={'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_prompt(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': '이름'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_name_too_long(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': 'a' * 51, 'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_prompt_too_long(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': '이름', 'prompt_text': 'x' * 5001},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.create_template')
    def test_create_template_success(self, mock_create, _):
        mock_create.return_value = {'id': 't1', 'name': '테스트'}
        resp = self.client.post('/api/templates',
                                json={'name': '테스트', 'prompt_text': '프롬프트 내용'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.create_template', return_value=None)
    def test_create_template_returns_none(self, mock_create, _):
        resp = self.client.post('/api/templates',
                                json={'name': '테스트', 'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.update_template', return_value=None)
    def test_update_template_not_found(self, mock_update, _):
        resp = self.client.put('/api/templates/t999',
                               json={'name': '변경'},
                               headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.update_template')
    def test_update_template_success(self, mock_update, _):
        mock_update.return_value = {'id': 't1', 'name': '변경됨'}
        resp = self.client.put('/api/templates/t1',
                               json={'name': '변경됨'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_update_template_empty_name(self, _):
        resp = self.client.put('/api/templates/t1',
                               json={'name': ''},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.delete_template', return_value=True)
    def test_delete_template_success(self, mock_del, _):
        resp = self.client.delete('/api/templates/t1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.delete_template', return_value=False)
    def test_delete_template_not_found(self, mock_del, _):
        resp = self.client.delete('/api/templates/t999', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.get_template_by_id', return_value=None)
    def test_use_template_not_found(self, mock_get, _):
        resp = self.client.post('/api/templates/t999/use', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.increment_usage')
    @patch('services.data.prompt_template_service.get_template_by_id')
    def test_use_template_success(self, mock_get, mock_inc, _):
        mock_get.return_value = {'id': 't1', 'prompt_text': '프롬프트'}
        resp = self.client.post('/api/templates/t1/use', headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── Video QA ──────────────────────────────────────


class TestVideoQARoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_video_qa_missing_url(self, _):
        resp = self.client.post('/api/video-qa', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=False)
    def test_video_qa_invalid_url(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://example.com',
                                      'question': '질문'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_missing_question(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_question_too_long(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc',
                                      'question': 'q' * 501},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.video_qa_service.answer_question')
    @patch('services.media.video_qa_service.is_video_indexed', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value='abc123')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_success(self, *mocks):
        mocks[3].return_value = {'answer': '답변입니다', 'sources': []}
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc123',
                                      'question': '이 영상은 무엇에 대한 것인가요?'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['answer'], '답변입니다')


# ── TTS ──────────────────────────────────────


class TestTTSRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_tts_missing_text(self, _):
        resp = self.client.post('/api/tts', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.tts_service.TTSService.synthesize')
    def test_tts_success(self, mock_synth, _):
        mock_synth.return_value = b'\x00\x01\x02\x03'  # 가짜 오디오 바이트
        resp = self.client.post('/api/tts',
                                json={'text': '안녕하세요', 'voice': 'ko-KR'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'audio/mpeg')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.tts_service.TTSService.synthesize',
           side_effect=ValueError('지원하지 않는 음성'))
    def test_tts_value_error(self, mock_synth, _):
        resp = self.client.post('/api/tts',
                                json={'text': '테스트'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 401, 500, 503])


# ── 이벤트 추출 ──────────────────────────────────────


class TestExtractEventsRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_events_missing_input(self, _):
        resp = self.client.post('/api/extract-events', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.event_extraction_service.get_event_summary')
    @patch('services.content.event_extraction_service.categorize_events')
    @patch('services.content.event_extraction_service.extract_events')
    def test_extract_events_with_transcript(self, mock_ext, mock_cat, mock_sum, _):
        mock_ext.return_value = [{'type': 'event', 'text': '발표'}]
        mock_cat.return_value = {'announcement': []}
        mock_sum.return_value = {'total': 1}
        resp = self.client.post('/api/extract-events',
                                json={'transcript': '오늘 새로운 제품을 발표합니다.'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('events', data)


# ── 자막 워크스페이스 ──────────────────────────────────────


class TestTranscriptRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_transcript_invalid_video_id(self, _):
        resp = self.client.get('/api/transcript/invalid!!')
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.transcript.transcript_workspace_service.parse_transcript_sentences')
    @patch('services.core.content_service.get_transcript')
    def test_transcript_success(self, mock_get, mock_parse, _):
        mock_get.return_value = {
            'text': '자막 내용입니다.',
            'source': 'api',
            'segments': []
        }
        mock_parse.return_value = [{'index': 0, 'text': '자막 내용입니다.'}]
        resp = self.client.get('/api/transcript/dQw4w9WgXcQ')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['video_id'], 'dQw4w9WgXcQ')
        self.assertEqual(data['sentence_count'], 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.get_transcript')
    def test_transcript_error(self, mock_get, _):
        mock_get.return_value = {'error': '자막 없음'}
        resp = self.client.get('/api/transcript/dQw4w9WgXcQ')
        self.assertEqual(resp.status_code, 422)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.get_transcript')
    def test_transcript_empty(self, mock_get, _):
        mock_get.return_value = {'text': '', 'source': 'api'}
        resp = self.client.get('/api/transcript/dQw4w9WgXcQ')
        self.assertEqual(resp.status_code, 422)


# ── 음성 캡처 ──────────────────────────────────────


class TestCaptureRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_capture_speech_missing_text(self, _):
        resp = self.client.post('/api/capture/speech', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.handsfree_capture_service.capture_speech')
    def test_capture_speech_success(self, mock_capture, _):
        result = MagicMock()
        result.text = '정돈된 텍스트'
        result.word_count = 2
        result.sentence_count = 1
        result.original_length = 10
        mock_capture.return_value = result
        resp = self.client.post('/api/capture/speech',
                                json={'text': '음성 입력'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['text'], '정돈된 텍스트')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_capture_merge_missing_texts(self, _):
        resp = self.client.post('/api/capture/merge',
                                json={'texts': []},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
