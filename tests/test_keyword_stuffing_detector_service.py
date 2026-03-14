"""Keyword Stuffing Detector 서비스 테스트."""
import unittest
from services.seo.keyword_stuffing_detector_service import detect_keyword_stuffing


class TestKeywordStuffingDetector(unittest.TestCase):

    def test_empty_content(self):
        result = detect_keyword_stuffing('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['stuffing_detected'])

    def test_none_content(self):
        result = detect_keyword_stuffing(None)
        self.assertEqual(result['score'], 100.0)

    def test_normal_content(self):
        content = ('다양한 주제를 폭넓게 다루는 글입니다. 여러 관점에서 심층 분석을 합니다. '
                   '종합적인 결론을 도출합니다. 독자에게 유용한 정보를 제공합니다. '
                   '배경 지식과 사례를 포함하여 설명합니다. 실용적인 가이드를 작성합니다.')
        result = detect_keyword_stuffing(content)
        self.assertFalse(result['summary']['stuffing_detected'])

    def test_stuffed_content(self):
        # 같은 키워드 과도 반복 (50단어 이상 필요)
        filler = ' '.join([f'다른단어{i}' for i in range(40)])
        content = ' '.join(['마케팅'] * 20) + ' ' + filler
        result = detect_keyword_stuffing(content)
        self.assertTrue(result['summary']['stuffing_detected'])
        self.assertGreater(len(result['stuffed_keywords']), 0)

    def test_density_calculation(self):
        content = '품질 관리는 중요합니다. 품질 검사를 합니다. 품질 보증이 필요합니다.'
        result = detect_keyword_stuffing(content)
        if result['keyword_density']:
            top = result['keyword_density'][0]
            self.assertIn('keyword', top)
            self.assertIn('count', top)
            self.assertIn('density', top)

    def test_stopwords_excluded(self):
        content = '합니다 합니다 합니다 합니다 합니다 합니다 합니다 합니다'
        result = detect_keyword_stuffing(content)
        # 불용어는 밀도 계산에서 제외
        self.assertFalse(result['summary']['stuffing_detected'])

    def test_english_stuffing(self):
        filler = ' '.join([f'word{i}' for i in range(40)])
        content = ' '.join(['marketing'] * 20) + ' ' + filler
        result = detect_keyword_stuffing(content)
        self.assertTrue(result['summary']['stuffing_detected'])

    def test_top_20_limit(self):
        words = [f'키워드{i}' for i in range(30)]
        content = ' '.join(words * 2)
        result = detect_keyword_stuffing(content)
        self.assertLessEqual(len(result['keyword_density']), 20)

    def test_max_density(self):
        content = '테스트 테스트 테스트 다른 단어 여러 가지 내용'
        result = detect_keyword_stuffing(content)
        self.assertGreater(result['summary']['max_density'], 0.0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_keyword_stuffing(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_stuffed(self):
        content = ' '.join(['SEO'] * 25 + ['content'] * 5)
        result = detect_keyword_stuffing(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '구조 확인입니다.'
        result = detect_keyword_stuffing(content)
        self.assertIn('keyword_density', result)
        self.assertIn('stuffed_keywords', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_words', result['summary'])
        self.assertIn('stuffing_detected', result['summary'])


if __name__ == '__main__':
    unittest.main()
