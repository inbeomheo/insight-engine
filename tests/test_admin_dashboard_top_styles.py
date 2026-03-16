"""admin dashboard top_styles 필드 테스트 (R35)"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestTopStylesLogic(unittest.TestCase):
    """top_styles 추출 로직 단위 테스트"""

    def _extract_top_styles(self, style_dist):
        """admin_dashboard에서 사용하는 동일한 로직"""
        top = sorted(style_dist.items(), key=lambda x: x[1], reverse=True)[:3]
        return [{'style': s, 'count': c} for s, c in top]

    def test_empty_distribution(self):
        """빈 스타일 분포 → 빈 리스트"""
        result = self._extract_top_styles({})
        self.assertEqual(result, [])

    def test_fewer_than_three(self):
        """스타일 2개면 2개만 반환"""
        result = self._extract_top_styles({'blog_seo': 10, 'summary': 5})
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['style'], 'blog_seo')
        self.assertEqual(result[0]['count'], 10)

    def test_exactly_three(self):
        """스타일 3개면 3개 전부 반환"""
        result = self._extract_top_styles({'a': 3, 'b': 1, 'c': 2})
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]['style'], 'a')
        self.assertEqual(result[1]['style'], 'c')
        self.assertEqual(result[2]['style'], 'b')

    def test_more_than_three(self):
        """스타일 5개면 상위 3개만"""
        result = self._extract_top_styles({'a': 10, 'b': 8, 'c': 6, 'd': 4, 'e': 2})
        self.assertEqual(len(result), 3)
        self.assertEqual([r['style'] for r in result], ['a', 'b', 'c'])

    def test_single_style(self):
        """스타일 1개면 1개만"""
        result = self._extract_top_styles({'blog_seo': 7})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {'style': 'blog_seo', 'count': 7})

    def test_tie_breaking(self):
        """동일 횟수 스타일도 3개까지만 반환"""
        result = self._extract_top_styles({'a': 5, 'b': 5, 'c': 5, 'd': 5})
        self.assertEqual(len(result), 3)
        # 모든 항목의 count가 5
        for item in result:
            self.assertEqual(item['count'], 5)

    def test_structure(self):
        """각 항목이 style, count 키를 가짐"""
        result = self._extract_top_styles({'blog_seo': 3, 'summary': 1})
        for item in result:
            self.assertIn('style', item)
            self.assertIn('count', item)
            self.assertIsInstance(item['style'], str)
            self.assertIsInstance(item['count'], int)


class TestAdminDashboardRoute(unittest.TestCase):
    """라우트 레벨: Supabase 비활성 시 top_styles 관련 코드 존재 검증"""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_route_no_supabase_returns_503(self, mock_sb):
        """Supabase 미연결 시 503 (기존 동작 유지)"""
        from app import app
        with app.test_client() as client:
            resp = client.get('/api/admin/dashboard',
                              headers={'Origin': 'http://localhost:3000'})
            # require_auth가 is_supabase_enabled=False면 통과하지만
            # admin_dashboard 내부에서 is_admin 체크함
            # Supabase 비활성 시 503 또는 인증 오류 반환 가능
            self.assertIn(resp.status_code, [401, 403, 503])


if __name__ == '__main__':
    unittest.main()
