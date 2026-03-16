"""usage_decorator 단위 테스트 — check_usage, require_usage, get_usage_for_response"""
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, g, jsonify


class TestCheckUsage(unittest.TestCase):
    """check_usage 데코레이터"""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    def test_supabase_disabled_passes_through(self, mock_enabled):
        from services.usage.usage_decorator import check_usage

        @check_usage
        def dummy():
            return jsonify({'ok': True})

        with self.app.test_request_context():
            result = dummy()
            self.assertEqual(result.status_code, 200)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_usage_exceeded_returns_429(self, mock_usage_svc, mock_enabled):
        from services.usage.usage_decorator import check_usage

        mock_usage_svc.check_can_use.return_value = (False, {'remaining': 0, 'is_admin': False})

        @check_usage
        def dummy():
            return jsonify({'ok': True})

        with self.app.test_request_context():
            g.user_id = 'user-1'
            result = dummy()
            # check_usage 가 tuple (response, 429) 반환
            if isinstance(result, tuple):
                resp, code = result
                self.assertEqual(code, 429)
            else:
                self.assertEqual(result.status_code, 429)


class TestRequireUsage(unittest.TestCase):
    """require_usage 데코레이터"""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    def test_supabase_disabled_no_decrement(self, mock_enabled):
        from services.usage.usage_decorator import require_usage

        @require_usage
        def dummy():
            return jsonify({'generated': True})

        with self.app.test_request_context():
            result = dummy()
            self.assertEqual(result.status_code, 200)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_success_decrements(self, mock_usage_svc, mock_enabled):
        from services.usage.usage_decorator import require_usage

        mock_usage_svc.check_can_use.return_value = (True, {'remaining': 5, 'is_admin': False})
        mock_usage_svc.decrement.return_value = {'remaining': 4}

        @require_usage
        def dummy():
            return jsonify({'ok': True})

        with self.app.test_request_context():
            g.user_id = 'user-2'
            result = dummy()
            mock_usage_svc.decrement.assert_called_once_with('user-2')


class TestGetUsageForResponse(unittest.TestCase):
    """get_usage_for_response: g 컨텍스트에서 사용량 반환"""

    def setUp(self):
        self.app = Flask(__name__)

    def test_returns_updated_usage(self):
        from services.usage.usage_decorator import get_usage_for_response

        with self.app.test_request_context():
            g.updated_usage = {'remaining': 4}
            g.usage = {'remaining': 5}
            result = get_usage_for_response()
            self.assertEqual(result['remaining'], 4)

    def test_falls_back_to_usage(self):
        from services.usage.usage_decorator import get_usage_for_response

        with self.app.test_request_context():
            g.usage = {'remaining': 5}
            result = get_usage_for_response()
            self.assertEqual(result['remaining'], 5)


if __name__ == '__main__':
    unittest.main()
