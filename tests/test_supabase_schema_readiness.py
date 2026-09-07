"""Supabase schema-version readiness gate regression tests."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from app import create_app
from utils.production_readiness import (
    REQUIRED_SUPABASE_SCHEMA_VERSION,
    SUPABASE_SCHEMA_VERSION_RPC,
    production_readiness_errors,
    supabase_schema_contract_errors,
)


ROOT = Path(__file__).resolve().parents[1]
_SAFE_PRODUCTION_ENV = {
    'FLASK_ENV': 'production',
    'SUPABASE_URL': 'https://test-project.supabase.co',
    'SUPABASE_PUBLISHABLE_KEY': 'sb_publishable_test',
    'SUPABASE_SECRET_KEY': 'sb_secret_test',
    'CORS_ORIGINS': 'https://app.example.com',
    'PUBLIC_ORIGIN': 'https://app.example.com',
    'METRICS_AUTH_TOKEN': 'metrics-token',
    'ENCRYPTION_SECRET': 'x' * 32,
    'REDIS_URL': 'redis://redis:6379/0',
    'AUTO_BACKUP_INTERVAL_HOURS': '6',
    'MAX_BACKUPS': '30',
    'APP_DATA_BACKUP_DIR': '/mnt/backups/insight-engine',
    'PLATFORM_VOLUME_BACKUPS_ENABLED': 'true',
}


@pytest.fixture(scope='module')
def client():
    with patch.dict('os.environ', {'FLASK_ENV': 'testing'}, clear=False):
        app = create_app({'TESTING': True})
    return app.test_client()


def _live_ready_request(
    client,
    *,
    supabase_enabled: bool = True,
    supabase_client=None,
    client_error: Exception | None = None,
):
    with patch.dict('os.environ', {'FLASK_ENV': 'production'}, clear=False), \
            patch('routes.utility.operations._check_cliproxyapi_ready', return_value=True), \
            patch('routes.utility.operations._check_redis_ready', return_value=True), \
            patch(
                'routes.utility.operations.is_supabase_enabled',
                return_value=supabase_enabled,
            ), \
            patch(
                'routes.utility.operations.get_supabase',
                return_value=supabase_client,
                side_effect=client_error,
            ) as get_supabase:
        response = client.get('/ready')
    return response, get_supabase


def _mock_supabase_response(data):
    rpc_request = Mock()
    rpc_request.execute.return_value = SimpleNamespace(data=data)
    supabase = Mock()
    supabase.rpc.return_value = rpc_request
    return supabase, rpc_request


def test_ready_accepts_required_schema_version_without_mutation_rpc(client):
    supabase, rpc_request = _mock_supabase_response(REQUIRED_SUPABASE_SCHEMA_VERSION)

    response, get_supabase = _live_ready_request(
        client,
        supabase_client=supabase,
    )

    assert response.status_code == 200
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema == {
        'ready': True,
        'enabled': True,
        'checked': True,
        'required_version': 9,
        'current_version': 9,
        'rpc': SUPABASE_SCHEMA_VERSION_RPC,
        'reason': 'ok',
    }
    get_supabase.assert_called_once_with()
    supabase.rpc.assert_called_once_with(SUPABASE_SCHEMA_VERSION_RPC, get=True)
    rpc_request.execute.assert_called_once_with()
    supabase.table.assert_not_called()
    assert [call.args[0] for call in supabase.rpc.call_args_list] == [
        SUPABASE_SCHEMA_VERSION_RPC,
    ]


def test_ready_rejects_unavailable_supabase_client(client):
    response, _get_supabase = _live_ready_request(client, supabase_client=None)

    assert response.status_code == 503
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema['ready'] is False
    assert schema['reason'] == 'client_unavailable'


def test_ready_rejects_supabase_client_creation_error(client):
    response, _get_supabase = _live_ready_request(
        client,
        client_error=RuntimeError('connection failed'),
    )

    assert response.status_code == 503
    assert (
        response.get_json()['dependencies']['supabase_schema']['reason']
        == 'client_error'
    )


@pytest.mark.parametrize('rpc_error', [
    RuntimeError('PGRST202 function is missing'),
    RuntimeError('temporary database error'),
])
def test_ready_rejects_missing_or_failed_schema_rpc(client, rpc_error):
    supabase = Mock()
    supabase.rpc.return_value.execute.side_effect = rpc_error

    response, _get_supabase = _live_ready_request(
        client,
        supabase_client=supabase,
    )

    assert response.status_code == 503
    body = response.get_json()
    assert body['dependencies']['supabase_schema']['reason'] == 'rpc_error'
    assert str(rpc_error) not in str(body)
    supabase.rpc.assert_called_once_with(SUPABASE_SCHEMA_VERSION_RPC, get=True)


def test_ready_rejects_outdated_schema_version(client):
    supabase, _rpc_request = _mock_supabase_response(
        REQUIRED_SUPABASE_SCHEMA_VERSION - 1
    )

    response, _get_supabase = _live_ready_request(
        client,
        supabase_client=supabase,
    )

    assert response.status_code == 503
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema['current_version'] == 8
    assert schema['required_version'] == 9
    assert schema['reason'] == 'schema_outdated'


@pytest.mark.parametrize('payload', [None, '9', [9], {'version': 9}, True])
def test_ready_rejects_malformed_schema_version(client, payload):
    supabase, _rpc_request = _mock_supabase_response(payload)

    response, _get_supabase = _live_ready_request(
        client,
        supabase_client=supabase,
    )

    assert response.status_code == 503
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema['current_version'] is None
    assert schema['reason'] == 'malformed_version'


def test_ready_keeps_explicit_supabase_disabled_local_mode_ready(client):
    with patch.dict('os.environ', {'FLASK_ENV': 'testing'}, clear=False), \
            patch(
                'routes.utility.operations.is_supabase_enabled',
                return_value=False,
            ), \
            patch('routes.utility.operations.get_supabase') as get_supabase:
        response = client.get('/ready')

    assert response.status_code == 200
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema['ready'] is True
    assert schema['enabled'] is False
    assert schema['checked'] is False
    assert schema['reason'] == 'skipped_outside_production'
    get_supabase.assert_not_called()


def test_ready_rejects_supabase_disabled_production(client):
    response, get_supabase = _live_ready_request(
        client,
        supabase_enabled=False,
    )

    assert response.status_code == 503
    schema = response.get_json()['dependencies']['supabase_schema']
    assert schema['reason'] == 'configuration_disabled'
    assert schema['checked'] is False
    get_supabase.assert_not_called()


def test_bundled_supabase_schema_contract_matches_required_version():
    assert supabase_schema_contract_errors(ROOT) == []


def test_offline_readiness_requires_bundled_schema_contract(tmp_path):
    errors = production_readiness_errors(
        _SAFE_PRODUCTION_ENV,
        project_root=tmp_path,
    )

    assert 'Supabase migrations are missing from the deployment artifact' in errors
    assert any('Supabase schema contract file is missing' in error for error in errors)


def test_offline_contract_rejects_stale_version_payload(tmp_path):
    migrations = tmp_path / 'supabase' / 'migrations'
    migrations.mkdir(parents=True)
    stale_contract = '''
CREATE OR REPLACE FUNCTION public.insight_engine_schema_version()
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
    SELECT 8;
$$;
'''
    (tmp_path / 'supabase' / 'schema.sql').write_text(
        stale_contract,
        encoding='utf-8',
    )
    (migrations / '009_workspace_rls_security.sql').write_text(
        stale_contract,
        encoding='utf-8',
    )

    errors = supabase_schema_contract_errors(tmp_path)

    assert len(errors) == 2
    assert all(f'{SUPABASE_SCHEMA_VERSION_RPC}() = 9' in error for error in errors)


def test_offline_contract_requires_version_bump_for_new_migration(tmp_path):
    migrations = tmp_path / 'supabase' / 'migrations'
    migrations.mkdir(parents=True)
    current_contract = '''
CREATE OR REPLACE FUNCTION public.insight_engine_schema_version()
RETURNS INTEGER
LANGUAGE sql
STABLE
SECURITY INVOKER
AS $$
    SELECT 9;
$$;
'''
    (tmp_path / 'supabase' / 'schema.sql').write_text(
        current_contract,
        encoding='utf-8',
    )
    (migrations / '009_workspace_rls_security.sql').write_text(
        current_contract,
        encoding='utf-8',
    )
    (migrations / '010_future.sql').write_text('SELECT 1;', encoding='utf-8')

    errors = supabase_schema_contract_errors(tmp_path)

    assert any('latest bundled migration version (10)' in error for error in errors)
