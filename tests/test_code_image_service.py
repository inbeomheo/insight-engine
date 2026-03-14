"""code_image_service 단위 테스트"""
import unittest

from services.media.code_image_service import generate_code_image, _highlight_line


class TestHighlightLine(unittest.TestCase):
    """_highlight_line 테스트"""

    def test_keyword_highlighted(self):
        """파이썬 키워드 하이라이트"""
        result = _highlight_line('def hello():', 'python')
        self.assertIn('font-weight:700', result)
        self.assertIn('def', result)

    def test_comment_highlighted(self):
        """주석 하이라이트"""
        result = _highlight_line('x = 1  # 주석', 'python')
        self.assertIn('# 주석', result)

    def test_xss_escaped(self):
        """HTML 특수문자 이스케이프"""
        result = _highlight_line('<script>alert(1)</script>', 'python')
        self.assertNotIn('<script>', result)


class TestGenerateCodeImage(unittest.TestCase):
    """generate_code_image 테스트"""

    def test_empty_code(self):
        """빈 코드 시 안내 메시지"""
        result = generate_code_image('')
        self.assertIn('코드가 없습니다', result)

    def test_returns_html(self):
        """HTML 반환"""
        result = generate_code_image('print("hello")', 'python')
        self.assertIn('<!DOCTYPE html>', result)

    def test_line_numbers(self):
        """줄 번호 포함"""
        result = generate_code_image('line1\nline2\nline3')
        self.assertIn('>1<', result)
        self.assertIn('>3<', result)

    def test_title_in_header(self):
        """제목 헤더에 표시"""
        result = generate_code_image('x = 1', 'python', title='main.py')
        self.assertIn('main.py', result)

    def test_default_title(self):
        """제목 없으면 기본값"""
        result = generate_code_image('x = 1', 'javascript')
        self.assertIn('code.javascript', result)

    def test_javascript_keywords(self):
        """자바스크립트 키워드 하이라이트"""
        result = generate_code_image('const x = true;', 'javascript')
        self.assertIn('const', result)

    def test_title_xss_escaped(self):
        """제목 XSS 이스케이프"""
        result = generate_code_image('x=1', 'python', title='<img onerror=alert(1)>')
        self.assertNotIn('<img onerror', result)


if __name__ == '__main__':
    unittest.main()
