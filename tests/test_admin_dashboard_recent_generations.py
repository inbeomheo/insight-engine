"""R59: /api/admin/dashboard recent_generations 필드 테스트"""
from __future__ import annotations

import unittest


class TestRecentGenerationsLogic(unittest.TestCase):
    """recent_generations 추출 로직 단위 테스트"""

    @staticmethod
    def _extract_recent(items):
        """admin_dashboard에서 사용하는 동일한 로직"""
        sorted_items = sorted(items, key=lambda x: x.get('created_at', ''), reverse=True)
        recent = []
        for item in sorted_items[:5]:
            title = (item.get('content') or '')[:80].split('\n')[0].strip()
            if not title:
                title = '(제목 없음)'
            recent.append({
                'title': title,
                'style': item.get('style', 'unknown'),
                'created_at': item.get('created_at', ''),
            })
        return recent

    def test_empty_items(self):
        """빈 목록 → 빈 리스트"""
        result = self._extract_recent([])
        self.assertEqual(result, [])

    def test_fewer_than_five(self):
        """3개 항목 → 3개 반환"""
        items = [
            {'content': '제목1\n본문', 'style': 'blog_seo', 'created_at': '2026-03-15'},
            {'content': '제목2\n본문', 'style': 'summary', 'created_at': '2026-03-16'},
            {'content': '제목3\n본문', 'style': 'tutorial', 'created_at': '2026-03-17'},
        ]
        result = self._extract_recent(items)
        self.assertEqual(len(result), 3)
        # 최신순
        self.assertEqual(result[0]['title'], '제목3')
        self.assertEqual(result[1]['title'], '제목2')

    def test_more_than_five(self):
        """7개 항목 → 상위 5개만"""
        items = [
            {'content': f'제목{i}', 'style': 'blog_seo', 'created_at': f'2026-03-{10+i:02d}'}
            for i in range(7)
        ]
        result = self._extract_recent(items)
        self.assertEqual(len(result), 5)

    def test_sorted_by_created_at_desc(self):
        """created_at 기준 최신순 정렬"""
        items = [
            {'content': '오래된', 'style': 'a', 'created_at': '2026-03-01'},
            {'content': '최신', 'style': 'b', 'created_at': '2026-03-17'},
            {'content': '중간', 'style': 'c', 'created_at': '2026-03-10'},
        ]
        result = self._extract_recent(items)
        self.assertEqual(result[0]['title'], '최신')
        self.assertEqual(result[1]['title'], '중간')
        self.assertEqual(result[2]['title'], '오래된')

    def test_empty_content_fallback(self):
        """content 없으면 '(제목 없음)'"""
        items = [{'content': '', 'style': 'blog_seo', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        self.assertEqual(result[0]['title'], '(제목 없음)')

    def test_none_content_fallback(self):
        """content=None → '(제목 없음)'"""
        items = [{'content': None, 'style': 'blog_seo', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        self.assertEqual(result[0]['title'], '(제목 없음)')

    def test_title_first_line_only(self):
        """content의 첫 줄만 제목으로 사용"""
        items = [{'content': '첫 줄 제목\n두 번째 줄\n세 번째 줄', 'style': 's', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        self.assertEqual(result[0]['title'], '첫 줄 제목')

    def test_title_max_80_chars(self):
        """제목이 80자 넘으면 잘림"""
        long_content = 'A' * 100
        items = [{'content': long_content, 'style': 's', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        self.assertLessEqual(len(result[0]['title']), 80)

    def test_structure_keys(self):
        """각 항목이 title, style, created_at 키를 가짐"""
        items = [{'content': '테스트', 'style': 'blog_seo', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        for item in result:
            self.assertIn('title', item)
            self.assertIn('style', item)
            self.assertIn('created_at', item)

    def test_missing_style_defaults_unknown(self):
        """style 없으면 'unknown'"""
        items = [{'content': '테스트', 'created_at': '2026-03-17'}]
        result = self._extract_recent(items)
        self.assertEqual(result[0]['style'], 'unknown')


if __name__ == '__main__':
    unittest.main()
