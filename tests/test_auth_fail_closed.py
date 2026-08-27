"""Authentication bypass and Supabase outage boundary tests."""
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, g, jsonify

from src.contexts.identity.interface.auth_decorators import (
    inject_auth_context,
    require_auth,
)


def _protected_app(*, flask_env: str = '', testing: bool = False) -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=testing, FLASK_ENV=flask_env)
    app.before_request(inject_auth_context)

    @app.get('/protected')
    @require_auth
    def protected():
        return jsonify({'user_id': g.get('user_id')})

    return app


@pytest.mark.parametrize('flask_env', ['development', 'testing'])
def test_missing_supabase_is_bypassed_only_in_explicit_local_environments(flask_env):
    app = _protected_app(flask_env=flask_env)

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == 200
    assert response.get_json() == {'user_id': None}


def test_missing_supabase_is_bypassed_when_flask_testing_is_explicit():
    app = _protected_app(testing=True)

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == 200


@pytest.mark.parametrize('flask_env', ['', 'staging', 'production'])
def test_missing_supabase_fails_closed_outside_explicit_local_mode(
    flask_env,
    monkeypatch,
):
    monkeypatch.setenv('FLASK_ENV', flask_env)
    app = _protected_app(flask_env=flask_env)

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == 503
    assert response.get_json() == {
        'error': '인증 서비스를 일시적으로 사용할 수 없습니다.',
        'code': 'AUTH_SERVICE_UNAVAILABLE',
    }


def test_production_environment_wins_over_testing_flag():
    app = _protected_app(flask_env='production', testing=True)

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=False,
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == 503


@pytest.mark.parametrize(
    ('flask_env', 'expected_status'),
    [('development', 200), ('production', 503)],
)
def test_supabase_configuration_check_error_respects_runtime_boundary(
    flask_env,
    expected_status,
):
    app = _protected_app(flask_env=flask_env)

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        side_effect=RuntimeError('configuration check failed'),
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == expected_status
    if expected_status == 503:
        assert response.get_json()['code'] == 'AUTH_SERVICE_UNAVAILABLE'


def test_enabled_supabase_still_requires_a_bearer_token():
    app = _protected_app(flask_env='production')

    with patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    ):
        response = app.test_client().get('/protected')

    assert response.status_code == 401
    assert response.get_json()['code'] == 'AUTH_REQUIRED'


@pytest.mark.parametrize(
    ('error', 'expected_status', 'expected_code'),
    [
        (Exception('invalid token'), 401, 'TOKEN_INVALID'),
        (Exception('token has expired'), 401, 'TOKEN_EXPIRED'),
        (ConnectionError('connection refused'), 503, 'AUTH_SERVICE_UNAVAILABLE'),
        (Exception('Invalid API key'), 503, 'AUTH_SERVICE_UNAVAILABLE'),
    ],
)
def test_token_errors_are_separated_from_supabase_outages(
    error,
    expected_status,
    expected_code,
):
    app = _protected_app(flask_env='production')
    supabase = MagicMock()
    supabase.auth.get_user.side_effect = error

    with (
        patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=True,
        ),
        patch(
            'src.contexts.identity.interface.auth_decorators.get_supabase',
            return_value=supabase,
        ),
    ):
        response = app.test_client().get(
            '/protected',
            headers={'Authorization': 'Bearer test-token'},
        )

    assert response.status_code == expected_status
    assert response.get_json()['code'] == expected_code


def test_enabled_supabase_with_missing_client_fails_closed():
    app = _protected_app(flask_env='production')

    with (
        patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=True,
        ),
        patch(
            'src.contexts.identity.interface.auth_decorators.get_supabase',
            return_value=None,
        ),
    ):
        response = app.test_client().get(
            '/protected',
            headers={'Authorization': 'Bearer test-token'},
        )

    assert response.status_code == 503
    assert response.get_json()['code'] == 'AUTH_SERVICE_UNAVAILABLE'
