"""summary_card_service 단위 테스트"""
import unittest

from services.summary_card_service import generate_summary_card, _wrap_lines


class TestWrapLines(unittest.TestCase):
    """_wrap_lines 유틸 함수 테스트"""

    def test_short_text_no_wrap(self):
        """짧은 텍스트는 줄바꿈 없음"""
        result = _wrap_lines('짧은 텍스트', 24)
        self.assertEqual(result, ['짧은 텍스트'])

    def test_long_text_wraps(self):
        """긴 텍스트는 max_chars 기준으로 줄바꿈"""
        result = _wrap_lines('가' * 50, 24)
        self.assertEqual(len(result[0]), 24)
        self.assertTrue(len(result) >= 2)

    def test_max_3_lines(self):
        """최대 3줄까지만 반환"""
        result = _wrap_lines('가' * 200, 24)
        self.assertEqual(len(result), 3)


class TestGenerateSummaryCard(unittest.TestCase):
    """generate_summary_card 함수 테스트"""

    def test_returns_svg_string(self):
        """SVG 문자열 반환"""
        result = generate_summary_card('테스트 제목', ['포인트 1', '포인트 2'])
        self.assertIn('<svg', result)
        self.assertIn('</svg>', result)

    def test_title_in_svg(self):
        """제목이 SVG에 포함됨"""
        result = generate_summary_card('나의 제목', ['포인트'])
        self.assertIn('나의 제목', result)

    def test_points_in_svg(self):
        """핵심 포인트가 SVG에 포함됨"""
        result = generate_summary_card('제목', ['첫번째 포인트', '두번째 포인트'])
        self.assertIn('첫번째 포인트', result)
        self.assertIn('두번째 포인트', result)

    def test_max_5_points(self):
        """최대 5개 포인트만 렌더링"""
        points = [f'포인트 {i}' for i in range(10)]
        result = generate_summary_card('제목', points)
        self.assertIn('포인트 4', result)
        self.assertNotIn('포인트 5', result)

    def test_html_escaping(self):
        """XSS 방지 — HTML 특수문자 이스케이프"""
        result = generate_summary_card('<script>alert(1)</script>', ['A & B'])
        self.assertNotIn('<script>', result)
        self.assertIn('&lt;script&gt;', result)
        self.assertIn('A &amp; B', result)

    def test_empty_title_defaults(self):
        """제목이 None이면 '요약'으로 기본값"""
        result = generate_summary_card(None, ['포인트'])
        self.assertIn('요약', result)

    def test_empty_points(self):
        """포인트가 None/빈 리스트여도 에러 없음"""
        result = generate_summary_card('제목', None)
        self.assertIn('<svg', result)
        result2 = generate_summary_card('제목', [])
        self.assertIn('<svg', result2)

    def test_long_point_truncated(self):
        """30자 넘는 포인트는 잘림"""
        long_point = '가' * 50
        result = generate_summary_card('제목', [long_point])
        # 원본 50자는 없고 28자+… 형태
        self.assertNotIn('가' * 50, result)


if __name__ == '__main__':
    unittest.main()
