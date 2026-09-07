"""요청 스코프 Supabase JWT/RLS 클라이언트 보안 회귀 테스트."""
from types import SimpleNamespace
from unittest.mock import MagicMock, call, patch

import pytest
from flask import Flask, g, jsonify

from services.exceptions import ConfigurationError


class _ImmediateThread:
    """테스트에서 백그라운드 target을 즉시 실행하는 최소 Thread 대역."""

    def __init__(self, target, args=(), kwargs=None, daemon=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self.daemon = daemon

    def start(self):
        self._target(*self._args, **self._kwargs)


def test_validated_requests_get_fresh_token_isolated_clients(monkeypatch):
    """서로 다른 두 요청의 JWT가 전역 클라이언트나 상대 요청으로 새지 않는다."""
    from src.contexts.identity.interface.auth_decorators import require_auth
    import src.shared.infrastructure.supabase_client as client_module

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')

    verification_client = MagicMock()
    verification_client.auth.get_user.side_effect = lambda token: SimpleNamespace(
        user=SimpleNamespace(id=f'user-{token}', email=None),
    )
    first_client = SimpleNamespace(marker='first-client')
    second_client = SimpleNamespace(marker='second-client')

    app = Flask(__name__)
    app.config['FLASK_ENV'] = 'production'

    @app.get('/rls-client')
    @require_auth
    def rls_client():
        client = client_module.get_user_supabase()
        return jsonify({'marker': client.marker})

    cached_client = client_module._supabase_client
    with (
        patch(
            'src.contexts.identity.interface.auth_decorators.get_supabase',
            return_value=verification_client,
        ),
        patch(
            'src.shared.infrastructure.supabase_client._lazy_create_client',
            side_effect=[first_client, second_client],
        ) as create_client,
    ):
        first_response = app.test_client().get(
            '/rls-client',
            headers={'Authorization': 'Bearer token-a'},
        )
        second_response = app.test_client().get(
            '/rls-client',
            headers={'Authorization': 'Bearer token-b'},
        )

    assert first_response.get_json() == {'marker': 'first-client'}
    assert second_response.get_json() == {'marker': 'second-client'}
    assert create_client.call_count == 2
    first_options = create_client.call_args_list[0].args[2]
    second_options = create_client.call_args_list[1].args[2]
    assert first_options.headers['Authorization'] == 'Bearer token-a'
    assert second_options.headers['Authorization'] == 'Bearer token-b'
    assert first_options.headers is not second_options.headers
    assert client_module._supabase_client is cached_client


@pytest.mark.parametrize(
    ('user_id', 'access_token'),
    [('user-1', None), (None, 'unbound-token')],
)
def test_enabled_mode_never_falls_back_to_anon_without_validated_request(
    monkeypatch,
    user_id,
    access_token,
):
    from src.shared.infrastructure.supabase_client import get_user_supabase

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')
    app = Flask(__name__)

    with app.test_request_context('/'):
        g.user_id = user_id
        g.access_token = access_token
        with (
            patch(
                'src.shared.infrastructure.supabase_client._lazy_create_client'
            ) as create_client,
            pytest.raises(ConfigurationError),
        ):
            get_user_supabase()

    create_client.assert_not_called()


def test_background_user_client_requires_explicit_validated_token(monkeypatch):
    from src.shared.infrastructure.supabase_client import get_user_supabase

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')
    scoped_client = MagicMock()

    with patch(
        'src.shared.infrastructure.supabase_client._lazy_create_client',
        return_value=scoped_client,
    ) as create_client:
        result = get_user_supabase(validated_access_token='background-token')

    assert result is scoped_client
    assert create_client.call_args.args[2].headers['Authorization'] == (
        'Bearer background-token'
    )


def test_real_user_client_applies_jwt_to_postgrest_only_on_fresh_instance(
    monkeypatch,
):
    import src.shared.infrastructure.supabase_client as client_module

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')
    cached_client = client_module._supabase_client

    client = client_module.get_user_supabase(
        validated_access_token='integration-token',
    )

    assert client.options.headers['Authorization'] == 'Bearer integration-token'
    assert client.postgrest.headers['Authorization'] == 'Bearer integration-token'
    assert client_module._supabase_client is cached_client


def test_disabled_local_mode_preserves_none_behavior(monkeypatch):
    from src.shared.infrastructure.supabase_client import get_user_supabase

    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_ANON_KEY', raising=False)

    with patch(
        'src.shared.infrastructure.supabase_client._lazy_create_client'
    ) as create_client:
        assert get_user_supabase() is None

    create_client.assert_not_called()


def test_service_role_access_is_explicit_and_fails_closed(monkeypatch):
    from src.shared.infrastructure.supabase_client import get_service_supabase

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_ANON_KEY', 'anon-key')
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)

    with pytest.raises(ConfigurationError):
        get_service_supabase()


def test_current_publishable_and_secret_key_names_are_supported(monkeypatch):
    import src.shared.infrastructure.supabase_client as client_module

    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_PUBLISHABLE_KEY', 'sb_publishable_test')
    monkeypatch.setenv('SUPABASE_SECRET_KEY', 'sb_secret_test')
    monkeypatch.delenv('SUPABASE_ANON_KEY', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_ROLE_KEY', raising=False)
    monkeypatch.setattr(client_module, '_supabase_client', None)
    monkeypatch.setattr(client_module, '_supabase_admin', None)

    public_client = MagicMock(name='public-client')
    admin_client = MagicMock(name='admin-client')
    with patch(
        'src.shared.infrastructure.supabase_client._lazy_create_client',
        side_effect=[public_client, admin_client],
    ) as create_client:
        assert client_module.is_supabase_enabled() is True
        assert client_module.get_supabase() is public_client
        assert client_module.get_service_supabase() is admin_client

    assert create_client.call_args_list == [
        call('https://example.supabase.co', 'sb_publishable_test'),
        call('https://example.supabase.co', 'sb_secret_test'),
    ]


def test_rls_services_use_user_scoped_helper():
    from services.data import (
        prompt_template_service,
        style_memory_service,
        workspace_service,
    )

    with (
        patch.object(prompt_template_service, 'is_supabase_enabled', return_value=True),
        patch.object(
            prompt_template_service,
            'get_user_supabase',
            return_value=None,
        ) as prompt_client,
    ):
        assert prompt_template_service.get_templates('user-1')['templates'] == []
    prompt_client.assert_called_once_with()

    with (
        patch.object(workspace_service, 'is_supabase_enabled', return_value=True),
        patch.object(
            workspace_service,
            'get_user_supabase',
            return_value=None,
        ) as workspace_client,
    ):
        assert workspace_service.WorkspaceService().list_workspaces('user-1') == []
    workspace_client.assert_called_once_with()

    with (
        patch.object(style_memory_service, 'is_supabase_enabled', return_value=True),
        patch.object(
            style_memory_service,
            'get_user_supabase',
            return_value=None,
        ) as style_client,
    ):
        profile = style_memory_service.get_profile('user-1')
        assert profile['preferred_length'] == 'medium'
    style_client.assert_called_once_with(validated_access_token=None)


def test_style_profile_background_handoff_is_token_isolated():
    from routes.generation_helpers import _queue_style_profile_update

    with (
        patch('threading.Thread', _ImmediateThread),
        patch('services.data.style_memory_service.update_profile') as update_profile,
    ):
        _queue_style_profile_update(
            'user-a',
            {'style': 'summary'},
            'token-a',
        )
        _queue_style_profile_update(
            'user-b',
            {'style': 'tutorial'},
            'token-b',
        )

    assert update_profile.call_args_list == [
        call(
            'user-a',
            {'style': 'summary'},
            validated_access_token='token-a',
        ),
        call(
            'user-b',
            {'style': 'tutorial'},
            validated_access_token='token-b',
        ),
    ]


def test_history_background_handoff_passes_validated_request_token():
    from routes.generation_helpers import _persist_generation_result

    app = Flask(__name__)
    app.ai_cache = MagicMock()
    params = {
        'model': 'chatmock/test',
        'modifiers': {},
        'style': 'summary',
        'output_format': 'html',
        'max_chars': None,
    }

    with (
        app.test_request_context('/'),
        patch('threading.Thread', _ImmediateThread),
        patch('routes.generation_helpers.save_history') as save_history,
    ):
        g.user_id = 'user-a'
        g.access_token = 'token-a'
        _persist_generation_result(
            'cache-key',
            'video-id',
            params,
            'https://example.com/video',
            'Video',
            {'title': 'Title', 'content': 'Body', 'html': '<p>Body</p>'},
            'internal-prompt',
            None,
            'transcript',
            'youtube',
            [],
            1.0,
            'report-id',
        )

    save_history.assert_called_once()
    assert save_history.call_args.args[0] == 'user-a'
    assert save_history.call_args.kwargs == {
        'validated_access_token': 'token-a',
    }


def test_prompt_context_captures_token_before_worker_thread():
    from services.core.ai_prompt_context import build_optional_prompt_contexts

    app = Flask(__name__)
    with (
        app.test_request_context('/'),
        patch('config.RAG_ENABLED', False),
        patch('config.WEB_SEARCH_ENABLED', False),
        patch(
            'services.data.style_memory_service.get_profile',
            return_value={'style_memory_enabled': True},
        ) as get_profile,
        patch(
            'services.data.style_memory_service.build_style_context',
            return_value='style-context',
        ),
        patch(
            'services.data.memory_service.memory_service.build_prompt_context',
            return_value='',
        ),
    ):
        g.user_id = 'user-a'
        g.access_token = 'token-a'
        contexts = build_optional_prompt_contexts('content', user_id='user-a')

    assert contexts[3] == 'style-context'
    get_profile.assert_called_once_with(
        'user-a',
        validated_access_token='token-a',
    )


def test_history_call_chain_forwards_explicit_background_token():
    from src.contexts.content_library import save_history_entry

    with patch(
        'services.data.supabase_service.get_user_supabase',
        return_value=None,
    ) as get_client:
        result = save_history_entry(
            'user-a',
            {'id': 'report-a', 'title': 'Title'},
            validated_access_token='token-a',
        )

    assert result is None
    get_client.assert_called_once_with(validated_access_token='token-a')
