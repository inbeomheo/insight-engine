"""Error tracking initialization and event sanitization."""
import logging

import pytest

from utils.error_tracking import REDACTED, init_error_tracking, sanitize_event


class DummyApp:
    def __init__(self, testing=False):
        self.testing = testing
        self.config = {'TESTING': testing}
        self.logger = logging.getLogger('test.error_tracking')


def test_init_error_tracking_is_disabled_without_dsn():
    app = DummyApp()

    def fail_loader():
        raise AssertionError('Sentry modules should not be loaded without a DSN')

    status = init_error_tracking(app, env={}, module_loader=fail_loader)

    assert status['status'] == 'disabled'
    assert status['enabled'] is False
    assert app.config['ERROR_TRACKING_STATUS'] == status


def test_init_error_tracking_skips_tests_by_default_even_with_dsn():
    app = DummyApp(testing=True)

    def fail_loader():
        raise AssertionError('Sentry modules should not be loaded in tests by default')

    status = init_error_tracking(
        app,
        env={'SENTRY_DSN': 'https://public@example.invalid/1'},
        module_loader=fail_loader,
    )

    assert status['status'] == 'skipped'
    assert status['enabled'] is False


def test_init_error_tracking_configures_sentry_with_privacy_defaults():
    app = DummyApp()
    init_kwargs = {}

    class FakeSentry:
        @staticmethod
        def init(**kwargs):
            init_kwargs.update(kwargs)

    class FakeFlaskIntegration:
        pass

    status = init_error_tracking(
        app,
        env={
            'FLASK_ENV': 'production',
            'SENTRY_DSN': 'https://public@example.invalid/1',
            'SENTRY_RELEASE': 'test-release',
            'SENTRY_TRACES_SAMPLE_RATE': '0.25',
            'SENTRY_PROFILES_SAMPLE_RATE': '0.10',
        },
        module_loader=lambda: (FakeSentry, FakeFlaskIntegration),
    )

    assert status['status'] == 'ok'
    assert status['enabled'] is True
    assert init_kwargs['dsn'] == 'https://public@example.invalid/1'
    assert init_kwargs['environment'] == 'production'
    assert init_kwargs['release'] == 'test-release'
    assert init_kwargs['traces_sample_rate'] == 0.25
    assert init_kwargs['profiles_sample_rate'] == 0.10
    assert init_kwargs['send_default_pii'] is False
    assert init_kwargs['before_send'] is sanitize_event
    assert isinstance(init_kwargs['integrations'][0], FakeFlaskIntegration)


def test_init_error_tracking_uses_release_metadata_when_sentry_release_is_unset():
    app = DummyApp()
    init_kwargs = {}

    class FakeSentry:
        @staticmethod
        def init(**kwargs):
            init_kwargs.update(kwargs)

    class FakeFlaskIntegration:
        pass

    status = init_error_tracking(
        app,
        env={
            'SENTRY_DSN': 'https://public@example.invalid/1',
            'APP_RELEASE': 'app-release-123',
            'GIT_SHA': 'git-sha-123',
        },
        module_loader=lambda: (FakeSentry, FakeFlaskIntegration),
    )

    assert status['status'] == 'ok'
    assert init_kwargs['release'] == 'app-release-123'


def test_init_error_tracking_required_raises_without_dsn():
    app = DummyApp()

    with pytest.raises(RuntimeError, match='SENTRY_DSN is required'):
        init_error_tracking(app, env={'ERROR_TRACKING_REQUIRED': 'true'})

    assert app.config['ERROR_TRACKING_STATUS']['status'] == 'error'


def test_sanitize_event_redacts_sensitive_request_values():
    event = {
        'request': {
            'headers': {
                'Authorization': 'Bearer should-not-leak',
                'X-Api-Key': 'should-not-leak',
                'User-Agent': 'pytest',
            },
            'cookies': {'sessionid': 'should-not-leak'},
            'query_string': 'token=should-not-leak&safe=ok',
            'url': 'https://example.invalid/path?api_key=should-not-leak&safe=ok',
            'data': {'password': 'should-not-leak', 'title': 'keep-me'},
        },
        'extra': {
            'nested': {
                'refresh_token': 'should-not-leak',
                'count': 1,
            },
        },
    }

    sanitized = sanitize_event(event, {})

    assert sanitized['request']['headers']['Authorization'] == REDACTED
    assert sanitized['request']['headers']['X-Api-Key'] == REDACTED
    assert sanitized['request']['headers']['User-Agent'] == 'pytest'
    assert sanitized['request']['cookies'] == REDACTED
    encoded_redacted = '%5BFiltered%5D'
    assert sanitized['request']['query_string'] == f'token={encoded_redacted}&safe=ok'
    assert sanitized['request']['url'] == f'https://example.invalid/path?api_key={encoded_redacted}&safe=ok'
    assert sanitized['request']['data']['password'] == REDACTED
    assert sanitized['request']['data']['title'] == 'keep-me'
    assert sanitized['extra']['nested']['refresh_token'] == REDACTED
    assert sanitized['extra']['nested']['count'] == 1
