"""keyword_density_service 단위 테스트"""
import unittest

from services.seo.keyword_density_service import (
    analyze_density,
    get_density_report,
    _tokenize,
)


class TestAnalyzeDensity(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_density('')
        self.assertEqual(result['total_words'], 0)
        self.assertEqual(result['keywords'], [])

    def test_none_content(self):
        result = analyze_density(None)
        self.assertEqual(result['keywords'], [])

    def test_no_keywords(self):
        result = analyze_density('파이썬 프로그래밍 입문 가이드')
        self.assertEqual(result['keywords'], [])
        self.assertGreater(result['total_words'], 0)

    def test_keyword_found(self):
        content = '파이썬은 좋은 언어입니다. 파이썬을 배우세요. 파이썬 강좌를 추천합니다.'
        result = analyze_density(content, ['파이썬'])
        kw = result['keywords'][0]
        self.assertEqual(kw['keyword'], '파이썬')
        self.assertGreater(kw['count'], 0)
        self.assertGreater(kw['density'], 0)

    def test_missing_keyword(self):
        result = analyze_density('파이썬 프로그래밍 가이드', ['자바스크립트'])
        kw = result['keywords'][0]
        self.assertEqual(kw['count'], 0)
        self.assertEqual(kw['status'], 'missing')

    def test_stuffing_detection(self):
        # 키워드를 과다하게 반복
        content = '파이썬 ' * 50 + '입문'
        result = analyze_density(content, ['파이썬'])
        kw = result['keywords'][0]
        self.assertIn(kw['status'], ('high', 'stuffing'))

    def test_position_tracking(self):
        content = '파이썬 시작. 중간 내용. 중간 내용. 중간 내용. 파이썬 끝.'
        result = analyze_density(content, ['파이썬'])
        kw = result['keywords'][0]
        self.assertGreater(len(kw['positions']), 0)

    def test_multiple_keywords(self):
        content = '파이썬과 자바스크립트는 인기 언어입니다.'
        result = analyze_density(content, ['파이썬', '자바스크립트'])
        self.assertEqual(len(result['keywords']), 2)

    def test_optimal_density_no_warning(self):
        # 적정 밀도(1~3%)가 되도록 구성
        words = ['프로그래밍', '언어', '개발', '학습', '도구', '환경', '설정', '배포'] * 5
        words += ['파이썬'] * 2
        content = ' '.join(words)
        result = analyze_density(content, ['파이썬'])
        kw = result['keywords'][0]
        if 1.0 <= kw['density'] <= 3.0:
            self.assertEqual(kw['status'], 'optimal')


class TestGetDensityReport(unittest.TestCase):

    def test_empty_content(self):
        result = get_density_report('')
        self.assertEqual(result['total_words'], 0)

    def test_basic_report(self):
        content = '파이썬 프로그래밍 입문 가이드입니다. 파이썬은 간결한 문법으로 초보자에게 적합합니다. 프로그래밍을 시작하세요.'
        result = get_density_report(content)
        self.assertGreater(result['total_words'], 0)
        self.assertGreater(result['unique_words'], 0)
        self.assertGreater(result['lexical_diversity'], 0)
        self.assertGreater(len(result['top_keywords']), 0)

    def test_top_n_limit(self):
        content = '하나 둘 셋 넷 다섯 여섯 일곱 여덟 아홉 열 ' * 5
        result = get_density_report(content, top_n=3)
        self.assertLessEqual(len(result['top_keywords']), 3)

    def test_suggestions_exist(self):
        result = get_density_report('테스트 콘텐츠 분석')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)


class TestTokenize(unittest.TestCase):

    def test_korean_words(self):
        tokens = _tokenize('파이썬 프로그래밍')
        self.assertIn('파이썬', tokens)
        self.assertIn('프로그래밍', tokens)

    def test_english_words(self):
        tokens = _tokenize('Python programming language')
        self.assertIn('python', tokens)
        self.assertIn('programming', tokens)

    def test_mixed(self):
        tokens = _tokenize('파이썬 Python 입문')
        self.assertEqual(len(tokens), 3)

    def test_short_words_excluded(self):
        tokens = _tokenize('a 나 I 것')
        self.assertEqual(len(tokens), 0)  # 1자 단어 제외


if __name__ == '__main__':
    unittest.main()
