"""
사용량 서비스 단위 테스트
UsageService, 데코레이터, 제한 로직
"""
import unittest
from unittest.mock import patch, MagicMock


class TestUsageService(unittest.TestCase):
    """UsageService 테스트"""

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=False)
    def test_supabase_disabled_returns_admin_usage(self, mock_enabled):
        """Supabase 비활성화 시 무제한 사용"""
        from services.usage.usage_service import UsageService, ADMIN_USAGE

        can_use, usage = UsageService.check_can_use('any-user-id')

        self.assertTrue(can_use)
        self.assertEqual(usage, ADMIN_USAGE)

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.is_admin', return_value=True)
    def test_admin_user_unlimited(self, mock_admin, mock_enabled):
        """관리자는 무제한 사용"""
        from services.usage.usage_service import UsageService, ADMIN_USAGE

        can_use, usage = UsageService.check_can_use('admin-user-id')

        self.assertTrue(can_use)
        self.assertEqual(usage, ADMIN_USAGE)

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.is_admin', return_value=False)
    @patch('services.usage.usage_service.get_usage')
    def test_normal_user_with_remaining(self, mock_get_usage, mock_admin, mock_enabled):
        """일반 사용자 - 남은 횟수 있음"""
        mock_get_usage.return_value = {
            'usage_count': 3,
            'max_usage': 5,
            'can_use': True,
            'is_admin': False
        }

        from services.usage.usage_service import UsageService

        can_use, usage = UsageService.check_can_use('normal-user')

        self.assertTrue(can_use)
        self.assertEqual(usage['usage_count'], 3)

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.is_admin', return_value=False)
    @patch('services.usage.usage_service.get_usage')
    def test_normal_user_limit_exceeded(self, mock_get_usage, mock_admin, mock_enabled):
        """일반 사용자 - 횟수 소진"""
        mock_get_usage.return_value = {
            'usage_count': 5,
            'max_usage': 5,
            'can_use': False,
            'is_admin': False
        }

        from services.usage.usage_service import UsageService

        can_use, usage = UsageService.check_can_use('exhausted-user')

        self.assertFalse(can_use)


class TestUsageDecorator(unittest.TestCase):
    """사용량 데코레이터 테스트"""

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_check_usage_decorator_bypasses_when_disabled(self, mock_enabled):
        """Supabase 비활성화 시 데코레이터 통과"""
        from services.usage.usage_decorator import check_usage
        from flask import Flask, g

        app = Flask(__name__)

        @check_usage
        def test_route():
            return {'success': True}

        with app.app_context():
            result = test_route()
            self.assertEqual(result, {'success': True})

    @patch('services.supabase_service.is_supabase_enabled', return_value=False)
    def test_require_usage_decorator_bypasses_when_disabled(self, mock_enabled):
        """Supabase 비활성화 시 require_usage 통과"""
        from services.usage.usage_decorator import require_usage
        from flask import Flask, g

        app = Flask(__name__)

        @require_usage
        def test_route():
            return {'success': True}

        with app.app_context():
            result = test_route()
            self.assertEqual(result, {'success': True})



    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.decrement')
    @patch('services.usage.usage_decorator.UsageService.check_can_use')
    def test_require_usage_decrements_only_on_success_status(self, mock_check_can_use, mock_decrement, mock_enabled):
        """require_usage는 2xx/3xx 응답에서만 차감"""
        from services.usage.usage_decorator import require_usage
        from flask import Flask, g

        app = Flask(__name__)
        usage = {'usage_count': 3, 'max_usage': 5, 'can_use': True, 'is_admin': False}
        mock_check_can_use.return_value = (True, usage)
        mock_decrement.return_value = {'usage_count': 2, 'max_usage': 5, 'can_use': True, 'is_admin': False}

        @require_usage
        def ok_route():
            return {'success': True}, 200

        @require_usage
        def bad_route():
            return {'error': 'bad request'}, 400

        with app.app_context():
            g.user_id = 'user-1'
            ok_route()
            mock_decrement.assert_called_once_with('user-1')
            self.assertEqual(g.updated_usage['usage_count'], 2)

            mock_decrement.reset_mock()
            g.user_id = 'user-1'
            bad_route()
            mock_decrement.assert_not_called()
            self.assertEqual(g.updated_usage['usage_count'], 3)


class TestAdminUsageConstant(unittest.TestCase):
    """ADMIN_USAGE 상수 테스트"""

    def test_admin_usage_structure(self):
        """ADMIN_USAGE 구조 검증"""
        from services.usage.usage_service import ADMIN_USAGE

        # 필수 필드 확인
        self.assertIn('usage_count', ADMIN_USAGE)
        self.assertIn('max_usage', ADMIN_USAGE)
        self.assertIn('can_use', ADMIN_USAGE)
        self.assertIn('is_admin', ADMIN_USAGE)

        # 관리자는 항상 사용 가능
        self.assertTrue(ADMIN_USAGE['can_use'])
        self.assertTrue(ADMIN_USAGE['is_admin'])

    def test_admin_usage_high_limit(self):
        """ADMIN_USAGE는 높은 사용량 제한을 가짐"""
        from services.usage.usage_service import ADMIN_USAGE

        # 일반 사용자 제한(5회)보다 훨씬 높아야 함
        self.assertGreater(ADMIN_USAGE['max_usage'], 100)


class TestUsageServiceDecrement(unittest.TestCase):
    """UsageService.decrement 테스트"""

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=False)
    def test_decrement_when_supabase_disabled(self, mock_enabled):
        """Supabase 비활성화 시 차감 스킵"""
        from services.usage.usage_service import UsageService, ADMIN_USAGE

        result = UsageService.decrement('any-user')

        self.assertEqual(result, ADMIN_USAGE)

    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.is_admin', return_value=True)
    def test_decrement_admin_no_change(self, mock_admin, mock_enabled):
        """관리자는 차감하지 않음"""
        from services.usage.usage_service import UsageService, ADMIN_USAGE

        result = UsageService.decrement('admin-user')

        self.assertEqual(result, ADMIN_USAGE)


if __name__ == '__main__':
    unittest.main()

