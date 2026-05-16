"""takeaway_extractor_service 단위 테스트"""
import unittest

from services.content.takeaway_extractor_service import (
    extract_takeaways,
    _split_sentences,
    _score_sentence,
    _clean_sentence,
)


class TestExtractTakeaways(unittest.TestCase):

    def test_empty_content(self):
        result = extract_takeaways('')
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['takeaways'], [])

    def test_none_content(self):
        result = extract_takeaways(None)
        self.assertEqual(result['total'], 0)

    def test_basic_extraction(self):
        content = """# 인공지능의 미래

인공지능 기술은 빠르게 발전하고 있습니다.
핵심은 데이터와 알고리즘의 결합입니다.
따라서 기업들은 AI 투자를 확대하고 있습니다.
그런데 윤리적 문제도 고려해야 합니다.
결론적으로 AI는 우리 삶을 크게 변화시킬 것입니다."""
        result = extract_takeaways(content, count=3)
        self.assertEqual(result['total'], 3)
        for t in result['takeaways']:
            self.assertIn('text', t)
            self.assertIn('score', t)
            self.assertIn('position', t)

    def test_count_limit(self):
        content = '문장1. 문장2. 문장3. 문장4. 문장5. 문장6. 문장7.'
        result = extract_takeaways(content, count=3)
        self.assertLessEqual(result['total'], 3)

    def test_max_count_cap(self):
        content = '. '.join([f'중요한 문장 {i}입니다' for i in range(20)])
        result = extract_takeaways(content, count=15)
        self.assertLessEqual(result['total'], 10)

    def test_min_count(self):
        content = '핵심 내용입니다. 결론입니다.'
        result = extract_takeaways(content, count=0)
        self.assertGreaterEqual(result['total'], 0)

    def test_headings_extracted(self):
        content = """# 제목 1

본문 내용입니다.

## 제목 2

추가 내용입니다."""
        result = extract_takeaways(content)
        self.assertIn('제목 1', result['headings'])
        self.assertIn('제목 2', result['headings'])

    def test_source_sentences_count(self):
        content = '첫째 문장은 이렇게 긴 문장입니다. 둘째 문장도 충분히 긴 내용을 담고 있습니다. 셋째 문장은 마무리입니다.'
        result = extract_takeaways(content)
        self.assertGreater(result['source_sentences'], 0)

    def test_importance_keywords_boost(self):
        content = """일반적인 내용입니다.
핵심은 이 부분이 가장 중요합니다.
부연하면 이건 부수적인 내용입니다.
따라서 결론은 명확합니다."""
        result = extract_takeaways(content, count=2)
        texts = [t['text'] for t in result['takeaways']]
        # 핵심/따라서 키워드가 포함된 문장이 상위에 올 가능성 높음
        has_important = any('핵심' in t or '따라서' in t for t in texts)
        self.assertTrue(has_important)

    def test_position_labels(self):
        content = '. '.join([f'문장 {i}번째 내용입니다' for i in range(10)])
        result = extract_takeaways(content, count=10)
        positions = {t['position'] for t in result['takeaways']}
        # intro, body, conclusion 중 최소 하나 존재
        self.assertTrue(positions & {'intro', 'body', 'conclusion'})


class TestSplitSentences(unittest.TestCase):

    def test_basic_split(self):
        sentences = _split_sentences('첫 번째 문장입니다. 두 번째 문장입니다.')
        self.assertGreaterEqual(len(sentences), 2)

    def test_filters_short(self):
        sentences = _split_sentences('짧은. 이것도 짧음. 이 문장은 충분히 깁니다 열 글자 이상.')
        # 10자 이하 문장은 필터링됨
        for s in sentences:
            self.assertGreater(len(s), 10)

    def test_removes_headings(self):
        sentences = _split_sentences('# 제목\n본문 내용이 여기에 있습니다.')
        for s in sentences:
            self.assertNotIn('#', s)

    def test_empty_input(self):
        self.assertEqual(_split_sentences(''), [])


class TestScoreSentence(unittest.TestCase):

    def test_intro_position_boost(self):
        score_intro = _score_sentence('일반 문장입니다', 0.0, 10)
        score_mid = _score_sentence('일반 문장입니다', 0.5, 10)
        self.assertGreater(score_intro, score_mid)

    def test_conclusion_position_boost(self):
        score_end = _score_sentence('일반 문장입니다', 0.95, 10)
        score_mid = _score_sentence('일반 문장입니다', 0.5, 10)
        self.assertGreater(score_end, score_mid)

    def test_keyword_boost(self):
        score_with = _score_sentence('핵심은 이것이 중요합니다', 0.5, 10)
        score_without = _score_sentence('그냥 평범한 내용입니다', 0.5, 10)
        self.assertGreater(score_with, score_without)

    def test_bold_boost(self):
        score_bold = _score_sentence('**중요한** 내용입니다', 0.5, 10)
        score_plain = _score_sentence('일반 내용입니다 여기에', 0.5, 10)
        self.assertGreater(score_bold, score_plain)

    def test_stat_boost(self):
        score_stat = _score_sentence('매출이 75% 증가했습니다', 0.5, 10)
        score_none = _score_sentence('매출이 증가했습니다 많이', 0.5, 10)
        self.assertGreater(score_stat, score_none)

    def test_score_bounds(self):
        score = _score_sentence('테스트', 0.5, 10)
        self.assertGreaterEqual(score, 0.0)
        self.assertLessEqual(score, 1.0)


class TestCleanSentence(unittest.TestCase):

    def test_remove_bullet(self):
        self.assertEqual(_clean_sentence('- 항목 내용'), '항목 내용')

    def test_remove_numbered(self):
        self.assertEqual(_clean_sentence('1. 첫 번째'), '첫 번째')
        self.assertEqual(_clean_sentence('2) 두 번째'), '두 번째')

    def test_remove_bold(self):
        self.assertEqual(_clean_sentence('**강조** 텍스트'), '강조 텍스트')

    def test_plain_text_unchanged(self):
        self.assertEqual(_clean_sentence('일반 텍스트'), '일반 텍스트')


if __name__ == '__main__':
    unittest.main()
