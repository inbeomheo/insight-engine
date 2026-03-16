"""R18: /api/admin/dashboard 응답에 avg_generation_time 필드 검증"""
import unittest
from unittest.mock import patch, MagicMock


class TestDashboardAvgGenerationTime(unittest.TestCase):
    """대시보드 응답에 avg_generation_time 필드가 포함되는지 검증"""

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
    def setUp(self, _mock_enabled):
        import app as flask_app
        self.app = flask_app.app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('routes.auth_routes.is_admin', return_value=True)
    @patch('routes.auth_routes.get_supabase')
    @patch('routes.auth_routes.is_supabase_enabled', return_value=True)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_generation_time_present(self, _mock_sb_global, mock_sb_enabled, mock_get_sb, _mock_admin):
        """avg_generation_time 필드가 응답에 포함되어야 함"""
        mock_supabase = MagicMock()

        # 히스토리 데이터 mock
        histories_result = MagicMock()
        histories_result.data = [
            {'created_at': '2026-03-15T00:00:00Z', 'style': 'blog_seo', 'elapsed_time': 3.0, 'success': True},
            {'created_at': '2026-03-15T01:00:00Z', 'style': 'summary', 'elapsed_time': 5.0, 'success': True},
            {'created_at': '2026-03-15T02:00:00Z', 'style': 'blog_seo', 'elapsed_time': 4.0, 'success': False},
        ]

        # 사용량 데이터 mock
        usage_result = MagicMock()
        usage_result.data = []

        # Supabase 체인 mock
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_gte = MagicMock()
        mock_order = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.gte.return_value = mock_gte

        # 첫 번째 호출(histories): .execute() 바로 반환
        mock_gte.execute.return_value = histories_result
        # 두 번째 호출(usage): .order().execute() 체인
        mock_gte.order.return_value = mock_order
        mock_order.execute.return_value = usage_result

        mock_get_sb.return_value = mock_supabase

        with self.app.test_request_context():
            from flask import g
            g.user_id = 'test-user-id'

            resp = self.client.get(
                '/api/admin/dashboard',
                headers={'Origin': 'http://localhost:3000', 'Authorization': 'Bearer test-token'}
            )

        data = resp.get_json()
        self.assertIn('avg_generation_time', data)
        # (3.0 + 5.0 + 4.0) / 3 = 4.0
        self.assertEqual(data['avg_generation_time'], 4.0)
        # avg_time과 동일 값인지 확인
        self.assertEqual(data['avg_generation_time'], data['avg_time'])

    @patch('routes.auth_routes.is_admin', return_value=True)
    @patch('routes.auth_routes.get_supabase')
    @patch('routes.auth_routes.is_supabase_enabled', return_value=True)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_generation_time_zero_when_no_data(self, _mock_sb_global, mock_sb_enabled, mock_get_sb, _mock_admin):
        """히스토리가 없으면 avg_generation_time이 0이어야 함"""
        mock_supabase = MagicMock()

        histories_result = MagicMock()
        histories_result.data = []

        usage_result = MagicMock()
        usage_result.data = []

        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_gte = MagicMock()
        mock_order = MagicMock()

        mock_supabase.table.return_value = mock_table
        mock_table.select.return_value = mock_select
        mock_select.gte.return_value = mock_gte
        mock_gte.execute.return_value = histories_result
        mock_gte.order.return_value = mock_order
        mock_order.execute.return_value = usage_result

        mock_get_sb.return_value = mock_supabase

        with self.app.test_request_context():
            from flask import g
            g.user_id = 'test-user-id'

            resp = self.client.get(
                '/api/admin/dashboard',
                headers={'Origin': 'http://localhost:3000', 'Authorization': 'Bearer test-token'}
            )

        data = resp.get_json()
        self.assertIn('avg_generation_time', data)
        self.assertEqual(data['avg_generation_time'], 0)


if __name__ == '__main__':
    unittest.main()
