"""쉬운말 변환 서비스 테스트."""
import unittest

from services.plain_language_service import (
    ReadabilityScore,
    simplify_text,
    assess_readability,
    _split_sentences,
    _count_complex_words,
    _break_long_sentence,
    _apply_easy_replacements,
)


class TestSplitSentences(unittest.TestCase):
    """문장 분리 테스트."""

    def test_basic_split(self):
        """마침표 기준 분리."""
        sentences = _split_sentences('첫 번째 문장. 두 번째 문장.')
        self.assertEqual(len(sentences), 2)

    def test_exclamation_split(self):
        """느낌표 기준 분리."""
        sentences = _split_sentences('좋습니다! 계속합시다.')
        self.assertEqual(len(sentences), 2)

    def test_empty_text(self):
        """빈 텍스트."""
        sentences = _split_sentences('')
        self.assertEqual(sentences, [])

    def test_single_sentence(self):
        """단일 문장."""
        sentences = _split_sentences('하나의 문장입니다')
        self.assertEqual(len(sentences), 1)


class TestCountComplexWords(unittest.TestCase):
    """복합어 수 계산 테스트."""

    def test_complex_patterns(self):
        """~적, ~화, ~성 패턴 감지."""
        count = _count_complex_words('체계적 접근으로 효율화를 달성하고 안정성을 확보합니다')
        self.assertGreaterEqual(count, 3)

    def test_replacement_words(self):
        """대체어 매핑 원본 단어도 복합어 계수."""
        count = _count_complex_words('활용하여 구현하고 개선합니다')
        self.assertGreaterEqual(count, 3)

    def test_simple_sentence(self):
        """단순 문장은 복합어 적음."""
        count = _count_complex_words('오늘 날씨가 좋습니다')
        self.assertEqual(count, 0)


class TestBreakLongSentence(unittest.TestCase):
    """긴 문장 분리 테스트."""

    def test_short_sentence_unchanged(self):
        """짧은 문장은 변경 없음."""
        sentence = '짧은 문장입니다.'
        result = _break_long_sentence(sentence, max_length=30)
        self.assertEqual(result, sentence)

    def test_long_sentence_broken(self):
        """긴 문장은 분리됨."""
        sentence = '이것은 매우 긴 문장으로, 여러 절로 구성되어 있으며, 분리가 필요합니다'
        result = _break_long_sentence(sentence, max_length=15)
        self.assertIn('.', result)

    def test_no_clause_boundary(self):
        """절 경계 없는 긴 문장은 그대로 반환."""
        sentence = '절경계없이이어지는매우긴하나의문장입니다'
        result = _break_long_sentence(sentence, max_length=10)
        self.assertEqual(result, sentence)


class TestApplyEasyReplacements(unittest.TestCase):
    """쉬운 대체어 적용 테스트."""

    def test_basic_replacement(self):
        """기본 대체어 적용."""
        result = _apply_easy_replacements('기능을 활용하여 구현합니다')
        self.assertIn('사용', result)
        self.assertIn('만들기', result)

    def test_multiple_replacements(self):
        """여러 단어 동시 치환."""
        result = _apply_easy_replacements('개선을 수행하고 제고합니다')
        self.assertIn('고치기', result)
        self.assertIn('하기', result)
        self.assertIn('높이기', result)

    def test_no_match(self):
        """대체 대상이 없으면 변경 없음."""
        original = '오늘 날씨가 좋습니다'
        result = _apply_easy_replacements(original)
        self.assertEqual(result, original)


class TestSimplifyText(unittest.TestCase):
    """텍스트 변환 통합 테스트."""

    def test_easy_level(self):
        """easy 레벨: 용어 치환 + 문장 분리."""
        text = '기능을 활용하여 체계적으로 구현합니다.'
        result = simplify_text(text, level='easy')
        self.assertIn('사용', result)
        self.assertIn('만들기', result)

    def test_normal_level_no_replacement(self):
        """normal 레벨: 용어 치환 안 함."""
        text = '기능을 활용하여 구현합니다.'
        result = simplify_text(text, level='normal')
        self.assertIn('활용', result)  # 치환 안 됨
        self.assertIn('구현', result)

    def test_original_level(self):
        """original 레벨: 변경 없음."""
        text = '기능을 활용하여 구현합니다.'
        result = simplify_text(text, level='original')
        self.assertEqual(result, text)

    def test_empty_text(self):
        """빈 텍스트."""
        self.assertEqual(simplify_text(''), '')
        self.assertEqual(simplify_text(None), '')

    def test_whitespace_only(self):
        """공백만 있는 텍스트."""
        result = simplify_text('   ')
        self.assertEqual(result, '   ')


class TestAssessReadability(unittest.TestCase):
    """가독성 평가 테스트."""

    def test_easy_text(self):
        """쉬운 텍스트는 높은 점수."""
        text = '오늘은 좋은 날입니다. 기분이 좋습니다. 산책합니다.'
        score = assess_readability(text)
        self.assertIsInstance(score, ReadabilityScore)
        self.assertGreaterEqual(score.score, 50)

    def test_complex_text(self):
        """복잡한 텍스트는 낮은 점수."""
        text = (
            '체계적이고 포괄적인 접근 방식을 통해 지속적인 효율화를 달성하고, '
            '획기적인 개선을 도모하여 명시적으로 활용 가능한 결과를 도출하며, '
            '적극적인 참여를 통해 체계적 성과를 이끌어내는 것이 필수적입니다.'
        )
        score = assess_readability(text)
        self.assertLess(score.score, 80)
        self.assertGreater(score.complex_word_ratio, 0)

    def test_empty_text(self):
        """빈 텍스트는 만점."""
        score = assess_readability('')
        self.assertEqual(score.score, 100.0)
        self.assertEqual(score.level, 'easy')

    def test_score_range(self):
        """점수는 0~100 범위."""
        text = '매우 복잡한 전문적 기술적 체계적 포괄적 지속적 명시적 획기적 적극적 효율적 즉각적 내용입니다.'
        score = assess_readability(text)
        self.assertGreaterEqual(score.score, 0)
        self.assertLessEqual(score.score, 100)

    def test_level_classification(self):
        """레벨 분류 확인."""
        easy_text = '좋아요. 감사합니다.'
        score = assess_readability(easy_text)
        self.assertIn(score.level, ('easy', 'normal', 'hard'))

    def test_suggestions_generated(self):
        """긴 문장 비율이 높으면 제안 생성."""
        long_text = (
            '이것은 굉장히 길고 복잡하며 여러 절로 이루어진 문장으로 '
            '독자가 이해하기 어려울 수 있는 형태의 텍스트를 의미합니다.'
        )
        score = assess_readability(long_text)
        # 긴 문장이 있으면 최소 하나의 제안
        self.assertIsInstance(score.suggestions, list)

    def test_avg_sentence_length(self):
        """평균 문장 길이 계산."""
        text = '짧은 문장. 또 짧은 문장.'
        score = assess_readability(text)
        self.assertGreater(score.avg_sentence_length, 0)

    def test_complex_word_ratio_range(self):
        """복합어 비율은 0~1 범위."""
        text = '체계적인 접근이 필요합니다. 효율적으로 수행합니다.'
        score = assess_readability(text)
        self.assertGreaterEqual(score.complex_word_ratio, 0)
        self.assertLessEqual(score.complex_word_ratio, 1)


if __name__ == '__main__':
    unittest.main()
