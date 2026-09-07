"""
사용량 서비스 단위 테스트
UsageService, 데코레이터, 제한 로직
"""
import threading
import unittest
from unittest.mock import patch, MagicMock


def _make_reservation(*, owned=True, billable=True, admin=False):
    from services.usage.usage_service import ADMIN_USAGE, UsageReservation
    from src.contexts.identity.application.ports import QuotaReservation

    if admin or not billable:
        usage = dict(ADMIN_USAGE)
        return UsageReservation(None, usage, usage, False)
    before = {
        'usage_count': 3,
        'max_usage': 5,
        'can_use': True,
        'is_admin': False,
    }
    after = {**before, 'usage_count': 2}
    quota = QuotaReservation(
        reservation_id='reservation-1',
        idempotency_key='client:key',
        request_fingerprint='a' * 64,
        owner_token_hash='b' * 64,
        amount=1,
        remaining=2,
        max_usage=5,
        owned=owned,
        replayed=not owned,
    )
    return UsageReservation(quota, before, after, billable)


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


class TestUsageRequestIdentity(unittest.TestCase):
    def test_fallback_key_is_stable_only_within_one_request(self):
        from flask import Flask
        from services.usage.usage_service import UsageService

        app = Flask(__name__)
        with app.test_request_context('/generate', method='POST', json={'b': 2, 'a': 1}):
            first = UsageService.request_identity('user-1')
            repeated_in_same_request = UsageService.request_identity('user-1')
        with app.test_request_context('/generate', method='POST', json={'a': 1, 'b': 2}):
            second = UsageService.request_identity('user-1')

        self.assertEqual(first, repeated_in_same_request)
        self.assertNotEqual(first[0], second[0])
        self.assertEqual(first[1], second[1])
        self.assertTrue(first[0].startswith('fallback:'))

    def test_client_key_is_validated_and_stored_only_as_hash(self):
        from flask import Flask
        from services.usage.usage_service import UsageService

        app = Flask(__name__)
        raw_key = 'request-1234'
        with app.test_request_context(
            '/generate',
            method='POST',
            json={'a': 1},
            headers={'Idempotency-Key': raw_key},
        ):
            stored_key, fingerprint = UsageService.request_identity('user-1')

        self.assertNotIn(raw_key, stored_key)
        self.assertTrue(stored_key.startswith('client:'))
        self.assertEqual(len(fingerprint), 64)

    def test_invalid_client_key_is_rejected(self):
        from flask import Flask
        from services.usage.usage_service import InvalidIdempotencyKey, UsageService

        app = Flask(__name__)
        with app.test_request_context(
            '/generate',
            method='POST',
            json={'a': 1},
            headers={'Idempotency-Key': 'bad key with spaces'},
        ):
            with self.assertRaises(InvalidIdempotencyKey):
                UsageService.request_identity('user-1')

    @patch('services.usage.usage_service._get_account_repository')
    def test_replayed_request_does_not_refund_other_owner(self, mock_repo):
        from services.usage.usage_service import UsageService

        reservation = _make_reservation(owned=False)
        result = UsageService.refund_reservation('user-1', reservation)

        self.assertEqual(result, reservation.usage_after)
        mock_repo.assert_not_called()

    @patch('services.usage.usage_service.mark_usage_accounting_unavailable')
    @patch('services.usage.usage_service._is_admin_cached', return_value=False)
    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.UsageService.request_identity')
    @patch(
        'src.contexts.identity.infrastructure.supabase_usage_gateway.SupabaseUsageGateway.reserve'
    )
    def test_idempotency_conflict_does_not_trip_accounting_breaker(
        self,
        mock_reserve,
        mock_identity,
        _mock_enabled,
        _mock_admin,
        mock_mark_unavailable,
    ):
        from flask import Flask
        from src.contexts.identity.application.ports import QuotaReservationConflict
        from services.usage.usage_service import (
            InvalidIdempotencyReplay,
            UsageService,
        )

        app = Flask(__name__)
        mock_identity.return_value = ('client:key', 'a' * 64)
        mock_reserve.side_effect = QuotaReservationConflict('conflict')

        with app.test_request_context('/generate', method='POST'):
            with self.assertRaises(InvalidIdempotencyReplay):
                UsageService.reserve_for_request('user-1')

        mock_mark_unavailable.assert_not_called()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_replayed_request_is_rejected_before_costly_work(
        self, mock_reserve, _mock_enabled
    ):
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage
        from services.usage.usage_service import UsageReservationReplay

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''
        usage = {'usage_count': 2, 'max_usage': 3, 'can_use': True}
        mock_reserve.side_effect = UsageReservationReplay(usage)
        costly_work = MagicMock()

        @require_usage
        def route():
            costly_work()
            return {'ok': True}

        with app.test_request_context('/generate', method='POST'):
            g.user_id = 'user-1'
            response = app.make_response(route())

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['code'], 'IDEMPOTENCY_REPLAY')
        self.assertEqual(response.get_json()['usage'], usage)
        costly_work.assert_not_called()


class TestUsageDecorator(unittest.TestCase):
    """사용량 데코레이터 테스트"""

    def test_usage_lease_release_retries_one_transient_failure(self):
        from services.usage.usage_decorator import _release_usage_lease

        class FlakyLease:
            lost = False

            def __init__(self):
                self.calls = 0

            @property
            def released(self):
                return self.calls >= 2

            def release(self):
                self.calls += 1

        lease = FlakyLease()
        _release_usage_lease(lease)

        self.assertEqual(lease.calls, 2)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
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
    @patch('services.usage.usage_decorator.UsageService.refund_reservation_quietly')
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_require_usage_reserves_before_work_and_refunds_failure(
        self, mock_reserve, mock_refund, mock_enabled
    ):
        """비용 작업 전 예약하며 실패 응답은 자신의 예약을 환불."""
        from services.usage.usage_decorator import require_usage
        from flask import Flask, g

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''
        reservation = _make_reservation()
        mock_reserve.return_value = reservation
        mock_refund.return_value = reservation.usage_before
        call_order = []
        mock_reserve.side_effect = lambda _user_id: (
            call_order.append('reserve') or reservation
        )

        @require_usage
        def ok_route():
            call_order.append('work')
            return {'success': True}, 200

        @require_usage
        def bad_route():
            return {'error': 'bad request'}, 400

        with app.test_request_context():
            g.user_id = 'user-1'
            ok_route()
            self.assertEqual(call_order, ['reserve', 'work'])
            mock_refund.assert_not_called()
            self.assertEqual(g.updated_usage['usage_count'], 2)

        with app.test_request_context():
            g.user_id = 'user-1'
            bad_route()
            mock_refund.assert_called_once_with('user-1', reservation)
            self.assertEqual(g.updated_usage['usage_count'], 3)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.refund_reservation')
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_require_usage_keeps_admin_and_cache_hit_non_billable(
        self, mock_reserve, mock_refund, mock_enabled
    ):
        """관리자는 미예약, 캐시 적중은 선예약을 즉시 환불."""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage
        from services.usage.usage_service import ADMIN_USAGE

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''

        @require_usage
        def admin_route():
            return {'success': True}, 200

        @require_usage
        def cached_route():
            g.skip_usage_decrement = True
            return {'cached': True}, 200

        admin_reservation = _make_reservation(admin=True)
        cached_reservation = _make_reservation()
        mock_reserve.side_effect = [admin_reservation, cached_reservation]
        mock_refund.return_value = cached_reservation.usage_before
        with app.test_request_context():
            g.user_id = 'admin-user'
            response = app.make_response(admin_route())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(g.updated_usage, ADMIN_USAGE)

        with app.test_request_context():
            g.user_id = 'cached-user'
            response = app.make_response(cached_route())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(g.updated_usage, cached_reservation.usage_before)

        mock_refund.assert_called_once_with('cached-user', cached_reservation)

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_same_user_concurrent_request_is_rejected_without_waiting(
        self, mock_reserve, mock_enabled
    ):
        """로컬 폴백은 동일 사용자의 예약→실행 구간을 비차단 직렬화."""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''
        entered = threading.Event()
        finish = threading.Event()
        first_response = {}
        mock_reserve.return_value = _make_reservation()

        @require_usage
        def slow_route():
            entered.set()
            finish.wait(timeout=2)
            return {'success': True}, 200

        def run_first_request():
            with app.test_request_context():
                g.user_id = 'same-user'
                first_response['response'] = app.make_response(slow_route())

        worker = threading.Thread(target=run_first_request)
        worker.start()
        self.assertTrue(entered.wait(timeout=1), '첫 번째 요청이 실행 구간에 진입해야 합니다.')

        try:
            with app.test_request_context():
                g.user_id = 'same-user'
                second_response = app.make_response(slow_route())
        finally:
            finish.set()
            worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(second_response.status_code, 409)
        self.assertEqual(second_response.get_json()['code'], 'USAGE_REQUEST_IN_PROGRESS')
        self.assertEqual(first_response['response'].status_code, 200)
        mock_reserve.assert_called_once_with('same-user')

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch('services.usage.usage_lock._get_redis_client')
    def test_redis_connection_failure_rejects_before_costly_work(
        self, mock_get_client, mock_reserve, mock_enabled
    ):
        """Redis가 설정된 경우 연결 실패를 로컬 잠금으로 폴백하지 않음"""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage

        app = Flask(__name__)
        app.config['REDIS_URL'] = 'redis://lock.invalid:6379/0'
        redis_lock = MagicMock()
        redis_lock.acquire.side_effect = OSError('연결 실패')
        redis_client = MagicMock()
        redis_client.get.return_value = None
        redis_client.lock.return_value = redis_lock
        mock_get_client.return_value = redis_client
        route_called = MagicMock()

        @require_usage
        def costly_route():
            route_called()
            return {'success': True}, 200

        with patch.dict('os.environ', {'REDIS_URL': 'redis://lock.invalid:6379/0'}):
            with app.test_request_context():
                g.user_id = 'redis-failure-user'
                response = app.make_response(costly_route())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        route_called.assert_not_called()
        mock_reserve.assert_not_called()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch('services.usage.usage_lock._get_redis_client')
    def test_redis_lock_is_non_blocking_and_released_after_full_usage_flow(
        self, mock_get_client, mock_reserve, mock_enabled
    ):
        """Redis 분산 잠금은 무대기 획득하고 차감 후 해제됨"""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage

        app = Flask(__name__)
        app.config['REDIS_URL'] = 'redis://locks:6379/0'
        redis_lock = MagicMock()
        redis_lock.acquire.return_value = True
        redis_client = MagicMock()
        redis_client.get.return_value = None
        redis_client.lock.return_value = redis_lock
        mock_get_client.return_value = redis_client
        mock_reserve.return_value = _make_reservation()

        @require_usage
        def costly_route():
            return {'success': True}, 200

        with patch.dict('os.environ', {'REDIS_URL': 'redis://locks:6379/0'}):
            with app.test_request_context():
                g.user_id = 'redis-user'
                response = app.make_response(costly_route())

        self.assertEqual(response.status_code, 200)
        redis_lock.acquire.assert_called_once_with(blocking=False)
        redis_lock.release.assert_called_once_with()
        mock_reserve.assert_called_once_with('redis-user')

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_require_usage_fails_before_work_when_reservation_unavailable(
        self, mock_reserve, mock_enabled
    ):
        """예약 장애 시 비용 작업을 시작하지 않고 503."""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage
        from services.usage.usage_service import UsageAccountingUnavailable

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''
        mock_reserve.side_effect = UsageAccountingUnavailable('billing down')
        route_called = MagicMock()

        @require_usage
        def costly_route():
            route_called()
            return {'success': True}, 200

        with app.test_request_context():
            g.user_id = 'accounting-failure-user'
            response = app.make_response(costly_route())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['code'], 'USAGE_ACCOUNTING_UNAVAILABLE')
        route_called.assert_not_called()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.refund_reservation')
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    def test_success_never_calls_post_work_accounting(
        self, mock_reserve, mock_refund, mock_enabled
    ):
        """비용 성공 뒤 추가 정산 RPC가 없어 성공 응답이 503으로 바뀌지 않음."""
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage
        from services.usage.usage_service import UsageAccountingUnavailable

        app = Flask(__name__)
        app.config['REDIS_URL'] = ''
        mock_reserve.return_value = _make_reservation()
        mock_refund.side_effect = UsageAccountingUnavailable('must not be called')

        @require_usage
        def costly_route():
            return {'success': True}, 200

        with app.test_request_context():
            g.user_id = 'success-user'
            response = app.make_response(costly_route())

        self.assertEqual(response.status_code, 200)
        mock_refund.assert_not_called()

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_decorator.UsageService.refund_reservation_quietly')
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch('services.usage.usage_decorator.acquire_usage_request_lock')
    def test_lost_lease_after_reservation_refunds_before_work(
        self, mock_acquire, mock_reserve, mock_refund, mock_enabled
    ):
        from flask import Flask, g
        from services.usage.usage_decorator import require_usage

        app = Flask(__name__)
        lease = MagicMock()
        lease.lost = False
        lease.lost_reason = RuntimeError('renewal lost')
        mock_acquire.return_value = lease
        reservation = _make_reservation()

        def reserve_then_lose(_user_id):
            lease.lost = True
            return reservation

        mock_reserve.side_effect = reserve_then_lose
        mock_refund.return_value = reservation.usage_before
        route_called = MagicMock()

        @require_usage
        def costly_route():
            route_called()
            return {'success': True}, 200

        with app.test_request_context():
            g.user_id = 'lease-lost-user'
            response = app.make_response(costly_route())

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mock_refund.assert_called_once_with('lease-lost-user', reservation)
        route_called.assert_not_called()
        lease.release.assert_called_once_with()


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

    @patch('services.usage.usage_service.mark_usage_accounting_unavailable')
    @patch('services.usage.usage_service.is_supabase_enabled', return_value=True)
    @patch('services.usage.usage_service.is_admin', return_value=False)
    @patch(
        'src.contexts.identity.infrastructure.supabase_usage_gateway.SupabaseUsageGateway.check_and_consume',
        side_effect=RuntimeError('rpc unavailable'),
    )
    def test_decrement_infrastructure_failure_is_fail_closed(
        self, _mock_consume, _mock_admin, _mock_enabled, mock_mark,
    ):
        from services.usage.usage_service import (
            UsageAccountingUnavailable,
            UsageService,
        )

        with self.assertRaises(UsageAccountingUnavailable):
            UsageService.decrement('user-1')

        mock_mark.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
