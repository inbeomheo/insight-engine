"""quality_service 단위 테스트 (내부 함수 위주)"""
import unittest

from services.quality.quality_service import (
    _parse_quality_json, _validate_quality_result,
    should_regenerate, calculate_comprehensive_score,
)


class TestParseQualityJson(unittest.TestCase):

    def test_plain_json(self):
        """일반 JSON 파싱"""
        raw = '{"accuracy": 8, "coherence": 7, "readability": 9, "usefulness": 8, "overall": 8, "grade": "A", "feedback": "좋음"}'
        result = _parse_quality_json(raw)
        self.assertEqual(result['accuracy'], 8)

    def test_code_block(self):
        """코드블록 내 JSON 파싱"""
        raw = '```json\n{"accuracy": 5, "coherence": 5, "readability": 5, "usefulness": 5, "overall": 5, "grade": "C", "feedback": "보통"}\n```'
        result = _parse_quality_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['grade'], 'C')

    def test_invalid_json(self):
        """잘못된 JSON → None"""
        self.assertIsNone(_parse_quality_json('not json'))

    def test_empty_string(self):
        """빈 문자열 → None"""
        self.assertIsNone(_parse_quality_json(''))


class TestValidateQualityResult(unittest.TestCase):

    def test_valid_result(self):
        """유효한 결과 정규화"""
        data = {
            'accuracy': 8, 'coherence': 7, 'readability': 9,
            'usefulness': 8, 'overall': 0, 'grade': 'X', 'feedback': '피드백'
        }
        result = _validate_quality_result(data)
        self.assertEqual(result['overall'], 8.0)
        self.assertEqual(result['grade'], 'A')

    def test_missing_keys_raises(self):
        """필수 키 누락 → ValueError"""
        with self.assertRaises(ValueError):
            _validate_quality_result({'accuracy': 8})

    def test_out_of_range_raises(self):
        """점수 범위 초과 → ValueError"""
        data = {
            'accuracy': 15, 'coherence': 7, 'readability': 9,
            'usefulness': 8, 'overall': 0, 'grade': 'A', 'feedback': 'ok'
        }
        with self.assertRaises(ValueError):
            _validate_quality_result(data)

    def test_grade_recalculation_b(self):
        """등급 B 재계산"""
        data = {
            'accuracy': 6, 'coherence': 6, 'readability': 7,
            'usefulness': 6, 'overall': 0, 'grade': 'X', 'feedback': 'ok'
        }
        result = _validate_quality_result(data)
        self.assertEqual(result['grade'], 'B')

    def test_grade_recalculation_d(self):
        """등급 D 재계산"""
        data = {
            'accuracy': 2, 'coherence': 3, 'readability': 3,
            'usefulness': 2, 'overall': 0, 'grade': 'X', 'feedback': 'bad'
        }
        result = _validate_quality_result(data)
        self.assertEqual(result['grade'], 'D')

    def test_non_string_feedback(self):
        """feedback이 문자열 아니면 기본값"""
        data = {
            'accuracy': 5, 'coherence': 5, 'readability': 5,
            'usefulness': 5, 'overall': 5, 'grade': 'C', 'feedback': None
        }
        result = _validate_quality_result(data)
        self.assertIsInstance(result['feedback'], str)


class TestShouldRegenerate(unittest.TestCase):

    def test_below_threshold(self):
        """등급이 임계값 미만 → True"""
        self.assertTrue(should_regenerate({'grade': 'D'}, 'C'))

    def test_meets_threshold(self):
        """등급이 임계값 이상 → False"""
        self.assertFalse(should_regenerate({'grade': 'B'}, 'C'))

    def test_exact_threshold(self):
        """등급이 정확히 임계값 → False"""
        self.assertFalse(should_regenerate({'grade': 'C'}, 'C'))


class TestCalculateComprehensiveScore(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠"""
        result = calculate_comprehensive_score('')
        self.assertEqual(result['total_score'], 0)

    def test_basic_content(self):
        """기본 콘텐츠 점수 범위"""
        content = '## 제목\n\n파이썬은 좋은 언어입니다.\n\n- 항목1\n- 항목2'
        result = calculate_comprehensive_score(content)
        self.assertGreater(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)

    def test_structured_content_higher(self):
        """구조화된 콘텐츠가 더 높은 점수"""
        simple = '간단한 텍스트입니다.'
        structured = (
            '# 제목\n\n## 서론\n\n좋은 글입니다.\n\n## 본론\n\n'
            '- 항목1\n- 항목2\n- 항목3\n\n## 결론\n\n마무리입니다.\n'
        ) * 5
        score_simple = calculate_comprehensive_score(simple)['total_score']
        score_structured = calculate_comprehensive_score(structured)['total_score']
        self.assertGreater(score_structured, score_simple)

    def test_cliche_penalty(self):
        """금지 표현 감점"""
        clean = '파이썬은 유용한 언어입니다. ' * 20
        cliche = '파이썬은 놀라운 혁신적 획기적 언어입니다. ' * 20
        score_clean = calculate_comprehensive_score(clean)['originality']
        score_cliche = calculate_comprehensive_score(cliche)['originality']
        self.assertGreater(score_clean, score_cliche)

    def test_details_included(self):
        """details 필드 포함"""
        result = calculate_comprehensive_score('내용입니다.')
        self.assertIn('char_count', result['details'])
        self.assertIn('word_count', result['details'])


if __name__ == '__main__':
    unittest.main()
