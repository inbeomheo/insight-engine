"""P7+: /generate-stream 토큰 delta SSE 회귀 테스트."""
import json
import unittest
from unittest.mock import patch

from app import create_app


_H = {'Origin': 'http://localhost:3000'}


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split('\n\n'):
        data_lines = [
            line.removeprefix('data: ')
            for line in block.splitlines()
            if line.startswith('data: ')
        ]
        if data_lines:
            events.append(json.loads('\n'.join(data_lines)))
    return events


class TestGenerateStreamDelta(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def _post(self, model='test/model'):
        return self.client.post(
            '/generate-stream',
            json={
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'model': model,
                'style': 'summary',
            },
            headers=_H,
        )

    def _patch_common(self):
        return (
            patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False),
            patch('routes.blog_routes.is_supabase_enabled', return_value=False),
            patch('routes.blog_routes.content_service.is_youtube_url', return_value=True),
            patch('routes.blog_routes.content_service.get_video_id', return_value='dQw4w9WgXcQ'),
            patch('routes.blog_routes.content_service.get_content_title', return_value='YT'),
            patch(
                'routes.blog_routes._fetch_youtube_content',
                return_value=('자막 본문', [], None, '자막 원문', 'api', []),
            ),
            patch('routes.blog_routes._get_style_prompt', return_value='스타일 프롬프트'),
            patch('routes.blog_routes.get_usage_for_response', return_value={'remaining': 4}),
        )

    def test_delta_events_accumulate_to_final_result_content(self):
        def fake_stream(*args, **kwargs):
            yield '본문 '
            yield '완성'
            return {
                'prompt': '사용된 프롬프트',
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5},
            }

        patches = self._patch_common() + (
            patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'delta', 'result'])

        deltas = ''.join(e['delta'] for e in events if e['type'] == 'delta')
        result = events[-1]
        self.assertEqual(deltas, '본문 완성')
        self.assertEqual(result['content'], deltas)
        self.assertEqual(result['title'], 'YT')
        self.assertIn('html', result)
        self.assertEqual(result['usage']['total_tokens'], 5)
        self.assertEqual(result['prompt'], '사용된 프롬프트')
        self.assertFalse(result['cached'])
        self.assertFalse(result['comment_summary_included'])
        self.assertEqual(result['youtube_title'], 'YT')
        self.assertEqual(result['transcript_source'], 'api')
        self.assertEqual(result['quota'], {'remaining': 4})

    def test_mid_stream_error_emits_korean_error_event(self):
        def broken_stream(*args, **kwargs):
            yield '부분'
            raise RuntimeError('boom')

        patches = self._patch_common() + (
            patch('routes.blog_routes.ai_service.create_content_stream', side_effect=broken_stream),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'error'])
        self.assertIn('생성 중 오류', events[-1]['error'])
        self.assertEqual(events[-1]['message'], events[-1]['error'])

    def test_glm_fallback_emits_single_delta_and_result_from_meta_result(self):
        fallback_result = {
            'title': 'GLM 제목',
            'content': 'GLM 본문',
            'html': '<p>GLM 본문</p>',
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
        }

        patches = self._patch_common() + (
            patch('services.core.ai_service.create_content', return_value=(fallback_result, 'GLM 프롬프트')),
        )
        with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6], patches[7], patches[8]:
            resp = self._post(model='zhipuai/GLM-4.7')
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'result'])
        self.assertEqual(events[1]['delta'], 'GLM 본문')
        self.assertEqual(events[-1]['title'], 'GLM 제목')
        self.assertEqual(events[-1]['content'], 'GLM 본문')
        self.assertEqual(events[-1]['usage']['total_tokens'], 18)


if __name__ == '__main__':
    unittest.main()
