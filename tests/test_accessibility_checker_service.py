"""accessibility_checker_service 단위 테스트"""
import unittest
from services.content.accessibility_checker_service import check_accessibility


class TestCheckAccessibility(unittest.TestCase):

    def test_empty(self):
        result = check_accessibility('')
        self.assertEqual(result['score'], 0.0)
        self.assertGreater(len(result['issues']), 0)

    def test_good_content(self):
        content = '# 제목\n\n## 섹션 1\n\n짧은 문단입니다.\n\n![설명적 이미지](img.png)\n\n[유용한 링크](https://example.com)'
        result = check_accessibility(content)
        self.assertGreater(result['score'], 0.5)

    def test_missing_alt(self):
        content = '# 제목\n\n![](img.png)\n\n본문입니다.'
        result = check_accessibility(content)
        rules = [i['rule'] for i in result['issues']]
        self.assertIn('img_alt_missing', rules)

    def test_heading_skip(self):
        content = '# H1\n### H3\n내용'
        result = check_accessibility(content)
        rules = [i['rule'] for i in result['issues']]
        self.assertIn('heading_skip', rules)

    def test_generic_link_text(self):
        content = '# 제목\n[여기](url)를 클릭하세요.'
        result = check_accessibility(content)
        rules = [i['rule'] for i in result['issues']]
        self.assertIn('link_text_generic', rules)

    def test_color_dependency(self):
        content = '# 제목\n빨간색으로 표시된 항목은 위험합니다.'
        result = check_accessibility(content)
        rules = [i['rule'] for i in result['issues']]
        self.assertIn('color_dependency', rules)

    def test_long_paragraph(self):
        content = '# 제목\n\n' + '매우 긴 문단입니다. ' * 60
        result = check_accessibility(content)
        rules = [i['rule'] for i in result['issues']]
        self.assertIn('paragraph_length', rules)

    def test_level_values(self):
        valid = {'A', 'AA', 'AAA'}
        content = '# 제목\n본문'
        result = check_accessibility(content)
        self.assertIn(result['level'], valid)

    def test_total_checks(self):
        content = '# 제목\n본문'
        result = check_accessibility(content)
        self.assertEqual(result['total_checks'], len(result['issues']) + len(result['passed']))

    def test_perfect_content(self):
        content = '# 제목\n\n## 섹션\n\n짧은 문단.\n\n![좋은 설명](img.png)\n\n[문서 보기](url)'
        result = check_accessibility(content)
        self.assertGreaterEqual(result['score'], 0.7)


if __name__ == '__main__':
    unittest.main()
