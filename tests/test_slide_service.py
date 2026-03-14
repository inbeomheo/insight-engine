"""slide_service 단위 테스트"""
import unittest

from services.media.slide_service import convert_to_slides, _split_into_slides, _render_slide, _inline_format


class TestSplitIntoSlides(unittest.TestCase):
    """_split_into_slides 테스트"""

    def test_h2_split(self):
        """## 헤딩 기준 분할"""
        md = '## 슬라이드 1\n내용\n## 슬라이드 2\n내용'
        slides = _split_into_slides(md)
        self.assertEqual(len(slides), 2)

    def test_no_heading(self):
        """헤딩 없으면 1개 슬라이드"""
        slides = _split_into_slides('일반 텍스트만')
        self.assertEqual(len(slides), 1)

    def test_h1_split(self):
        """# 헤딩 기준 분할"""
        md = '# 제목\n내용\n# 다음'
        slides = _split_into_slides(md)
        self.assertEqual(len(slides), 2)


class TestInlineFormat(unittest.TestCase):
    """_inline_format 테스트"""

    def test_bold(self):
        result = _inline_format('**볼드**')
        self.assertIn('<strong>', result)

    def test_italic(self):
        result = _inline_format('*이탤릭*')
        self.assertIn('<em>', result)

    def test_inline_code(self):
        result = _inline_format('`코드`')
        self.assertIn('<code>', result)


class TestRenderSlide(unittest.TestCase):
    """_render_slide 테스트"""

    def test_heading(self):
        result = _render_slide('## 제목')
        self.assertIn('<h2>', result)

    def test_bullet_list(self):
        result = _render_slide('- 항목1\n- 항목2')
        self.assertIn('<ul>', result)
        self.assertIn('<li>', result)

    def test_code_block(self):
        result = _render_slide('```python\nprint("hi")\n```')
        self.assertIn('<pre>', result)

    def test_blockquote(self):
        result = _render_slide('> 인용문')
        self.assertIn('<blockquote>', result)


class TestConvertToSlides(unittest.TestCase):
    """convert_to_slides 테스트"""

    def test_returns_html(self):
        result = convert_to_slides('## 슬라이드 1\n내용')
        self.assertIn('<!DOCTYPE html>', result)
        self.assertIn('reveal.js', result)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            convert_to_slides('')

    def test_theme_applied(self):
        result = convert_to_slides('## 제목', theme='white')
        self.assertIn('white.css', result)

    def test_multiple_sections(self):
        md = '## A\n내용A\n## B\n내용B'
        result = convert_to_slides(md)
        self.assertEqual(result.count('<section>'), 2)


if __name__ == '__main__':
    unittest.main()
