"""hashtag_generator_service 단위 테스트"""
import unittest

from services.content.hashtag_generator_service import (
    generate_hashtags,
    _extract_words,
    _is_stopword,
    _format_hashtag,
)


class TestGenerateHashtags(unittest.TestCase):

    def test_empty_content(self):
        result = generate_hashtags('')
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['hashtags'], [])

    def test_none_content(self):
        result = generate_hashtags(None)
        self.assertEqual(result['total'], 0)

    def test_basic_korean(self):
        content = '인공지능 기술이 빠르게 발전하고 있습니다. 인공지능은 미래를 바꿀 것입니다.'
        result = generate_hashtags(content)
        self.assertGreater(result['total'], 0)
        tags = [h['tag'] for h in result['hashtags']]
        self.assertTrue(any('#인공지능' in t for t in tags))

    def test_heading_boost(self):
        content = '# 머신러닝 가이드\n일반 텍스트 내용입니다.'
        result = generate_hashtags(content, include_headings=True)
        tags = [h['tag'] for h in result['hashtags']]
        # 헤딩 키워드가 상위에 등장
        self.assertTrue(any('머신러닝' in t for t in tags[:3]))

    def test_bold_boost(self):
        content = '이것은 **핵심포인트**에 대한 설명입니다. 일반 텍스트가 여기 있습니다.'
        result = generate_hashtags(content)
        tags = [h['tag'] for h in result['hashtags']]
        self.assertTrue(any('핵심포인트' in t for t in tags))

    def test_count_limit(self):
        content = '단어1 단어2 단어3 단어4 단어5 단어6 단어7 단어8 단어9 단어10 단어11'
        result = generate_hashtags(content, count=3)
        self.assertLessEqual(result['total'], 3)

    def test_max_count_cap(self):
        content = ' '.join([f'키워드{i}' for i in range(50)])
        result = generate_hashtags(content, count=50)
        self.assertLessEqual(result['total'], 30)

    def test_score_normalized(self):
        content = '인공지능 인공지능 인공지능 데이터 데이터 분석'
        result = generate_hashtags(content)
        if result['hashtags']:
            self.assertEqual(result['hashtags'][0]['score'], 1.0)

    def test_top_keywords_returned(self):
        content = '파이썬 프로그래밍은 데이터 분석에 유용합니다.'
        result = generate_hashtags(content)
        self.assertIsInstance(result['top_keywords'], list)

    def test_category_tags(self):
        content = '인공지능 머신러닝 딥러닝이 중요합니다. 인공지능 활용법.'
        result = generate_hashtags(content)
        self.assertIsInstance(result['category_tags'], list)

    def test_stopwords_filtered(self):
        content = '이것은 그리고 하지만 따라서 중요한 인공지능입니다.'
        result = generate_hashtags(content)
        tags = [h['tag'] for h in result['hashtags']]
        self.assertFalse(any('#그리고' == t for t in tags))
        self.assertFalse(any('#하지만' == t for t in tags))

    def test_english_content(self):
        content = 'Machine learning and artificial intelligence are transforming technology.'
        result = generate_hashtags(content)
        self.assertGreater(result['total'], 0)


class TestExtractWords(unittest.TestCase):

    def test_korean(self):
        words = _extract_words('한국어 테스트입니다')
        self.assertIn('한국어', words)

    def test_english(self):
        words = _extract_words('hello world test')
        self.assertIn('hello', words)

    def test_min_length(self):
        words = _extract_words('a ab abc 가 가나')
        # 영어 3자 이상, 한국어 2자 이상
        self.assertNotIn('a', words)
        self.assertNotIn('ab', words)
        self.assertIn('abc', words)
        self.assertIn('가나', words)


class TestIsStopword(unittest.TestCase):

    def test_korean_stopword(self):
        self.assertTrue(_is_stopword('그리고'))
        self.assertTrue(_is_stopword('하지만'))

    def test_english_stopword(self):
        self.assertTrue(_is_stopword('the'))
        self.assertTrue(_is_stopword('and'))

    def test_non_stopword(self):
        self.assertFalse(_is_stopword('인공지능'))
        self.assertFalse(_is_stopword('machine'))


class TestFormatHashtag(unittest.TestCase):

    def test_korean(self):
        self.assertEqual(_format_hashtag('인공지능'), '#인공지능')

    def test_english(self):
        self.assertEqual(_format_hashtag('AI'), '#AI')

    def test_empty(self):
        self.assertEqual(_format_hashtag(''), '')

    def test_special_chars_removed(self):
        result = _format_hashtag('test!@#')
        self.assertEqual(result, '#test')


if __name__ == '__main__':
    unittest.main()
