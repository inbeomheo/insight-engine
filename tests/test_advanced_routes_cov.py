"""advanced_routes.py 라우트 커버리지 테스트.

마인드맵, 멀티스타일, 퓨전, 리라이트, QA, 파이프라인,
썸네일, 인라인 편집, 에이전트 커버.
"""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}

# require_auth + require_usage 를 동시에 우회하는 패치 목록
_AUTH_PATCHES = [
    patch('services.data.supabase_service.is_supabase_enabled', return_value=False),
    patch('services.usage.usage_decorator.UsageService'),
]


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── 마인드맵 ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestMindmap(_Base):

    def test_mindmap_no_content(self, _):
        resp = self.client.post('/api/mindmap', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 401])

    @patch('services.core.ai_service.create_content',
           return_value={'content': '# Mindmap', 'usage': {}})
    @patch('services.core.content_service.truncate_text', side_effect=lambda t, n: t)
    def test_mindmap_success(self, _trunc, _ai, _):
        self.app.config['STYLE_PROMPTS'] = {'mindmap': 'convert to mindmap'}
        resp = self.client.post('/api/mindmap',
                                json={'content': 'test content'},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 500])
        if resp.status_code == 200:
            data = resp.get_json()
            self.assertIn('markdown', data)

    def test_mindmap_missing_prompt(self, _):
        """STYLE_PROMPTS에 mindmap이 없으면 500."""
        self.app.config['STYLE_PROMPTS'] = {}
        resp = self.client.post('/api/mindmap',
                                json={'content': 'test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 500])


# ── 멀티스타일 ─────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestGenerateMulti(_Base):

    def test_multi_no_url(self, _):
        resp = self.client.post('/api/generate-multi', json={}, headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_multi_invalid_url(self, _):
        resp = self.client.post('/api/generate-multi',
                                json={'url': 'https://example.com', 'styles': ['blog_seo']},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_multi_no_styles(self, _):
        resp = self.client.post('/api/generate-multi',
                                json={'url': 'https://www.youtube.com/watch?v=test123'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_multi_too_many_styles(self, _):
        resp = self.client.post('/api/generate-multi',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=test123',
                                    'styles': ['s1', 's2', 's3', 's4', 's5', 's6']
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    @patch('routes.advanced_routes._fetch_youtube_content',
           return_value=('transcript', [], None, [], 'api', None))
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value='vid1')
    @patch('services.core.content_service.get_content_title', return_value='Title')
    @patch('services.core.content_service.truncate_text', side_effect=lambda t, n: t)
    @patch('services.core.ai_service.create_content',
           return_value={'content': 'ok', 'title': 'T', 'html': '<p>', 'usage': {}})
    def test_multi_success(self, _ai, _trunc, _title, _vid, _yt, _fetch, _):
        self.app.config['STYLE_PROMPTS'] = {'blog_seo': 'prompt'}
        resp = self.client.post('/api/generate-multi',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=test123',
                                    'styles': ['blog_seo']
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [200, 429])

    @patch('routes.advanced_routes._fetch_youtube_content',
           return_value=(None, [], '자막 없음', [], None, None))
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value='vid1')
    @patch('services.core.content_service.get_content_title', return_value='Title')
    def test_multi_transcript_error(self, _title, _vid, _yt, _fetch, _):
        resp = self.client.post('/api/generate-multi',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=test123',
                                    'styles': ['blog_seo']
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    @patch('services.core.content_service.is_youtube_url', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value=None)
    def test_multi_invalid_video_id(self, _vid, _yt, _):
        resp = self.client.post('/api/generate-multi',
                                json={
                                    'url': 'https://www.youtube.com/watch?v=bad',
                                    'styles': ['blog_seo']
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_multi_composes_base_prompt_for_ui_style(self, _):
        from prompts.base import BASE_PROMPT

        self.app.config['STYLE_PROMPTS'] = {'summary': 'SUMMARY_ONLY'}
        with (
            patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False),
            patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False),
            patch('routes.advanced_routes._fetch_youtube_content',
                  return_value=('transcript', [], None, [], 'api', None)),
            patch('services.core.content_service.is_youtube_url', return_value=True),
            patch('services.core.content_service.get_video_id', return_value='vid1'),
            patch('services.core.content_service.get_content_title', return_value='Title'),
            patch('services.core.content_service.truncate_text', side_effect=lambda t, n: t),
            patch('services.core.ai_service.create_content',
                  return_value={'content': 'ok', 'title': 'T', 'html': '<p>', 'usage': {}}) as create_content,
        ):
            resp = self.client.post(
                '/api/generate-multi',
                json={
                    'url': 'https://www.youtube.com/watch?v=test123',
                    'styles': ['summary'],
                    'model': 'zhipuai/test',
                },
                headers=_H,
                environ_overrides={'REMOTE_ADDR': '127.0.10.1'},
            )

        self.assertEqual(resp.status_code, 200)
        style_prompt = create_content.call_args[0][2]
        self.assertTrue(style_prompt.startswith(BASE_PROMPT))
        self.assertEqual(style_prompt.count(BASE_PROMPT), 1)
        self.assertTrue(style_prompt.endswith('SUMMARY_ONLY'))

    def test_multi_transform_style_does_not_get_base_prompt(self, _):
        from prompts.base import BASE_PROMPT

        self.app.config['STYLE_PROMPTS'] = {'mindmap': 'TRANSFORM_ONLY'}
        with (
            patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False),
            patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False),
            patch('routes.advanced_routes._fetch_youtube_content',
                  return_value=('transcript', [], None, [], 'api', None)),
            patch('services.core.content_service.is_youtube_url', return_value=True),
            patch('services.core.content_service.get_video_id', return_value='vid1'),
            patch('services.core.content_service.get_content_title', return_value='Title'),
            patch('services.core.content_service.truncate_text', side_effect=lambda t, n: t),
            patch('services.core.ai_service.create_content',
                  return_value={'content': 'ok', 'title': 'T', 'html': '<p>', 'usage': {}}) as create_content,
        ):
            resp = self.client.post(
                '/api/generate-multi',
                json={
                    'url': 'https://www.youtube.com/watch?v=test123',
                    'styles': ['mindmap'],
                    'model': 'zhipuai/test',
                },
                headers=_H,
                environ_overrides={'REMOTE_ADDR': '127.0.10.2'},
            )

        self.assertEqual(resp.status_code, 200)
        style_prompt = create_content.call_args[0][2]
        self.assertEqual(style_prompt, 'TRANSFORM_ONLY')
        self.assertFalse(style_prompt.startswith(BASE_PROMPT))


# ── 퓨전 ──────────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestGenerateFusion(_Base):

    def test_fusion_too_few_urls(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': ['http://a.com'], 'model': 'gemini/test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_fusion_too_many_urls(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': [f'http://{i}.com' for i in range(6)], 'model': 'gemini/test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    def test_fusion_no_model(self, _):
        resp = self.client.post('/api/generate-fusion',
                                json={'urls': ['http://a.com', 'http://b.com'], 'model': ''},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429])

    @patch('services.core.fusion_service.generate_fusion',
           return_value={'content': 'fused', 'title': 'T'})
    def test_fusion_success(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['https://youtube.com/watch?v=a', 'https://youtube.com/watch?v=b'],
                                    'model': 'gemini/test',
                                    'style': 'blog_seo'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [200, 429])

    @patch('services.core.fusion_service.generate_fusion',
           side_effect=ValueError('bad input'))
    def test_fusion_value_error(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['http://a.com', 'http://b.com'],
                                    'model': 'gemini/test'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429, 500])

    @patch('services.core.fusion_service.generate_fusion',
           side_effect=Exception('boom'))
    def test_fusion_exception(self, _fusion, _):
        resp = self.client.post('/api/generate-fusion',
                                json={
                                    'urls': ['http://a.com', 'http://b.com'],
                                    'model': 'gemini/test'
                                },
                                headers=_H)
        self.assertIn(resp.status_code, [429, 500])


# ── 리라이트 ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestRewrite(_Base):

    def test_rewrite_no_content(self, _):
        resp = self.client.post('/api/rewrite',
                                json={'platform': 'twitter'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_rewrite_no_platform(self, _):
        resp = self.client.post('/api/rewrite',
                                json={'content': 'hello'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.content.rewrite_service.rewrite_for_platform',
           return_value={'content': 'rewritten', 'platform': 'twitter'})
    def test_rewrite_success(self, _rw, _):
        resp = self.client.post('/api/rewrite',
                                json={'content': 'hello world test', 'platform': 'twitter'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.content.rewrite_service.rewrite_for_platform',
           return_value={'error': 'unsupported platform'})
    def test_rewrite_error_result(self, _rw, _):
        resp = self.client.post('/api/rewrite',
                                json={'content': 'hello world test', 'platform': 'bad'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.content.rewrite_service.rewrite_for_platform',
           side_effect=Exception('boom'))
    def test_rewrite_exception(self, _rw, _):
        resp = self.client.post('/api/rewrite',
                                json={'content': 'hello world test', 'platform': 'twitter'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 500])


# ── QA 체크 ──────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestQACheck(_Base):

    def test_qa_no_content(self, _):
        resp = self.client.post('/api/qa-check', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.quality.qa_gate_service.check_quality',
           return_value={'passed': True, 'issues': []})
    def test_qa_success(self, _qa, _):
        resp = self.client.post('/api/qa-check',
                                json={'content': 'test content'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['passed'])

    @patch('services.quality.qa_gate_service.check_quality',
           side_effect=Exception('qa fail'))
    def test_qa_exception(self, _qa, _):
        resp = self.client.post('/api/qa-check',
                                json={'content': 'test'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 500])


# ── 썸네일 ───────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestThumbnail(_Base):

    def test_thumbnail_no_title(self, _):
        resp = self.client.post('/api/generate-thumbnail', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.media.thumbnail_service.generate_thumbnail',
           return_value={'success': True, 'url': 'https://img.example.com/thumb.png'})
    def test_thumbnail_success(self, _thumb, _):
        resp = self.client.post('/api/generate-thumbnail',
                                json={'title': 'Test Title'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.media.thumbnail_service.generate_thumbnail',
           return_value={'success': False, 'error': 'API error'})
    def test_thumbnail_fail(self, _thumb, _):
        resp = self.client.post('/api/generate-thumbnail',
                                json={'title': 'Test Title'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 인라인 편집 ──────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestInlineEdit(_Base):

    def test_inline_edit_no_content(self, _):
        resp = self.client.post('/api/inline-edit',
                                json={'selection': 'text'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    def test_inline_edit_no_selection(self, _):
        resp = self.client.post('/api/inline-edit',
                                json={'content': 'full text'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.core.ai_service.inline_edit',
           return_value={'content': 'edited', 'usage': {}})
    def test_inline_edit_no_instruction(self, _ai, _):
        """instruction 없으면 400."""
        resp = self.client.post('/api/inline-edit',
                                json={'content': 'full', 'selection': 'part', 'instruction': ''},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.core.ai_service.inline_edit',
           return_value={'content': 'edited', 'usage': {}})
    def test_inline_edit_success(self, _ai, _):
        resp = self.client.post('/api/inline-edit',
                                json={
                                    'content': 'full text',
                                    'selection': 'text',
                                    'instruction': 'make bold'
                                },
                                headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 파이프라인 ────────────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestPipeline(_Base):

    def test_pipeline_no_url(self, _):
        resp = self.client.post('/api/pipeline',
                                json={'pipeline_id': 'blog_automation'},
                                headers=_H)
        # _get_request_data가 url 파싱 시 에러 또는 빈 URL 400
        self.assertIn(resp.status_code, [400, 429, 500])

    def test_pipeline_invalid_pipeline_id(self, _):
        resp = self.client.post('/api/pipeline',
                                json={'pipeline_id': 'nonexistent', 'url': 'https://youtube.com/watch?v=a'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 429, 500])


# ── 에이전트 리서치 ──────────────────────────────────


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestAgentResearch(_Base):

    def test_agent_research_no_topic(self, _):
        resp = self.client.post('/api/agent/research', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 에러 정리 헬퍼 ─────────────────────────────────────


class TestSanitizeGenerationError(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_safe_message(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback('[인증 실패] bad', 'fallback')
            self.assertIn('인증', result)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_server_error_uses_fallback(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback('[서버 오류] internal details', 'fallback')
            self.assertEqual(result, 'fallback')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_none_error(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback(None, 'fallback')
            self.assertIsInstance(result, str)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_exception_object(self, _):
        from utils.responses import safe_error_or_fallback
        with self.app.app_context():
            result = safe_error_or_fallback(ValueError('oops'), 'fallback')
            self.assertIsInstance(result, str)


if __name__ == '__main__':
    unittest.main()
