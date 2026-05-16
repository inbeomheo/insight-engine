"""prompts/quality_eval — 품질 평가 프롬프트 구조 검증

LLM-as-judge 프롬프트가 필수 플레이스홀더와 형식 가이드를 포함하는지 확인.
프롬프트 텍스트가 무심코 깨지면 평가 시스템이 망가지므로 invariant 보호.
"""
import unittest

from prompts.quality_eval import QUALITY_EVAL_PROMPT


class TestQualityEvalPrompt(unittest.TestCase):

    def test_is_non_empty_string(self):
        self.assertIsInstance(QUALITY_EVAL_PROMPT, str)
        self.assertGreater(len(QUALITY_EVAL_PROMPT.strip()), 200)

    def test_contains_required_placeholders(self):
        """포맷팅 시 사용되는 플레이스홀더가 포함되어야 함"""
        # {source_summary}, {content} 는 .format() 으로 채워짐
        self.assertIn('{source_summary}', QUALITY_EVAL_PROMPT)
        self.assertIn('{content}', QUALITY_EVAL_PROMPT)

    def test_describes_four_evaluation_criteria(self):
        """평가 기준 4개가 모두 명시되어야 함"""
        for criterion in ('정확성', '일관성', '가독성', '유용성'):
            with self.subTest(criterion=criterion):
                self.assertIn(criterion, QUALITY_EVAL_PROMPT)
        # 영문 키도 포함 (JSON 출력 필드)
        for key in ('accuracy', 'coherence', 'readability', 'usefulness'):
            with self.subTest(key=key):
                self.assertIn(key, QUALITY_EVAL_PROMPT)

    def test_includes_grade_buckets(self):
        """A/B/C/D 4개 등급이 모두 언급"""
        for grade in ('A등급', 'B등급', 'C등급', 'D등급'):
            with self.subTest(grade=grade):
                self.assertIn(grade, QUALITY_EVAL_PROMPT)

    def test_output_json_schema_keys_present(self):
        """JSON 출력 스키마의 모든 필드가 프롬프트에 명시"""
        for key in ('accuracy', 'coherence', 'readability', 'usefulness',
                    'overall', 'grade', 'feedback'):
            with self.subTest(key=key):
                self.assertIn(f'"{key}"', QUALITY_EVAL_PROMPT)

    def test_instructs_json_only_output(self):
        """JSON 외 텍스트 출력 금지 지시가 있어야 함 — 파싱 안정성"""
        self.assertIn('JSON', QUALITY_EVAL_PROMPT)
        # 다른 텍스트 금지 문구
        self.assertTrue(
            '다른 텍스트' in QUALITY_EVAL_PROMPT
            or 'JSON 외' in QUALITY_EVAL_PROMPT,
            'JSON-only 지시가 없음'
        )

    def test_format_does_not_raise(self):
        """.format(source_summary=..., content=...) 호출 정상 동작"""
        try:
            filled = QUALITY_EVAL_PROMPT.format(
                source_summary='요약 텍스트',
                content='생성 콘텐츠',
            )
        except (KeyError, IndexError) as e:
            self.fail(f'format 호출 시 예외: {e}')
        self.assertIn('요약 텍스트', filled)
        self.assertIn('생성 콘텐츠', filled)


if __name__ == '__main__':
    unittest.main()
