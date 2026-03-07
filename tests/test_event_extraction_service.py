"""event_extraction_service 단위 테스트 (내부 함수 위주)"""
import unittest

from services.event_extraction_service import (
    _parse_events_json, _validate_events, categorize_events, get_event_summary,
    EVENT_TYPES
)


class TestParseEventsJson(unittest.TestCase):

    def test_plain_json_array(self):
        """일반 JSON 배열 파싱"""
        raw = '[{"type": "key_point", "content": "중요 사항"}]'
        result = _parse_events_json(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['type'], 'key_point')

    def test_markdown_code_block(self):
        """마크다운 코드블록 내 JSON 파싱"""
        raw = '```json\n[{"type": "action_item", "content": "할 일"}]\n```'
        result = _parse_events_json(raw)
        self.assertEqual(len(result), 1)

    def test_empty_string(self):
        """빈 문자열 → 빈 리스트"""
        self.assertEqual(_parse_events_json(''), [])

    def test_invalid_json(self):
        """잘못된 JSON → 빈 리스트"""
        self.assertEqual(_parse_events_json('not json at all'), [])

    def test_json_with_surrounding_text(self):
        """주변 텍스트가 있는 JSON 배열"""
        raw = '결과입니다:\n[{"type": "question", "content": "질문?"}]\n끝.'
        result = _parse_events_json(raw)
        self.assertEqual(len(result), 1)


class TestValidateEvents(unittest.TestCase):

    def test_valid_action_item(self):
        """유효한 액션 아이템"""
        events = [{'type': 'action_item', 'content': '코드 리뷰하기', 'priority': 'high'}]
        result = _validate_events(events)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['priority'], 'high')

    def test_invalid_type_skipped(self):
        """잘못된 타입 → 건너뜀"""
        events = [{'type': 'invalid_type', 'content': '내용'}]
        result = _validate_events(events)
        self.assertEqual(len(result), 0)

    def test_empty_content_skipped(self):
        """빈 content → 건너뜀"""
        events = [{'type': 'key_point', 'content': ''}]
        result = _validate_events(events)
        self.assertEqual(len(result), 0)

    def test_non_dict_skipped(self):
        """dict가 아닌 항목 → 건너뜀"""
        events = ['not a dict', 42]
        result = _validate_events(events)
        self.assertEqual(len(result), 0)

    def test_key_point_importance_clamped(self):
        """핵심 포인트 중요도 클램핑"""
        events = [{'type': 'key_point', 'content': '포인트', 'importance': 5.0}]
        result = _validate_events(events)
        self.assertEqual(result[0]['importance'], 1.0)

    def test_question_status_default(self):
        """질문 상태 기본값"""
        events = [{'type': 'question', 'content': '왜?'}]
        result = _validate_events(events)
        self.assertEqual(result[0]['status'], 'open')

    def test_decision_stakeholders(self):
        """결정 사항 이해관계자"""
        events = [{'type': 'decision', 'content': '결정', 'stakeholders': ['팀장', '개발자']}]
        result = _validate_events(events)
        self.assertEqual(len(result[0]['stakeholders']), 2)

    def test_content_truncated(self):
        """긴 content 200자 절단"""
        events = [{'type': 'key_point', 'content': '가' * 300}]
        result = _validate_events(events)
        self.assertEqual(len(result[0]['content']), 200)

    def test_invalid_priority_default(self):
        """잘못된 priority → medium"""
        events = [{'type': 'action_item', 'content': '할 일', 'priority': 'urgent'}]
        result = _validate_events(events)
        self.assertEqual(result[0]['priority'], 'medium')


class TestCategorizeEvents(unittest.TestCase):

    def test_categorize(self):
        """유형별 분류"""
        events = [
            {'type': 'action_item', 'content': 'A'},
            {'type': 'key_point', 'content': 'B'},
            {'type': 'action_item', 'content': 'C'},
        ]
        result = categorize_events(events)
        self.assertEqual(len(result['action_item']), 2)
        self.assertEqual(len(result['key_point']), 1)

    def test_empty_events(self):
        """빈 이벤트 목록"""
        result = categorize_events([])
        for key in EVENT_TYPES:
            self.assertEqual(len(result[key]), 0)


class TestGetEventSummary(unittest.TestCase):

    def test_summary(self):
        """요약 통계"""
        events = [
            {'type': 'action_item', 'content': 'A', 'priority': 'high'},
            {'type': 'key_point', 'content': 'B', 'importance': 0.9},
            {'type': 'question', 'content': 'C?', 'status': 'open'},
        ]
        summary = get_event_summary(events)
        self.assertEqual(summary['total'], 3)
        self.assertEqual(len(summary['highlights']['high_priority_actions']), 1)
        self.assertEqual(len(summary['highlights']['important_key_points']), 1)
        self.assertEqual(len(summary['highlights']['open_questions']), 1)

    def test_summary_empty(self):
        """빈 이벤트 요약"""
        summary = get_event_summary([])
        self.assertEqual(summary['total'], 0)


if __name__ == '__main__':
    unittest.main()
