"""Webhook test route service tests."""

from services.platform.webhook_test_service import run_webhook_test


class _FakeWebhook:
    created = []
    result = {"success": True, "status_code": 200}
    error = None

    def __init__(self, *, url, enabled):
        self.url = url
        self.enabled = enabled
        self.__class__.created.append((url, enabled))

    def test(self):
        if self.error:
            raise self.error
        return dict(self.result)


def test_run_webhook_test_rejects_missing_url():
    payload, status = run_webhook_test(
        {},
        webhook_cls=_FakeWebhook,
    )

    assert status == 400
    assert payload == {"success": False, "error": "웹훅 URL이 필요합니다."}


def test_run_webhook_test_sends_enabled_test_payload():
    _FakeWebhook.created = []
    _FakeWebhook.result = {"success": True, "status_code": 204}
    _FakeWebhook.error = None

    payload, status = run_webhook_test(
        {"url": " https://hooks.example.com/test "},
        webhook_cls=_FakeWebhook,
    )

    assert status == 200
    assert payload == {"success": True, "status_code": 204}
    assert _FakeWebhook.created == [("https://hooks.example.com/test", True)]


def test_run_webhook_test_sanitizes_failed_result_error():
    _FakeWebhook.result = {"success": False, "error": "secret token leaked"}
    _FakeWebhook.error = None

    payload, status = run_webhook_test(
        {"url": "https://hooks.example.com/test"},
        webhook_cls=_FakeWebhook,
        sanitize_error=lambda message: f"safe:{message}",
    )

    assert status == 400
    assert payload == {"success": False, "error": "safe:secret token leaked"}


def test_run_webhook_test_normalizes_server_error_prefix():
    _FakeWebhook.result = {"success": False, "error": "[서버 오류] raw detail"}
    _FakeWebhook.error = None

    payload, status = run_webhook_test(
        {"url": "https://hooks.example.com/test"},
        webhook_cls=_FakeWebhook,
        sanitize_error=lambda message: message,
    )

    assert status == 400
    assert payload == {"success": False, "error": "[서버 오류] 웹훅 테스트에 실패했습니다."}


def test_run_webhook_test_handles_test_exceptions():
    _FakeWebhook.error = RuntimeError("boom")
    logged = []

    payload, status = run_webhook_test(
        {"url": "https://hooks.example.com/test"},
        webhook_cls=_FakeWebhook,
        log_error=lambda message, **kwargs: logged.append((message, kwargs)),
    )

    assert status == 500
    assert payload == {"success": False, "error": "[서버 오류] 웹훅 테스트 중 문제가 발생했습니다."}
    assert logged and "Webhook test failed: boom" in logged[0][0]
