"""
이벤트 추출 기능 통합 테스트

services/event_extraction_service.py 및 /api/extract-events 엔드포인트를 검증합니다.
"""
import json
import unittest
from unittest.mock import MagicMock, patch


# =============================================
# 서비스 단위 테스트
# =============================================

class TestEventExtractionService(unittest.TestCase):
    """이벤트 추출 서비스 단위 테스트"""

    def test_parse_events_json_valid(self):
        """정상적인 JSON 배열을 올바르게 파싱합니다."""
        from services.event_extraction_service import _parse_events_json

        raw = json.dumps([
            {"type": "action_item", "content": "파이썬 설치하기", "timestamp": "00:01:00",
             "priority": "high", "context": "개발 환경 설정"},
        ])
        result = _parse_events_json(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'action_item')

    def test_parse_events_json_with_markdown_codeblock(self):
        """마크다운 코드블록이 포함된 응답도 파싱합니다."""
        from services.event_extraction_service import _parse_events_json

        raw = '```json\n[{"type": "key_point", "content": "중요 내용", "timestamp": "", "context": "배경"}]\n```'
        result = _parse_events_json(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'key_point')

    def test_parse_events_json_invalid(self):
        """파싱 불가한 텍스트는 빈 리스트를 반환합니다."""
        from services.event_extraction_service import _parse_events_json

        self.assertEqual(_parse_events_json(''), [])
        self.assertEqual(_parse_events_json('유효하지 않은 텍스트'), [])
        self.assertEqual(_parse_events_json('{"type": "action_item"}'), [])  # 배열 아님

    def test_validate_events_removes_invalid(self):
        """유효하지 않은 이벤트를 제거합니다."""
        from services.event_extraction_service import _validate_events

        events = [
            # 유효: action_item
            {"type": "action_item", "content": "할 일", "timestamp": "00:01:00",
             "priority": "high", "context": "배경"},
            # 무효: content 없음
            {"type": "key_point", "content": "", "timestamp": "", "context": ""},
            # 무효: 알 수 없는 type
            {"type": "unknown_type", "content": "내용", "timestamp": "", "context": ""},
            # 무효: dict가 아님
            "문자열",
        ]
        result = _validate_events(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'action_item')

    def test_validate_events_normalizes_priority(self):
        """잘못된 priority 값은 'medium'으로 정규화합니다."""
        from services.event_extraction_service import _validate_events

        events = [
            {"type": "action_item", "content": "할 일", "timestamp": "",
             "priority": "INVALID_VALUE", "context": ""},
        ]
        result = _validate_events(events)
        self.assertEqual(result[0]['priority'], 'medium')

    def test_validate_events_clamps_importance(self):
        """importance 값을 0.0~1.0 범위로 제한합니다."""
        from services.event_extraction_service import _validate_events

        events = [
            {"type": "key_point", "content": "핵심", "timestamp": "",
             "importance": 1.5, "context": ""},
            {"type": "key_point", "content": "핵심2", "timestamp": "",
             "importance": -0.5, "context": ""},
        ]
        result = _validate_events(events)
        self.assertEqual(result[0]['importance'], 1.0)
        self.assertEqual(result[1]['importance'], 0.0)

    def test_categorize_events(self):
        """이벤트를 유형별로 올바르게 분류합니다."""
        from services.event_extraction_service import categorize_events

        events = [
            {"type": "action_item", "content": "A", "timestamp": "", "context": "", "priority": "high"},
            {"type": "action_item", "content": "B", "timestamp": "", "context": "", "priority": "low"},
            {"type": "key_point", "content": "C", "timestamp": "", "context": "", "importance": 0.8},
            {"type": "question", "content": "D", "timestamp": "", "context": "", "status": "open"},
        ]
        result = categorize_events(events)
        self.assertEqual(len(result['action_item']), 2)
        self.assertEqual(len(result['key_point']), 1)
        self.assertEqual(len(result['decision']), 0)
        self.assertEqual(len(result['question']), 1)

    def test_get_event_summary(self):
        """이벤트 요약 통계를 올바르게 반환합니다."""
        from services.event_extraction_service import get_event_summary

        events = [
            {"type": "action_item", "content": "A", "timestamp": "", "context": "", "priority": "high"},
            {"type": "action_item", "content": "B", "timestamp": "", "context": "", "priority": "medium"},
            {"type": "key_point", "content": "C", "timestamp": "", "context": "", "importance": 0.9},
            {"type": "question", "content": "D", "timestamp": "", "context": "", "status": "open"},
        ]
        summary = get_event_summary(events)
        self.assertEqual(summary['total'], 4)
        self.assertEqual(summary['by_type']['action_item'], 2)
        self.assertEqual(summary['by_type']['key_point'], 1)
        self.assertEqual(summary['by_type']['question'], 1)
        self.assertEqual(len(summary['highlights']['high_priority_actions']), 1)
        self.assertEqual(len(summary['highlights']['important_key_points']), 1)
        self.assertEqual(len(summary['highlights']['open_questions']), 1)

    def test_extract_events_empty_transcript_raises(self):
        """빈 자막은 ValueError를 발생시킵니다."""
        from services.event_extraction_service import extract_events
        with self.assertRaises(ValueError) as ctx:
            extract_events('')
        self.assertIn('자막', str(ctx.exception))

    @patch('services.ai_service._build_completion_kwargs')
    @patch('litellm.completion')
    def test_extract_events_with_mock_llm(self, mock_completion, mock_build_kwargs):
        """모킹된 LiteLLM으로 이벤트 추출 흐름을 검증합니다."""
        from services.event_extraction_service import extract_events

        # LiteLLM 응답 모킹
        fake_events = [
            {"type": "action_item", "content": "파이썬 설치하기", "timestamp": "00:01:00",
             "priority": "high", "context": "개발 환경 설정"},
            {"type": "key_point", "content": "변수는 데이터를 저장합니다", "timestamp": "00:05:00",
             "importance": 0.85, "context": "기본 개념"},
        ]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps(fake_events)
        mock_completion.return_value = mock_response
        mock_build_kwargs.return_value = {
            'model': 'test/model',
            'messages': [{'role': 'user', 'content': 'test'}],
        }

        result = extract_events('테스트 자막 내용입니다. ' * 20)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['type'], 'action_item')
        self.assertEqual(result[0]['priority'], 'high')
        self.assertEqual(result[1]['type'], 'key_point')
        self.assertAlmostEqual(result[1]['importance'], 0.85)


# =============================================
# API 엔드포인트 통합 테스트
# =============================================

class TestExtractEventsEndpoint(unittest.TestCase):
    """/api/extract-events 엔드포인트 통합 테스트"""

    def setUp(self):
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def _make_fake_events(self):
        """테스트용 가짜 이벤트 데이터를 반환합니다."""
        return [
            {"type": "action_item", "content": "테스트 액션", "timestamp": "00:01:00",
             "priority": "high", "context": "테스트 컨텍스트"},
            {"type": "key_point", "content": "테스트 핵심 포인트", "timestamp": "00:05:00",
             "importance": 0.9, "context": "중요한 내용"},
        ]

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.event_extraction_service.extract_events')
    def test_extract_events_with_transcript(self, mock_extract, mock_supabase):
        """transcript 직접 제공 시 정상 응답을 반환합니다."""
        mock_extract.return_value = self._make_fake_events()

        res = self.client.post('/api/extract-events', json={
            'transcript': '이것은 테스트 자막입니다. ' * 30,
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('events', data)
        self.assertIn('categorized', data)
        self.assertIn('summary', data)
        self.assertEqual(len(data['events']), 2)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_events_missing_input(self, mock_supabase):
        """url과 transcript 모두 없으면 400을 반환합니다."""
        res = self.client.post('/api/extract-events', json={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_events_invalid_youtube_url(self, mock_supabase):
        """유효하지 않은 YouTube URL은 400을 반환합니다."""
        res = self.client.post('/api/extract-events', json={
            'url': 'https://example.com/not-youtube',
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn('error', data)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes.content_service.is_youtube_url', return_value=True)
    @patch('routes.blog_routes.content_service.get_video_id', return_value='test_video_id')
    @patch('routes.blog_routes.content_service.get_transcript')
    @patch('services.event_extraction_service.extract_events')
    def test_extract_events_with_url(
        self, mock_extract, mock_get_transcript, mock_get_video_id,
        mock_is_youtube, mock_supabase
    ):
        """YouTube URL 제공 시 자막을 추출하고 이벤트를 반환합니다."""
        mock_get_transcript.return_value = {
            'transcript': '테스트 자막',
            'segments': [],
        }
        mock_extract.return_value = self._make_fake_events()

        res = self.client.post('/api/extract-events', json={
            'url': 'https://www.youtube.com/watch?v=test_video_id',
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('events', data)
        self.assertEqual(len(data['events']), 2)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.event_extraction_service.extract_events')
    def test_extract_events_service_error(self, mock_extract, mock_supabase):
        """서비스 내부 오류는 500으로 처리합니다."""
        mock_extract.side_effect = RuntimeError('AI 모델 오류 발생')

        res = self.client.post('/api/extract-events', json={
            'transcript': '테스트 자막 내용입니다.',
        })
        self.assertEqual(res.status_code, 500)
        data = res.get_json()
        self.assertIn('error', data)

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes.content_service.is_youtube_url', return_value=True)
    @patch('routes.blog_routes.content_service.get_video_id', return_value='vid123')
    @patch('routes.blog_routes.content_service.get_transcript', return_value=None)
    def test_extract_events_no_transcript(
        self, mock_get_transcript, mock_get_video_id, mock_is_youtube, mock_supabase
    ):
        """자막이 없는 영상은 422를 반환합니다."""
        res = self.client.post('/api/extract-events', json={
            'url': 'https://www.youtube.com/watch?v=vid123',
        })
        self.assertEqual(res.status_code, 422)
        data = res.get_json()
        self.assertIn('error', data)


if __name__ == '__main__':
    unittest.main()
