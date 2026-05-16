"""prompts/event_extraction 프롬프트 구조 검증

YouTube 자막 → 구조화된 이벤트(액션/핵심/결정/질문) JSON 배열 추출 프롬프트.
프롬프트 변경으로 JSON 스키마가 깨지면 다운스트림 파싱이 망가지므로 invariant 보호.
"""
import unittest

from prompts.event_extraction import EVENT_EXTRACTION_PROMPT


class TestEventExtractionPrompt(unittest.TestCase):

    def test_is_non_empty(self):
        self.assertIsInstance(EVENT_EXTRACTION_PROMPT, str)
        self.assertGreater(len(EVENT_EXTRACTION_PROMPT.strip()), 500)

    def test_four_event_types_described(self):
        for event_type in ('action_item', 'key_point', 'decision', 'question'):
            with self.subTest(type=event_type):
                self.assertIn(event_type, EVENT_EXTRACTION_PROMPT)

    def test_common_fields_specified(self):
        for field in ('type', 'content', 'timestamp', 'context'):
            with self.subTest(field=field):
                self.assertIn(f'`{field}`', EVENT_EXTRACTION_PROMPT)

    def test_event_specific_fields_defined(self):
        """각 이벤트 타입의 전용 필드"""
        # action_item: priority
        self.assertIn('priority', EVENT_EXTRACTION_PROMPT)
        for p in ('high', 'medium', 'low'):
            self.assertIn(f'"{p}"', EVENT_EXTRACTION_PROMPT)
        # key_point: importance
        self.assertIn('importance', EVENT_EXTRACTION_PROMPT)
        # decision: stakeholders
        self.assertIn('stakeholders', EVENT_EXTRACTION_PROMPT)
        # question: status
        self.assertIn('status', EVENT_EXTRACTION_PROMPT)
        for s in ('open', 'resolved'):
            self.assertIn(f'"{s}"', EVENT_EXTRACTION_PROMPT)

    def test_timestamp_format_specified(self):
        self.assertIn('HH:MM:SS', EVENT_EXTRACTION_PROMPT)

    def test_event_count_bounds_specified(self):
        """최소/최대 이벤트 개수 가이드 명시 — LLM 과다/과소 생성 방지"""
        self.assertTrue(
            '최소 3개' in EVENT_EXTRACTION_PROMPT and '최대 20개' in EVENT_EXTRACTION_PROMPT,
            '이벤트 개수 경계 가이드 누락'
        )

    def test_no_creation_rule(self):
        """추측/창작 금지 규칙 존재 — 환각 방지"""
        self.assertTrue(
            ('추측' in EVENT_EXTRACTION_PROMPT) and ('창작' in EVENT_EXTRACTION_PROMPT),
            '환각 방지 규칙 누락'
        )

    def test_json_only_output_instruction(self):
        """다른 텍스트/마크다운 금지 → 파싱 안정성"""
        self.assertIn('JSON', EVENT_EXTRACTION_PROMPT)
        self.assertTrue(
            '다른 텍스트' in EVENT_EXTRACTION_PROMPT
            or '마크다운' in EVENT_EXTRACTION_PROMPT,
            'JSON-only 지시 누락'
        )

    def test_ends_with_transcript_placeholder(self):
        """프롬프트 끝에 '자막:' 으로 자막 본문이 이어지는 구조"""
        self.assertTrue(EVENT_EXTRACTION_PROMPT.rstrip().endswith('자막:'))


if __name__ == '__main__':
    unittest.main()
