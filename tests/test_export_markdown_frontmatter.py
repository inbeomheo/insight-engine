"""export_markdown frontmatter 옵션 테스트 (R33)"""
import io
import json
import unittest
from unittest.mock import patch

from services.export.export_service import export_markdown


class TestExportMarkdownFrontmatter(unittest.TestCase):
    """export_markdown의 frontmatter 파라미터 단위 테스트"""

    def test_no_frontmatter_default(self):
        """frontmatter 미지정 시 기존 동작 유지"""
        buf = export_markdown('제목', '내용')
        text = buf.read().decode('utf-8')
        self.assertTrue(text.startswith('# 제목'))
        self.assertNotIn('---', text)

    def test_frontmatter_with_title_date(self):
        """title, date frontmatter 포함"""
        fm = {'title': '테스트 제목', 'date': '2026-03-17'}
        buf = export_markdown('제목', '내용', frontmatter=fm)
        text = buf.read().decode('utf-8')
        self.assertTrue(text.startswith('---'))
        self.assertIn('title: 테스트 제목', text)
        self.assertIn('date: 2026-03-17', text)
        # frontmatter 종료 후 본문
        self.assertIn('# 제목', text)

    def test_frontmatter_with_tags_list(self):
        """tags 리스트가 YAML 리스트 형식으로 출력"""
        fm = {'tags': ['AI', '콘텐츠', '자동화']}
        buf = export_markdown('제목', '내용', frontmatter=fm)
        text = buf.read().decode('utf-8')
        self.assertIn('tags:', text)
        self.assertIn('  - AI', text)
        self.assertIn('  - 콘텐츠', text)
        self.assertIn('  - 자동화', text)

    def test_frontmatter_none_no_effect(self):
        """frontmatter=None이면 기존 동작"""
        buf = export_markdown('제목', '내용', frontmatter=None)
        text = buf.read().decode('utf-8')
        self.assertNotIn('---', text)

    def test_frontmatter_empty_dict_no_effect(self):
        """frontmatter={} (빈 딕셔너리)이면 frontmatter 없음"""
        buf = export_markdown('제목', '내용', frontmatter={})
        text = buf.read().decode('utf-8')
        self.assertNotIn('---', text)

    def test_frontmatter_structure_valid(self):
        """frontmatter 구조가 --- 로 시작하고 --- 로 끝남"""
        fm = {'title': 'Test', 'author': 'AI'}
        buf = export_markdown('제목', '내용', frontmatter=fm)
        text = buf.read().decode('utf-8')
        lines = text.split('\n')
        self.assertEqual(lines[0], '---')
        # 두 번째 --- 찾기
        close_idx = None
        for i in range(1, len(lines)):
            if lines[i] == '---':
                close_idx = i
                break
        self.assertIsNotNone(close_idx)


class TestExportMarkdownRoute(unittest.TestCase):
    """라우트 레벨 frontmatter 전달 테스트"""

    def setUp(self):
        from app import create_app

        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_route_passes_frontmatter(self, mock_sb):
        """POST /api/export/markdown에 frontmatter 전달 시 YAML 헤더 포함"""
        resp = self.client.post('/api/export/markdown', json={
            'title': '테스트',
            'content': '본문 내용입니다.',
            'frontmatter': {
                'title': '테스트',
                'date': '2026-03-17',
                'tags': ['AI', 'test'],
            },
        }, headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode('utf-8')
        self.assertIn('---', text)
        self.assertIn('title: 테스트', text)
        self.assertIn('  - AI', text)

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_route_without_frontmatter(self, mock_sb):
        """frontmatter 미전달 시 기존 동작"""
        resp = self.client.post('/api/export/markdown', json={
            'title': '테스트',
            'content': '본문 내용입니다.',
        }, headers={'Origin': 'http://localhost:3000'})
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode('utf-8')
        self.assertNotIn('---', text)


if __name__ == '__main__':
    unittest.main()
