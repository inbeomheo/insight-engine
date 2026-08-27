"""usage_decorator 단위 테스트 — check_usage, require_usage, get_usage_for_response"""
from concurrent.futures import ThreadPoolExecutor
import unittest
from unittest.mock import patch, MagicMock
from flask import Flask, g, jsonify


def _reservation():
    from services.usage.usage_service import UsageReservation
    from src.contexts.identity.application.ports import QuotaReservation

    before = {'usage_count': 5, 'max_usage': 5, 'can_use': True, 'is_admin': False}
    after = {**before, 'usage_count': 4}
    quota = QuotaReservation(
        reservation_id='reservation-1',
        idempotency_key='client:key',
        request_fingerprint='a' * 64,
        owner_token_hash='b' * 64,
        amount=1,
        remaining=4,
        max_usage=5,
        owned=True,
        replayed=False,
    )
    return UsageReservation(quota, before, after, True)


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
    def test_success_is_pre_reserved_without_post_decrement(self, mock_usage_svc, mock_enabled):
        from services.usage.usage_decorator import require_usage

        reservation = _reservation()
        mock_usage_svc.reserve_for_request.return_value = reservation

        @require_usage
        def dummy():
            return jsonify({'ok': True})

        with self.app.test_request_context():
            g.user_id = 'user-2'
            result = dummy()
            mock_usage_svc.reserve_for_request.assert_called_once_with('user-2')
            mock_usage_svc.decrement.assert_not_called()
            self.assertEqual(g.updated_usage, reservation.usage_after)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_failure_before_cost_boundary_refunds_reservation(
        self, mock_usage_svc, mock_enabled
    ):
        from services.usage.usage_decorator import require_usage

        reservation = _reservation()
        mock_usage_svc.reserve_for_request.return_value = reservation
        mock_usage_svc.refund_reservation_quietly.return_value = (
            reservation.usage_before
        )

        @require_usage
        def dummy():
            raise RuntimeError('validation failed')

        with self.app.test_request_context():
            g.user_id = 'user-before-cost'
            with self.assertRaisesRegex(RuntimeError, 'validation failed'):
                dummy()
            mock_usage_svc.refund_reservation_quietly.assert_called_once_with(
                'user-before-cost', reservation
            )
            self.assertEqual(g.updated_usage, reservation.usage_before)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_failure_response_after_cost_boundary_keeps_charge(
        self, mock_usage_svc, mock_enabled
    ):
        from services.usage.usage_decorator import (
            mark_usage_charge_committed,
            require_usage,
        )

        reservation = _reservation()
        mock_usage_svc.reserve_for_request.return_value = reservation

        @require_usage
        def dummy():
            self.assertTrue(mark_usage_charge_committed())
            return jsonify({'error': 'provider failed'}), 502

        with self.app.test_request_context():
            g.user_id = 'user-after-cost'
            response, status = dummy()
            self.assertEqual(status, 502)
            self.assertEqual(response.get_json()['error'], 'provider failed')
            mock_usage_svc.refund_reservation_quietly.assert_not_called()
            self.assertEqual(g.updated_usage, reservation.usage_after)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_exception_after_cost_boundary_keeps_charge(
        self, mock_usage_svc, mock_enabled
    ):
        from services.usage.usage_decorator import (
            mark_usage_charge_committed,
            require_usage,
        )

        reservation = _reservation()
        mock_usage_svc.reserve_for_request.return_value = reservation

        @require_usage
        def dummy():
            mark_usage_charge_committed()
            raise RuntimeError('provider response lost')

        with self.app.test_request_context():
            g.user_id = 'user-after-cost'
            with self.assertRaisesRegex(RuntimeError, 'provider response lost'):
                dummy()
            mock_usage_svc.refund_reservation_quietly.assert_not_called()
            self.assertEqual(g.updated_usage, reservation.usage_after)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService')
    def test_skip_flag_after_cost_boundary_does_not_refund(
        self, mock_usage_svc, mock_enabled
    ):
        from services.usage.usage_decorator import (
            mark_usage_charge_committed,
            require_usage,
        )

        reservation = _reservation()
        mock_usage_svc.reserve_for_request.return_value = reservation

        @require_usage
        def dummy():
            mark_usage_charge_committed()
            g.skip_usage_decrement = True
            return jsonify({'ok': True})

        with self.app.test_request_context():
            g.user_id = 'user-after-cost'
            self.assertEqual(dummy().status_code, 200)
            mock_usage_svc.refund_reservation.assert_not_called()
            self.assertEqual(g.updated_usage, reservation.usage_after)


class TestUsageChargeState(unittest.TestCase):
    def test_explicit_state_is_thread_safe_and_commits_once(self):
        from services.usage.usage_decorator import UsageChargeState

        state = UsageChargeState()
        with ThreadPoolExecutor(max_workers=8) as executor:
            transitions = list(
                executor.map(lambda _index: state.mark_committed(), range(64))
            )

        self.assertTrue(state.committed)
        self.assertEqual(sum(transitions), 1)

    def test_helper_without_request_or_explicit_state_is_noop(self):
        from services.usage.usage_decorator import mark_usage_charge_committed

        self.assertFalse(mark_usage_charge_committed())

    def test_helper_commits_explicit_state_without_request_context(self):
        from services.usage.usage_decorator import (
            UsageChargeState,
            mark_usage_charge_committed,
        )

        state = UsageChargeState()

        self.assertTrue(mark_usage_charge_committed(state))
        self.assertTrue(state.committed)

    def test_captured_worker_callback_keeps_state_and_lease_boundary(self):
        from services.usage.usage_decorator import (
            UsageChargeState,
            capture_usage_charge_callback,
        )
        from services.usage.usage_lock import UsageLockUnavailable

        state = UsageChargeState()
        lease = MagicMock(lost=False, released=False)
        with Flask(__name__).test_request_context():
            g.usage_charge_state = state
            g.usage_lease = lease
            callback = capture_usage_charge_callback()

        self.assertIsNotNone(callback)
        self.assertTrue(callback())
        self.assertTrue(state.committed)

        second_state = UsageChargeState()
        lost_lease = MagicMock(
            lost=True,
            released=False,
            lost_reason=RuntimeError('lost'),
        )
        with Flask(__name__).test_request_context():
            g.usage_charge_state = second_state
            g.usage_lease = lost_lease
            lost_callback = capture_usage_charge_callback()

        with self.assertRaises(UsageLockUnavailable):
            lost_callback()
        self.assertFalse(second_state.committed)

        released_state = UsageChargeState()
        released_lease = MagicMock(lost=False, released=True)
        with Flask(__name__).test_request_context():
            g.usage_charge_state = released_state
            g.usage_lease = released_lease
            released_callback = capture_usage_charge_callback()

        with self.assertRaises(UsageLockUnavailable):
            released_callback()
        self.assertFalse(released_state.committed)


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
