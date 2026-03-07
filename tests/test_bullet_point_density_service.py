"""Bullet Point Density Analyzer 서비스 테스트."""
import unittest
from services.bullet_point_density_service import analyze_bullet_density


class TestBulletPointDensityAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_bullet_density('')
        self.assertEqual(result['summary']['total_list_items'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_none_content(self):
        result = analyze_bullet_density(None)
        self.assertEqual(result['summary']['total_list_items'], 0)

    def test_no_bullets(self):
        content = '서술형 텍스트만 있습니다.\n추가 설명입니다.\n더 많은 설명입니다.'
        result = analyze_bullet_density(content)
        self.assertEqual(result['summary']['total_list_items'], 0)
        self.assertEqual(result['score'], 40.0)

    def test_markdown_bullets(self):
        content = '설명입니다.\n- 항목 1\n- 항목 2\n- 항목 3\n추가 설명.'
        result = analyze_bullet_density(content)
        self.assertEqual(result['summary']['total_list_items'], 3)

    def test_markdown_asterisk_bullets(self):
        content = '설명입니다.\n* 항목 A\n* 항목 B\n추가 설명.'
        result = analyze_bullet_density(content)
        self.assertGreater(result['summary']['total_list_items'], 0)

    def test_numbered_list(self):
        content = '설명입니다.\n1. 첫째\n2. 둘째\n3. 셋째\n추가 설명.'
        result = analyze_bullet_density(content)
        self.assertEqual(result['summary']['total_list_items'], 3)

    def test_high_density(self):
        content = '- 항목 1\n- 항목 2\n- 항목 3\n- 항목 4\n- 항목 5'
        result = analyze_bullet_density(content)
        self.assertGreater(result['summary']['bullet_density'], 50)

    def test_low_density(self):
        lines = ['서술 텍스트입니다.'] * 20 + ['- 항목 하나']
        content = '\n'.join(lines)
        result = analyze_bullet_density(content)
        self.assertLess(result['summary']['bullet_density'], 10)

    def test_list_groups(self):
        content = '서론.\n- A\n- B\n- C\n중간 텍스트.\n- D\n- E'
        result = analyze_bullet_density(content)
        self.assertEqual(result['summary']['list_group_count'], 2)

    def test_long_list_group(self):
        items = '\n'.join(f'- 항목 {i}' for i in range(12))
        content = f'설명입니다.\n{items}\n추가 설명.'
        result = analyze_bullet_density(content)
        long_groups = [g for g in result['list_groups'] if g['is_long']]
        self.assertGreater(len(long_groups), 0)

    def test_section_analysis(self):
        content = """## 소개
서론 텍스트입니다.

## 본론
- 항목 1
- 항목 2
- 항목 3
"""
        result = analyze_bullet_density(content)
        self.assertGreater(len(result['section_analysis']), 0)

    def test_suggestions_no_bullets(self):
        content = '서술형 텍스트만 있습니다.\n추가 설명입니다.'
        result = analyze_bullet_density(content)
        self.assertTrue(any('없습니다' in s for s in result['suggestions']))

    def test_suggestions_high_density(self):
        content = '\n'.join(f'- 항목 {i}' for i in range(20))
        result = analyze_bullet_density(content)
        self.assertTrue(any('과다' in s or '적정' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = '- 항목\n텍스트'
        result = analyze_bullet_density(content)
        self.assertIn('section_analysis', result)
        self.assertIn('list_groups', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_list_items', result['summary'])
        self.assertIn('bullet_density', result['summary'])
        self.assertIn('list_group_count', result['summary'])


if __name__ == '__main__':
    unittest.main()
