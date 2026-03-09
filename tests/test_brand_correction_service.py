"""
브랜드 규칙 기반 자동 교정 서비스 테스트
"""
import unittest

from services.brand_correction_service import (
    Correction,
    CorrectionResult,
    auto_correct_brand,
    validate_rules,
)


def _make_rules(*overrides):
    """기본 테스트 규칙 생성."""
    default = [
        {'find': '혁신적', 'replace': '새로운', 'name': '금지어_혁신적'},
        {'find': '놀라운', 'replace': '주목할 만한', 'name': '금지어_놀라운'},
        {'find': 'Insigth Engine', 'replace': 'Insight Engine', 'name': '오탈자_브랜드명'},
    ]
    return default


class TestAutoCorrectBasic(unittest.TestCase):
    """기본 교정 동작 검증."""

    def test_single_correction(self):
        content = '이것은 혁신적인 제품입니다.'
        rules = [{'find': '혁신적', 'replace': '새로운', 'name': '금지어_혁신적'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.corrected, '이것은 새로운인 제품입니다.')
        self.assertEqual(result.correction_count, 1)
        self.assertEqual(result.original, content)
        self.assertEqual(result.corrections[0].original_text, '혁신적')
        self.assertEqual(result.corrections[0].corrected_text, '새로운')

    def test_multiple_corrections(self):
        content = '놀라운 혁신적 서비스입니다.'
        rules = _make_rules()
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.correction_count, 2)
        self.assertNotIn('혁신적', result.corrected)
        self.assertNotIn('놀라운', result.corrected)


class TestAutoCorrectNoMatch(unittest.TestCase):
    """매칭되지 않는 경우."""

    def test_no_match(self):
        content = '평범한 문장입니다.'
        rules = _make_rules()
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.corrected, content)
        self.assertEqual(result.correction_count, 0)
        self.assertEqual(result.corrections, [])


class TestAutoCorrectEmptyInput(unittest.TestCase):
    """빈 입력 처리."""

    def test_empty_content(self):
        result = auto_correct_brand('', _make_rules())
        self.assertEqual(result.correction_count, 0)
        self.assertEqual(result.corrected, '')

    def test_none_content(self):
        result = auto_correct_brand(None, _make_rules())
        self.assertEqual(result.correction_count, 0)

    def test_whitespace_content(self):
        result = auto_correct_brand('   ', _make_rules())
        self.assertEqual(result.correction_count, 0)

    def test_empty_rules(self):
        result = auto_correct_brand('혁신적 콘텐츠', [])
        self.assertEqual(result.corrected, '혁신적 콘텐츠')
        self.assertEqual(result.correction_count, 0)


class TestAutoCorrectMultipleOccurrences(unittest.TestCase):
    """같은 단어가 여러 번 등장하는 경우."""

    def test_multiple_occurrences(self):
        content = '혁신적 기술로 혁신적 미래를 만듭니다.'
        rules = [{'find': '혁신적', 'replace': '새로운', 'name': '금지어'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.correction_count, 2)
        self.assertEqual(result.corrected.count('새로운'), 2)
        self.assertNotIn('혁신적', result.corrected)


class TestAutoCorrectPosition(unittest.TestCase):
    """교정 위치(position) 정확도."""

    def test_position_tracking(self):
        content = '시작 혁신적 끝'
        rules = [{'find': '혁신적', 'replace': '새로운', 'name': '교정'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.corrections[0].position, 3)  # '시작 ' = 3글자

    def test_positions_ascending(self):
        """corrections 리스트가 위치 오름차순으로 정렬."""
        content = '놀라운 결과와 혁신적 성과'
        rules = _make_rules()
        result = auto_correct_brand(content, rules)

        positions = [c.position for c in result.corrections]
        self.assertEqual(positions, sorted(positions))


class TestAutoCorrectBrandName(unittest.TestCase):
    """브랜드명 오탈자 교정."""

    def test_brand_typo_fix(self):
        content = 'Insigth Engine을 사용해보세요.'
        rules = [{'find': 'Insigth Engine', 'replace': 'Insight Engine', 'name': '브랜드명'}]
        result = auto_correct_brand(content, rules)

        self.assertIn('Insight Engine', result.corrected)
        self.assertNotIn('Insigth Engine', result.corrected)


class TestAutoCorrectCaseSensitive(unittest.TestCase):
    """대소문자 구분 옵션."""

    def test_case_sensitive_default(self):
        """기본값은 대소문자 구분."""
        content = 'HELLO world Hello'
        rules = [{'find': 'Hello', 'replace': 'Hi', 'name': '인사'}]
        result = auto_correct_brand(content, rules)

        # 'Hello'만 매칭, 'HELLO'는 비매칭
        self.assertEqual(result.correction_count, 1)
        self.assertIn('Hi', result.corrected)
        self.assertIn('HELLO', result.corrected)

    def test_case_insensitive(self):
        content = 'HELLO world Hello'
        rules = [{'find': 'hello', 'replace': 'Hi', 'name': '인사', 'case_sensitive': False}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.correction_count, 2)


class TestAutoCorrectPreservesOriginal(unittest.TestCase):
    """original 필드가 원본을 보존."""

    def test_original_preserved(self):
        content = '놀라운 기술입니다.'
        rules = [{'find': '놀라운', 'replace': '좋은', 'name': '교정'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.original, content)
        self.assertNotEqual(result.corrected, content)


class TestAutoCorrectRuleName(unittest.TestCase):
    """교정 결과에 규칙명이 포함."""

    def test_rule_name_in_correction(self):
        content = '혁신적 제품'
        rules = [{'find': '혁신적', 'replace': '새로운', 'name': '금지어_혁신적'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.corrections[0].rule_name, '금지어_혁신적')


class TestAutoCorrectEmptyFindRule(unittest.TestCase):
    """find가 빈 문자열인 규칙은 무시."""

    def test_empty_find_skipped(self):
        content = '테스트 문장'
        rules = [{'find': '', 'replace': '교체', 'name': '빈규칙'}]
        result = auto_correct_brand(content, rules)

        self.assertEqual(result.correction_count, 0)
        self.assertEqual(result.corrected, content)


class TestValidateRules(unittest.TestCase):
    """규칙 유효성 검증."""

    def test_valid_rules(self):
        rules = [{'find': 'a', 'replace': 'b', 'name': 'rule1'}]
        errors = validate_rules(rules)
        self.assertEqual(errors, [])

    def test_missing_find(self):
        rules = [{'replace': 'b', 'name': 'rule1'}]
        errors = validate_rules(rules)
        self.assertTrue(any("'find'" in e for e in errors))

    def test_missing_replace(self):
        rules = [{'find': 'a', 'name': 'rule1'}]
        errors = validate_rules(rules)
        self.assertTrue(any("'replace'" in e for e in errors))

    def test_missing_name(self):
        rules = [{'find': 'a', 'replace': 'b'}]
        errors = validate_rules(rules)
        self.assertTrue(any("'name'" in e for e in errors))

    def test_not_dict(self):
        rules = ['not a dict']
        errors = validate_rules(rules)
        self.assertTrue(any('dict' in e for e in errors))


class TestAutoCorrectDataclass(unittest.TestCase):
    """dataclass 필드 검증."""

    def test_correction_result_fields(self):
        result = auto_correct_brand('혁신적', [{'find': '혁신적', 'replace': '새로운', 'name': 'r'}])

        self.assertIsInstance(result, CorrectionResult)
        self.assertIsInstance(result.original, str)
        self.assertIsInstance(result.corrected, str)
        self.assertIsInstance(result.corrections, list)
        self.assertIsInstance(result.correction_count, int)

    def test_correction_fields(self):
        result = auto_correct_brand('혁신적', [{'find': '혁신적', 'replace': '새로운', 'name': 'r'}])
        corr = result.corrections[0]

        self.assertIsInstance(corr, Correction)
        self.assertIsInstance(corr.original_text, str)
        self.assertIsInstance(corr.corrected_text, str)
        self.assertIsInstance(corr.rule_name, str)
        self.assertIsInstance(corr.position, int)


if __name__ == '__main__':
    unittest.main()
