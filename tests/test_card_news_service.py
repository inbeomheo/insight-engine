"""card_news_service 단위 테스트"""
import unittest

from services.card_news_service import (
    generate_card_news, _split_content_to_points, _wrap_text_svg
)


class TestSplitContentToPoints(unittest.TestCase):

    def test_heading_extraction(self):
        md = '## 포인트 하나\n## 포인트 둘\n## 포인트 셋'
        points = _split_content_to_points(md)
        self.assertGreaterEqual(len(points), 3)

    def test_list_items(self):
        md = '- 첫 번째 아이템입니다\n- 두 번째 아이템입니다\n- 세 번째 아이템입니다\n- 네 번째 아이템입니다'
        points = _split_content_to_points(md)
        self.assertGreaterEqual(len(points), 4)

    def test_max_points(self):
        md = '\n'.join(f'## 포인트 번호 {i}' for i in range(20))
        points = _split_content_to_points(md, max_points=5)
        self.assertLessEqual(len(points), 5)

    def test_empty_content(self):
        self.assertEqual(_split_content_to_points(''), [])


class TestWrapTextSvg(unittest.TestCase):

    def test_short_text(self):
        result = _wrap_text_svg('짧은 텍스트')
        self.assertIn('tspan', result)
        self.assertEqual(result.count('tspan'), 2)  # open + close

    def test_long_text_wraps(self):
        result = _wrap_text_svg('이것은 매우 매우 긴 텍스트로 여러 줄로 나뉘어야 합니다')
        self.assertGreater(result.count('tspan'), 2)

    def test_xss_escaped(self):
        result = _wrap_text_svg('<script>alert(1)</script>')
        self.assertNotIn('<script>', result)


class TestGenerateCardNews(unittest.TestCase):

    def test_empty_content(self):
        self.assertEqual(generate_card_news(''), [])

    def test_returns_svg_list(self):
        md = '## 주제 하나\n내용\n## 주제 둘\n내용\n## 주제 셋\n내용'
        cards = generate_card_news(md, title='테스트')
        self.assertGreater(len(cards), 0)
        self.assertIn('<svg', cards[0])

    def test_title_card_first(self):
        md = '## 핵심 포인트 하나\n## 핵심 포인트 둘\n## 핵심 포인트 셋'
        cards = generate_card_news(md, title='제목 카드')
        self.assertIn('제목 카드', cards[0])

    def test_card_count(self):
        """제목 카드 + 포인트 카드"""
        md = '## 포인트 하나\n## 포인트 둘\n## 포인트 셋'
        cards = generate_card_news(md)
        points = _split_content_to_points(md)
        self.assertEqual(len(cards), len(points) + 1)


if __name__ == '__main__':
    unittest.main()
