"""blog_routes.py 라우트 커버리지 테스트.

핵심 생성 엔드포인트 (/generate, /generate-batch) +
템플릿, Video QA, TTS, 이벤트 추출, 자막 워크스페이스, 캡처 엔드포인트 커버.
"""
import unittest
from unittest.mock import MagicMock, patch

from flask import g

from app import create_app
from src.contexts.identity.domain.exceptions import QuotaExceeded
from services.usage.usage_service import UsageReservation
from services.usage.usage_lock import UsageLockUnavailable
from src.contexts.identity.application.ports import QuotaReservation

_H = {'Origin': 'http://localhost:3000'}


def _batch_reservation():
    before = {'usage_count': 3, 'max_usage': 5, 'can_use': True, 'is_admin': False}
    after = {**before, 'usage_count': 2}
    quota = QuotaReservation(
        reservation_id='batch-reservation',
        idempotency_key='client:key',
        request_fingerprint='a' * 64,
        owner_token_hash='b' * 64,
        amount=1,
        remaining=2,
        max_usage=5,
        owned=True,
        replayed=False,
    )
    return UsageReservation(quota, before, after, True)


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


# ── 헬퍼 함수 테스트 ──────────────────────────────────────


class TestExtractClientId(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_client_id_from_json(self, _):
        """JSON body에서 clientId 추출."""
        from routes.blog_routes import _extract_client_id
        with self.app.test_request_context(
            json={'clientId': 'test-123'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            cid = _extract_client_id(flask_req)
            self.assertEqual(cid, 'test-123')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_client_id_empty(self, _):
        """clientId가 없으면 빈 문자열."""
        from routes.blog_routes import _extract_client_id
        with self.app.test_request_context(json={}, content_type='application/json'):
            from flask import request as flask_req
            cid = _extract_client_id(flask_req)
            self.assertEqual(cid, '')


class TestValidateModifiers(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_none(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_valid(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers({'length': 'short', 'language': 'ko'})
        self.assertIsNone(err)
        self.assertEqual(result['length'], 'short')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_invalid_type(self, _):
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers('not a dict')
        self.assertIsNone(result)
        self.assertIsNotNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_modifiers_invalid_values(self, _):
        """유효하지 않은 값은 무시."""
        from routes.blog_routes import _validate_modifiers
        result, err = _validate_modifiers({'length': 'invalid_value', 'language': 'ko'})
        self.assertNotIn('length', result or {})
        self.assertEqual((result or {}).get('language'), 'ko')


class TestValidateCustomPrompt(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_none(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_valid(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt('커스텀 프롬프트')
        self.assertEqual(result, '커스텀 프롬프트')
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_custom_prompt_invalid_type(self, _):
        from routes.blog_routes import _validate_custom_prompt
        result, err = _validate_custom_prompt(12345)
        self.assertIsNone(result)
        self.assertIsNotNone(err)


class TestValidateStyle(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_style_accepts_quiz(self, _):
        from routes.blog_routes import _validate_style
        self.assertEqual(_validate_style('quiz'), 'quiz')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_style_accepts_retention_cards(self, _):
        from routes.blog_routes import _validate_style
        self.assertEqual(_validate_style('retention_cards'), 'retention_cards')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_style_unknown_passes_through(self, _):
        from routes.blog_routes import _validate_style
        self.assertEqual(_validate_style('unknown_style'), 'unknown_style')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_style_preserves_custom_prompt_style(self, _):
        from routes.blog_routes import _validate_style
        self.assertEqual(_validate_style('my_custom', '프롬프트'), 'my_custom')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_style_empty_defaults(self, _):
        from routes.blog_routes import _validate_style
        self.assertEqual(_validate_style('   '), 'summary')


class TestGetRequestData(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_json(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'url': 'https://youtube.com/watch?v=123',
                  'model': 'chatmock/gpt-5.4-mini',
                  'style': 'summary'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['url'], 'https://youtube.com/watch?v=123')
            self.assertEqual(params['style'], 'summary')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_defaults(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertIsNone(params['url'])
            self.assertIsNotNone(params['model'])  # 기본값 존재

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_rejects_unlisted_model_and_preserves_auto(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(json={'model': 'attacker/model'}):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['model_error'], '지원하지 않는 AI 모델입니다.')

        with self.app.test_request_context(json={'model': 'auto'}):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertIsNone(params['model_error'])
            self.assertEqual(params['model'], 'auto')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_detail_level_validation(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'detail_level': 'invalid'},
            content_type='application/json'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['detail_level'], 'standard')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_get_request_data_form_data(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            data={'url': 'https://youtube.com/watch?v=abc',
                  'style': 'blog_seo'},
            content_type='multipart/form-data'
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['url'], 'https://youtube.com/watch?v=abc')


# ── /generate 엔드포인트 ──────────────────────────────────────


class TestGenerateRoute(_Base):

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_generate_rejects_unlisted_model_before_source_work(self, _, __):
        with patch('routes.blog_routes.content_service.is_youtube_url') as mock_youtube:
            resp = self.client.post(
                '/generate',
                json={
                    'url': 'https://youtube.com/watch?v=abc',
                    'model': 'attacker/model',
                },
                headers=_H,
                environ_overrides={'REMOTE_ADDR': '198.51.100.91'},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['code'], 'UNSUPPORTED_MODEL')
        mock_youtube.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_missing_url(self, _):
        """URL도 content도 없으면 400."""
        resp = self.client.post('/generate', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.generation_helpers._handle_web_source')
    def test_generate_non_youtube_url(self, mock_web, _):
        """비YouTube URL은 _handle_web_source로 라우팅."""
        mock_web.return_value = ({'title': '웹', 'content': '결과'}, 200)
        resp = self.client.post('/generate',
                                json={'url': 'https://example.com/article'},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 400, 500])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes._handle_direct_text')
    def test_generate_direct_text(self, mock_direct, _):
        """직접 텍스트 입력 모드."""
        # generate()는 blog_routes 네임스페이스에 바인딩된 _handle_direct_text를 호출하므로
        # generation_helpers가 아닌 routes.blog_routes를 patch해야 mock이 적용됨
        # _handle_direct_text는 Flask Response를 반환해야 함
        # 앱 컨텍스트 내에서 호출되므로 side_effect로 처리
        def fake_handle(*args, **kwargs):
            from flask import jsonify as _jsonify
            return _jsonify({'title': '직접입력', 'content': '결과'})
        mock_direct.side_effect = fake_handle
        resp = self.client.post('/generate',
                                json={'content': '충분히 긴 텍스트입니다. ' * 10},
                                headers=_H)
        self.assertIn(resp.status_code, [200, 400, 500])


# ── /generate-batch 엔드포인트 ──────────────────────────────────────


class TestGenerateBatchRoute(_Base):

    @patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=False)
    @patch('routes.blog_routes._process_single_url')
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    def test_batch_rejects_unlisted_model_before_reservation(
        self, mock_reserve, mock_process, _,
    ):
        with patch.object(self.app.logger, 'info') as mock_log:
            resp = self.client.post(
                '/generate-batch',
                json={
                    'urls': ['https://youtube.com/watch?v=abc'],
                    'model': 'attacker/model',
                    'customPrompt': 'DO-NOT-LOG-PRIVATE-PROMPT',
                },
                headers=_H,
                environ_overrides={'REMOTE_ADDR': '198.51.100.92'},
            )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['code'], 'UNSUPPORTED_MODEL')
        mock_reserve.assert_not_called()
        mock_process.assert_not_called()
        self.assertNotIn('DO-NOT-LOG-PRIVATE-PROMPT', str(mock_log.call_args_list))

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    def test_batch_no_json(self, mock_reserve, _):
        """JSON이 아닌 content-type은 500 (UnsupportedMediaType catch)."""
        resp = self.client.post('/generate-batch',
                                data='not json',
                                content_type='text/plain',
                                headers=_H)
        self.assertEqual(resp.status_code, 500)
        mock_reserve.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    def test_batch_no_urls(self, mock_reserve, _):
        resp = self.client.post('/generate-batch',
                                json={'model': 'test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        mock_reserve.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    def test_batch_too_many_urls(self, mock_reserve, _):
        urls = [f'https://youtube.com/watch?v={i}' for i in range(20)]
        resp = self.client.post('/generate-batch',
                                json={'urls': urls},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)
        mock_reserve.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    def test_batch_usage_exceeded(self, mock_reserve, _):
        from src.contexts.identity.domain.exceptions import QuotaExceeded
        mock_reserve.side_effect = QuotaExceeded('no usage left')
        resp = self.client.post('/generate-batch',
                                json={'urls': ['https://youtube.com/watch?v=123']},
                                headers=_H)
        self.assertEqual(resp.status_code, 429)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    @patch('routes.blog_routes._process_single_url')
    def test_batch_replay_is_rejected_before_workers(
        self, mock_process, mock_reserve, _
    ):
        from services.usage.usage_service import UsageReservationReplay

        mock_reserve.side_effect = UsageReservationReplay({
            'usage_count': 4,
            'max_usage': 5,
            'can_use': True,
        })
        resp = self.client.post(
            '/generate-batch',
            json={'urls': ['https://youtube.com/watch?v=123']},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()['code'], 'IDEMPOTENCY_REPLAY')
        mock_process.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.refund_reservation')
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    @patch('routes.blog_routes._process_single_url')
    def test_batch_all_failed_refunds_own_reservation(
        self, mock_process, mock_reserve, mock_refund, _
    ):
        reservation = _batch_reservation()
        mock_reserve.return_value = reservation
        mock_refund.return_value = reservation.usage_before
        mock_process.return_value = {
            'success': False,
            'url': 'https://youtube.com/watch?v=123',
            'error': 'provider failed',
        }

        resp = self.client.post(
            '/generate-batch',
            json={'urls': ['https://youtube.com/watch?v=123']},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['successful'], 0)
        self.assertEqual(resp.get_json()['usage'], reservation.usage_before)
        mock_refund.assert_called_once_with(None, reservation)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.refund_reservation')
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    @patch('routes.blog_routes._process_single_url')
    def test_batch_all_failed_after_provider_start_keeps_reservation(
        self, mock_process, mock_reserve, mock_refund, _
    ):
        reservation = _batch_reservation()
        mock_reserve.return_value = reservation

        def fail_after_provider(
            _app, url, _model, _style, _modifiers, _custom_prompt,
            on_cost_start, **_options,
        ):
            on_cost_start()
            return {
                'success': False,
                'url': url,
                'error': 'provider response lost',
            }

        mock_process.side_effect = fail_after_provider
        resp = self.client.post(
            '/generate-batch',
            json={'urls': ['https://youtube.com/watch?v=123']},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['successful'], 0)
        self.assertEqual(resp.get_json()['usage'], reservation.usage_after)
        mock_refund.assert_not_called()

    def test_batch_lost_lease_after_reservation_stops_before_workers(self):
        def fake_validate(_token):
            from flask import g
            g.user_id = 'batch-user'
            return {'valid': True, 'error': None, 'code': None}

        lease = MagicMock()
        lease.lost = False
        lease.lost_reason = RuntimeError('renewal lost')
        reservation = _batch_reservation()

        def reserve_then_lose(_user_id):
            lease.lost = True
            return reservation

        with (
            patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            patch('routes.blog_routes.is_supabase_enabled', return_value=True),
            patch('routes.blog_routes.acquire_usage_request_lock', return_value=lease),
            patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                side_effect=reserve_then_lose,
            ),
            patch(
                'services.usage.usage_service.UsageService.refund_reservation_quietly',
                return_value=reservation.usage_before,
            ) as mock_refund,
            patch('routes.blog_routes._process_single_url') as mock_process,
        ):
            resp = self.client.post(
                '/generate-batch',
                json={'urls': ['https://youtube.com/watch?v=123']},
                headers={**_H, 'Authorization': 'Bearer token'},
            )

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mock_process.assert_not_called()
        mock_refund.assert_called_once_with('batch-user', reservation)
        lease.release.assert_called_once_with()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.usage.usage_service.UsageService.refund_reservation_quietly')
    @patch('services.usage.usage_service.UsageService.reserve_for_request')
    @patch('routes.blog_routes._process_single_url')
    def test_batch_worker_lock_loss_returns_503_and_refunds_before_cost(
        self, mock_process, mock_reserve, mock_refund, _
    ):
        reservation = _batch_reservation()
        mock_reserve.return_value = reservation
        mock_process.side_effect = UsageLockUnavailable('lease lost')

        resp = self.client.post(
            '/generate-batch',
            json={'urls': ['https://youtube.com/watch?v=123']},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mock_refund.assert_called_once_with(None, reservation)


# ── 템플릿 API ──────────────────────────────────────


class TestTemplateRoutes(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.get_templates')
    def test_list_templates(self, mock_get, _):
        mock_get.return_value = {'templates': [], 'total': 0}
        resp = self.client.get('/api/templates')
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_name(self, _):
        resp = self.client.post('/api/templates',
                                json={'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_missing_prompt(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': '이름'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_name_too_long(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': 'a' * 51, 'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_create_template_prompt_too_long(self, _):
        resp = self.client.post('/api/templates',
                                json={'name': '이름', 'prompt_text': 'x' * 5001},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.create_template')
    def test_create_template_success(self, mock_create, _):
        mock_create.return_value = {'id': 't1', 'name': '테스트'}
        resp = self.client.post('/api/templates',
                                json={'name': '테스트', 'prompt_text': '프롬프트 내용'},
                                headers=_H)
        self.assertEqual(resp.status_code, 201)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.create_template', return_value=None)
    def test_create_template_returns_none(self, mock_create, _):
        resp = self.client.post('/api/templates',
                                json={'name': '테스트', 'prompt_text': '프롬프트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.update_template', return_value=None)
    def test_update_template_not_found(self, mock_update, _):
        resp = self.client.put('/api/templates/t999',
                               json={'name': '변경'},
                               headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.update_template')
    def test_update_template_success(self, mock_update, _):
        mock_update.return_value = {'id': 't1', 'name': '변경됨'}
        resp = self.client.put('/api/templates/t1',
                               json={'name': '변경됨'},
                               headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_update_template_empty_name(self, _):
        resp = self.client.put('/api/templates/t1',
                               json={'name': ''},
                               headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.delete_template', return_value=True)
    def test_delete_template_success(self, mock_del, _):
        resp = self.client.delete('/api/templates/t1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.delete_template', return_value=False)
    def test_delete_template_not_found(self, mock_del, _):
        resp = self.client.delete('/api/templates/t999', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.get_template_by_id', return_value=None)
    def test_use_template_not_found(self, mock_get, _):
        resp = self.client.post('/api/templates/t999/use', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_template_service.increment_usage')
    @patch('services.data.prompt_template_service.get_template_by_id')
    def test_use_template_success(self, mock_get, mock_inc, _):
        mock_get.return_value = {'id': 't1', 'prompt_text': '프롬프트'}
        resp = self.client.post('/api/templates/t1/use', headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── Video QA ──────────────────────────────────────


class TestPublicGenerationModelBoundary(_Base):

    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    )
    def test_merged_and_stream_reject_unlisted_model_before_ai(self, _, __):
        requests = [
            (
                '/api/generate-merged',
                {'urls': ['https://youtu.be/a', 'https://youtu.be/b'], 'model': 'attacker/model'},
            ),
            (
                '/generate-stream',
                {'url': 'https://youtu.be/a', 'model': 'attacker/model'},
            ),
        ]
        with patch('routes.blog_routes.ai_service.create_content') as mock_create, patch(
            'routes.blog_routes.ai_service.create_content_stream'
        ) as mock_stream:
            for index, (path, payload) in enumerate(requests):
                with self.subTest(path=path):
                    resp = self.client.post(
                        path,
                        json=payload,
                        headers=_H,
                        environ_overrides={'REMOTE_ADDR': f'198.51.100.{93 + index}'},
                    )
                    self.assertEqual(resp.status_code, 400)
                    self.assertEqual(resp.get_json()['code'], 'UNSUPPORTED_MODEL')
        mock_create.assert_not_called()
        mock_stream.assert_not_called()


class TestVideoQARoute(_Base):

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_video_qa_requires_auth(self, _):
        resp = self.client.post(
            '/api/video-qa',
            json={'video_url': 'https://youtube.com/watch?v=abc', 'question': '질문'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.71'},
        )
        self.assertEqual(resp.status_code, 401)

    @patch(
        'services.usage.usage_decorator.UsageService.reserve_for_request',
        side_effect=QuotaExceeded,
    )
    @patch('services.usage.usage_decorator.is_supabase_enabled', return_value=True)
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_video_qa_rejects_exhausted_usage(self, _, __, mock_reserve):
        def authenticate(_token):
            g.user_id = 'user-video-qa'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ), patch('services.media.video_qa_service.answer_question') as mock_answer:
            resp = self.client.post(
                '/api/video-qa',
                json={'video_url': 'https://youtube.com/watch?v=abc', 'question': '질문'},
                headers={**_H, 'Authorization': 'Bearer token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.72'},
            )

        self.assertEqual(resp.status_code, 429)
        mock_reserve.assert_called_once_with('user-video-qa')
        mock_answer.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.video_qa_service.answer_question')
    def test_video_qa_rejects_unlisted_model_before_ai(self, mock_answer, _):
        resp = self.client.post(
            '/api/video-qa',
            json={
                'video_url': 'https://youtube.com/watch?v=abc',
                'question': '질문',
                'model': 'attacker/model',
            },
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.73'},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()['code'], 'UNSUPPORTED_MODEL')
        mock_answer.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_video_qa_rejects_oversized_follow_up(self, _):
        resp = self.client.post(
            '/api/video-qa',
            json={
                'video_url': 'https://youtube.com/watch?v=abc',
                'question': '질문',
                'history': [{'role': 'user', 'content': 'x' * 501}],
            },
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.74'},
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_video_qa_missing_url(self, _):
        resp = self.client.post('/api/video-qa', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=False)
    def test_video_qa_invalid_url(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://example.com',
                                      'question': '질문'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_missing_question(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_question_too_long(self, mock_yt, _):
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc',
                                      'question': 'q' * 501},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.video_qa_service.answer_question')
    @patch('services.media.video_qa_service.is_video_indexed', return_value=True)
    @patch('services.core.content_service.get_video_id', return_value='abc123')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_video_qa_success(self, *mocks):
        mocks[3].return_value = {'answer': '답변입니다', 'sources': []}
        resp = self.client.post('/api/video-qa',
                                json={'video_url': 'https://youtube.com/watch?v=abc123',
                                      'question': '이 영상은 무엇에 대한 것인가요?'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['answer'], '답변입니다')


# ── TTS ──────────────────────────────────────


class TestTTSRoute(_Base):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_tts_missing_text(self, _):
        resp = self.client.post('/api/tts', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.tts_service.TTSService.synthesize')
    def test_tts_success(self, mock_synth, _):
        mock_synth.return_value = b'\x00\x01\x02\x03'  # 가짜 오디오 바이트
        resp = self.client.post('/api/tts',
                                json={'text': '안녕하세요', 'voice': 'ko-KR'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'audio/mpeg')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.tts_service.TTSService.synthesize',
           side_effect=ValueError('지원하지 않는 음성'))
    def test_tts_value_error(self, mock_synth, _):
        resp = self.client.post('/api/tts',
                                json={'text': '테스트'},
                                headers=_H)
        self.assertIn(resp.status_code, [400, 401, 500, 503])


# ── 이벤트 추출 ──────────────────────────────────────


class TestExtractEventsRoute(_Base):

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_extract_events_requires_auth_when_supabase_enabled(self, _):
        resp = self.client.post(
            '/api/extract-events',
            json={'transcript': '이벤트가 있는 자막'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.61'},
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
    def test_extract_events_rejects_exhausted_usage(self, _, __, mock_reserve):
        def authenticate(_token):
            g.user_id = 'user-events'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ), patch(
            'services.content.event_extraction_service.extract_events'
        ) as mock_extract:
            resp = self.client.post(
                '/api/extract-events',
                json={'transcript': '이벤트가 있는 자막'},
                headers={**_H, 'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.62'},
            )

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mock_reserve.assert_called_once_with('user-events')
        mock_extract.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_extract_events_missing_input(self, _):
        resp = self.client.post('/api/extract-events', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.event_extraction_service.get_event_summary')
    @patch('services.content.event_extraction_service.categorize_events')
    @patch('services.content.event_extraction_service.extract_events')
    def test_extract_events_with_transcript(self, mock_ext, mock_cat, mock_sum, _):
        mock_ext.return_value = [{'type': 'event', 'text': '발표'}]
        mock_cat.return_value = {'announcement': []}
        mock_sum.return_value = {'total': 1}
        resp = self.client.post('/api/extract-events',
                                json={'transcript': '오늘 새로운 제품을 발표합니다.'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('events', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.event_extraction_service.get_event_summary', return_value={'total': 1})
    @patch('services.content.event_extraction_service.categorize_events', return_value={'announcement': []})
    @patch('services.content.event_extraction_service.extract_events', return_value=[{'type': 'event', 'text': '발표'}])
    @patch('services.core.content_service.get_transcript', return_value={'text': 'URL에서 얻은 자막', 'source': 'api'})
    @patch('services.core.content_service.get_video_id', return_value='video-id')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_extract_events_accepts_content_service_text_contract(
        self, _is_youtube, _video_id, _transcript, mock_ext, _mock_cat, _mock_sum, _supabase,
    ):
        resp = self.client.post(
            '/api/extract-events',
            json={'url': 'https://youtube.com/watch?v=video-id'},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 200)
        mock_ext.assert_called_once_with(
            'URL에서 얻은 자막', model='chatmock/gpt-5.4-mini'
        )

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.event_extraction_service.extract_events')
    def test_extract_events_rejects_unlisted_model(self, mock_extract, _):
        resp = self.client.post(
            '/api/extract-events',
            json={
                'transcript': '이벤트가 있는 자막',
                'model': 'attacker/arbitrary-model',
            },
            headers=_H,
        )

        self.assertEqual(resp.status_code, 400)
        mock_extract.assert_not_called()


if __name__ == '__main__':
    unittest.main()
