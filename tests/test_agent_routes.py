"""에이전트 채팅 라우트의 인증·요청 제한·사용량 정책 회귀 테스트."""
from types import SimpleNamespace
import threading
import unittest
from unittest.mock import MagicMock, patch

from flask import g

from app import create_app
from services.usage.usage_service import UsageReservationReplay
from src.contexts.identity.domain.exceptions import QuotaExceeded


class TestAgentRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['REDIS_URL'] = ''
        self.client = self.app.test_client()

    @staticmethod
    def _authenticate(_token):
        g.user_id = 'agent-user'
        g.access_token = 'valid-token'
        return {'valid': True, 'error': None, 'code': None}

    @staticmethod
    def _reservation():
        usage_after = {
            'can_use': True,
            'usage_count': 2,
            'max_usage': 3,
            'is_admin': False,
        }
        return SimpleNamespace(
            quota=SimpleNamespace(owned=True),
            usage_before={**usage_after, 'usage_count': 3},
            usage_after=usage_after,
            billable=True,
            owned=True,
        )

    @staticmethod
    def _response():
        return SimpleNamespace(
            content='완료',
            session_id='session-1',
            tool_calls_count=1,
            iterations_used=1,
            elapsed_seconds=0.1,
            metadata={},
        )

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_chat_requires_auth_when_supabase_enabled(self, _):
        resp = self.client.post(
            '/api/agent/chat',
            json={'message': '안녕'},
            environ_overrides={'REMOTE_ADDR': '198.51.100.51'},
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')

    @patch(
        'services.usage.usage_decorator.UsageService.reserve_for_request',
        side_effect=QuotaExceeded,
    )
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_chat_rejects_exhausted_usage(self, _, __, mock_reserve):
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent') as mock_agent:
            resp = self.client.post(
                '/api/agent/chat',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.52'},
            )

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mock_reserve.assert_called_once_with('agent-user')
        mock_agent.assert_not_called()

    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=False,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_chat_keeps_local_mode_available(self, _, __):
        fake_agent = SimpleNamespace(run=lambda **_kwargs: self._response())
        with patch('agent.AIAgent', return_value=fake_agent):
            resp = self.client.post(
                '/api/agent/chat',
                json={'message': '안녕'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.53'},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['content'], '완료')

    @patch('routes.agent_routes.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_chat_and_stream_reject_unlisted_model_before_agent(self, _, __, ___):
        with patch('agent.AIAgent') as mock_agent:
            for index, path in enumerate(('/api/agent/chat', '/api/agent/chat/stream')):
                with self.subTest(path=path):
                    resp = self.client.post(
                        path,
                        json={'message': '안녕', 'model': 'attacker/model'},
                        environ_overrides={'REMOTE_ADDR': f'198.51.100.{80 + index}'},
                    )
                    self.assertEqual(resp.status_code, 400)
                    self.assertEqual(resp.get_json()['code'], 'UNSUPPORTED_MODEL')
        mock_agent.assert_not_called()

    @patch(
        'routes.agent_routes.UsageService.refund_reservation_quietly',
    )
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch(
        'routes.agent_routes.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_decrements_only_after_success(
        self, _, __, mock_reserve, mock_refund,
    ):
        mock_reserve.return_value = self._reservation()
        fake_agent = SimpleNamespace(run=lambda **_kwargs: self._response())
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent', return_value=fake_agent):
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.54'},
            )
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('"type": "done"', body)
        mock_reserve.assert_called_once_with('agent-user')
        mock_refund.assert_not_called()

    @patch(
        'routes.agent_routes.UsageService.refund_reservation_quietly',
    )
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch(
        'routes.agent_routes.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_redacts_internal_error_and_does_not_decrement(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation
        def fail(**_kwargs):
            raise RuntimeError('postgresql://admin:secret@internal/token=private')

        fake_agent = SimpleNamespace(run=fail)
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent', return_value=fake_agent):
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.55'},
            )
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('에이전트 처리 중 문제가 발생했습니다.', body)
        self.assertNotIn('secret', body)
        self.assertNotIn('private', body)
        mock_refund.assert_called_once_with('agent-user', reservation)

    @patch(
        'routes.agent_routes.is_supabase_enabled',
        return_value=False,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_stream_redacts_secret_bearing_tool_exception_preview(self, _, __):
        raw_secret = 'sk-secret-from-tool-exception'

        class ToolFailureAgent:
            def __init__(self, **kwargs):
                self._on_tool_end = kwargs['on_tool_end']

            def run(self, **_kwargs):
                self._on_tool_end(
                    'exploder',
                    (
                        '{"error": "도구 실행 실패: Authorization Bearer '
                        f'{raw_secret} postgresql://admin:pw@internal/db'
                    ),
                    0.1,
                )
                return TestAgentRoutes._response()

        with patch('agent.AIAgent', ToolFailureAgent):
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '도구 예외를 발생시켜'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.59'},
            )
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('도구 실행 중 문제가 발생했습니다.', body)
        self.assertNotIn(raw_secret, body)
        self.assertNotIn('postgresql://', body)

    @patch(
        'routes.agent_routes.UsageService.reserve_for_request',
        side_effect=QuotaExceeded,
    )
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_rejects_exhausted_usage_before_agent_runs(
        self, _, __, mock_reserve,
    ):
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent') as mock_agent:
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.56'},
            )

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mock_reserve.assert_called_once_with('agent-user')
        mock_agent.assert_not_called()

    @patch(
        'routes.agent_routes.UsageService.reserve_for_request',
        side_effect=UsageReservationReplay({'usage_count': 2}),
    )
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_replay_is_rejected_before_agent_runs(
        self, _, __, mock_reserve,
    ):
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent') as mock_agent:
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={
                    'Authorization': 'Bearer valid-token',
                    'Idempotency-Key': 'same-operation',
                },
                environ_overrides={'REMOTE_ADDR': '198.51.100.60'},
            )

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()['code'], 'IDEMPOTENCY_REPLAY')
        mock_reserve.assert_called_once_with('agent-user')
        mock_agent.assert_not_called()

    @patch('routes.agent_routes.UsageService.refund_reservation_quietly')
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_lost_lease_before_ai_refunds_and_never_runs_agent(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation

        class LeaseLostAtWorkerBoundary:
            released = False
            lost_reason = RuntimeError('renewal failed')

            def __init__(self):
                self.checks = 0

            @property
            def lost(self):
                self.checks += 1
                return self.checks >= 3

            def release(self):
                self.released = True

        lease = LeaseLostAtWorkerBoundary()
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch(
            'routes.agent_routes.acquire_usage_request_lock',
            return_value=lease,
        ), patch('agent.AIAgent') as mock_agent:
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.61'},
            )
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('에이전트 처리 중 문제가 발생했습니다.', body)
        mock_agent.assert_not_called()
        mock_refund.assert_called_once_with('agent-user', reservation)

    @patch('routes.agent_routes.UsageService.refund_reservation_quietly')
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_thread_start_failure_refunds_and_releases_lease(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation
        lease = MagicMock(lost=False, released=False)

        def release_lease():
            lease.released = True

        lease.release.side_effect = release_lease

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch(
            'routes.agent_routes.acquire_usage_request_lock',
            return_value=lease,
        ), patch(
            'routes.agent_routes._start_agent_thread',
            side_effect=RuntimeError('thread unavailable'),
        ), patch('agent.AIAgent') as mock_agent:
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.63'},
            )

        self.assertEqual(resp.status_code, 500)
        mock_agent.assert_not_called()
        mock_refund.assert_called_once_with('agent-user', reservation)
        lease.release.assert_called_once_with()

    @patch(
        'routes.agent_routes.UsageService.refund_reservation_quietly',
    )
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_concurrent_stream_for_same_user_is_rejected(
        self, _, __, mock_reserve, mock_refund,
    ):
        mock_reserve.return_value = self._reservation()
        entered = threading.Event()
        finish = threading.Event()
        first_result = {}

        def slow_run(**_kwargs):
            entered.set()
            finish.wait(timeout=2)
            return self._response()

        fake_agent = SimpleNamespace(run=slow_run)

        def first_request():
            client = self.app.test_client()
            resp = client.post(
                '/api/agent/chat/stream',
                json={'message': '첫 요청'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.57'},
            )
            first_result['status'] = resp.status_code
            first_result['body'] = resp.get_data(as_text=True)

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent', return_value=fake_agent):
            worker = threading.Thread(target=first_request)
            worker.start()
            self.assertTrue(entered.wait(timeout=1))
            try:
                second = self.client.post(
                    '/api/agent/chat/stream',
                    json={'message': '두 번째 요청'},
                    headers={'Authorization': 'Bearer valid-token'},
                    environ_overrides={'REMOTE_ADDR': '198.51.100.58'},
                )
            finally:
                finish.set()
                worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()['code'], 'USAGE_REQUEST_IN_PROGRESS')
        self.assertEqual(first_result['status'], 200)
        self.assertIn('"type": "done"', first_result['body'])
        mock_reserve.assert_called_once_with('agent-user')
        mock_refund.assert_not_called()

    @patch(
        'services.usage.usage_decorator.UsageService.refund_reservation_quietly',
    )
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_sync_provider_failure_after_cost_start_keeps_reservation(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation
        raw_secret = 'Authorization: Bearer sk-provider-secret'

        class CostStartingAgent:
            def __init__(self, **kwargs):
                self._on_cost_start = kwargs['on_cost_start']

            def run(self, **_kwargs):
                self._on_cost_start()
                raise RuntimeError(raw_secret)

        with self.assertLogs('routes.agent_routes', level='ERROR') as logs:
            with patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=self._authenticate,
            ), patch('agent.AIAgent', CostStartingAgent):
                resp = self.client.post(
                    '/api/agent/chat',
                    json={'message': '안녕'},
                    headers={'Authorization': 'Bearer valid-token'},
                    environ_overrides={'REMOTE_ADDR': '198.51.100.62'},
                )

        self.assertEqual(resp.status_code, 500)
        self.assertNotIn(raw_secret, '\n'.join(logs.output))
        self.assertIn('RuntimeError', '\n'.join(logs.output))
        mock_refund.assert_not_called()

    @patch(
        'services.usage.usage_decorator.UsageService.refund_reservation_quietly',
    )
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_sync_cost_boundary_lock_loss_returns_503_and_refunds(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation

        class LeaseLostAtCostBoundary:
            released = False
            lost_reason = RuntimeError('renewal failed')

            def __init__(self):
                self.checks = 0

            @property
            def lost(self):
                self.checks += 1
                return self.checks >= 3

            def release(self):
                self.released = True

        class CostStartingAgent:
            def __init__(self, **kwargs):
                self._on_cost_start = kwargs['on_cost_start']

            def run(self, **_kwargs):
                self._on_cost_start()
                raise AssertionError('비용 경계 뒤로 진행하면 안 됩니다.')

        lease = LeaseLostAtCostBoundary()
        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch(
            'services.usage.usage_decorator.acquire_usage_request_lock',
            return_value=lease,
        ), patch('agent.AIAgent', CostStartingAgent):
            resp = self.client.post(
                '/api/agent/chat',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.64'},
            )

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mock_refund.assert_called_once_with('agent-user', reservation)

    @patch(
        'services.usage.usage_decorator.UsageService.refund_reservation_quietly',
    )
    @patch('services.usage.usage_decorator.UsageService.reserve_for_request')
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_sync_worker_provider_uses_captured_lease_callback(
        self, _, __, mock_reserve, mock_refund,
    ):
        reservation = self._reservation()
        mock_reserve.return_value = reservation
        lease = MagicMock(lost=False, released=False)

        class WorkerCostAgent:
            def __init__(self, **kwargs):
                self._on_cost_start = kwargs['on_cost_start']

            def run(self, **_kwargs):
                errors = []
                lease.lost = True
                lease.lost_reason = RuntimeError('renewal failed')

                def invoke_provider_boundary():
                    try:
                        self._on_cost_start()
                    except Exception as exc:
                        errors.append(exc)

                worker = threading.Thread(target=invoke_provider_boundary)
                worker.start()
                worker.join(timeout=1)
                if errors:
                    raise errors[0]
                return TestAgentRoutes._response()

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch(
            'services.usage.usage_decorator.acquire_usage_request_lock',
            return_value=lease,
        ), patch('agent.AIAgent', WorkerCostAgent):
            resp = self.client.post(
                '/api/agent/chat',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.65'},
            )

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mock_refund.assert_called_once_with('agent-user', reservation)

    @patch(
        'routes.agent_routes.UsageService.refund_reservation_quietly',
    )
    @patch('routes.agent_routes.UsageService.reserve_for_request')
    @patch('routes.agent_routes.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_stream_provider_failure_after_cost_start_keeps_reservation(
        self, _, __, mock_reserve, mock_refund,
    ):
        mock_reserve.return_value = self._reservation()

        class CostStartingAgent:
            def __init__(self, **kwargs):
                self._on_cost_start = kwargs['on_cost_start']

            def run(self, **_kwargs):
                self._on_cost_start()
                raise RuntimeError('provider response lost')

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=self._authenticate,
        ), patch('agent.AIAgent', CostStartingAgent):
            resp = self.client.post(
                '/api/agent/chat/stream',
                json={'message': '안녕'},
                headers={'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.63'},
            )
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('에이전트 처리 중 문제가 발생했습니다.', body)
        mock_refund.assert_not_called()

    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=False,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_chat_is_rate_limited(self, _, __):
        from extensions import limiter

        previous_enabled = limiter.enabled
        self.app.config['RATELIMIT_ENABLED'] = True
        limiter.enabled = True
        limiter.init_app(self.app)
        limiter.reset()
        self.addCleanup(setattr, limiter, 'enabled', previous_enabled)
        self.addCleanup(limiter.reset)

        fake_agent = SimpleNamespace(run=lambda **_kwargs: self._response())
        with patch('agent.AIAgent', return_value=fake_agent):
            responses = [
                self.client.post(
                    '/api/agent/chat',
                    json={'message': '안녕'},
                    environ_overrides={'REMOTE_ADDR': '198.51.100.99'},
                )
                for _ in range(6)
            ]

        self.assertTrue(all(resp.status_code == 200 for resp in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)


if __name__ == '__main__':
    unittest.main()
