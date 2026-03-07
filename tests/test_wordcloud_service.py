"""wordcloud_service 단위 테스트"""
import unittest

from services.wordcloud_service import generate_wordcloud, _count_words


class TestCountWords(unittest.TestCase):
    """_count_words 내부 함수 테스트"""

    def test_basic_counting(self):
        """기본 단어 빈도 계산"""
        text = '파이썬 파이썬 자바 자바 자바'
        result = _count_words(text, 10)
        words = dict(result)
        self.assertEqual(words['자바'], 3)
        self.assertEqual(words['파이썬'], 2)

    def test_stopwords_removed(self):
        """불용어 제거"""
        text = 'the quick brown fox jumps'
        result = _count_words(text, 10)
        words = [w for w, _ in result]
        self.assertNotIn('the', words)
        self.assertIn('quick', words)

    def test_short_words_excluded(self):
        """영어 2글자 이하 제외"""
        text = 'AI is a big deal in IT'
        result = _count_words(text, 10)
        words = [w for w, _ in result]
        self.assertNotIn('ai', words)
        self.assertNotIn('it', words)

    def test_html_stripped(self):
        """HTML 태그 제거"""
        text = '<p>프로그래밍</p> <strong>프로그래밍</strong>'
        result = _count_words(text, 10)
        words = dict(result)
        self.assertEqual(words.get('프로그래밍', 0), 2)


class TestGenerateWordcloud(unittest.TestCase):
    """generate_wordcloud 함수 테스트"""

    def test_returns_svg(self):
        """SVG 문자열 반환"""
        text = '파이썬 개발 파이썬 프로그래밍 파이썬 서버'
        result = generate_wordcloud(text)
        self.assertIn('<svg', result)
        self.assertIn('</svg>', result)

    def test_words_in_svg(self):
        """단어가 SVG에 포함됨"""
        text = '프로그래밍 ' * 10
        result = generate_wordcloud(text)
        self.assertIn('프로그래밍', result)

    def test_empty_text_raises(self):
        """빈 텍스트 시 ValueError"""
        with self.assertRaises(ValueError):
            generate_wordcloud('')

    def test_none_text_raises(self):
        """None 시 ValueError"""
        with self.assertRaises(ValueError):
            generate_wordcloud(None)

    def test_max_words_limit(self):
        """최대 단어 수 제한"""
        words = ' '.join(f'단어{i} ' * (100 - i) for i in range(80))
        result = generate_wordcloud(words, max_words=10)
        # SVG 내 text 요소 수 확인
        text_count = result.count('<text ')
        self.assertLessEqual(text_count, 10)

    def test_custom_dimensions(self):
        """커스텀 크기"""
        text = '파이썬 ' * 10
        result = generate_wordcloud(text, width=600, height=300)
        self.assertIn('width="600"', result)
        self.assertIn('height="300"', result)


if __name__ == '__main__':
    unittest.main()
