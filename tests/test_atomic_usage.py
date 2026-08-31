"""원자적 사용량 예약 / 실패 시 환불."""
from unittest.mock import patch

from flask import Flask, g, jsonify

from services.usage.usage_decorator import require_usage


def test_require_usage_reserves_before_handler():
    app = Flask(__name__)
    app.config["TESTING"] = True
    order = []

    with patch("services.usage.usage_decorator.is_supabase_enabled", return_value=True), patch(
        "services.usage.usage_decorator.UsageService"
    ) as mock_usage:
        mock_usage.try_consume_atomic.return_value = (
            True,
            {"usage_count": 4, "can_use": True, "is_admin": False, "max_usage": 20},
        )

        @require_usage
        def dummy():
            order.append("handler")
            mock_usage.try_consume_atomic.assert_called_once()
            return jsonify({"ok": True})

        with app.test_request_context():
            g.user_id = "user-1"
            resp = dummy()
        assert resp.status_code == 200
        mock_usage.refund.assert_not_called()


def test_require_usage_refunds_on_validation_failure():
    app = Flask(__name__)
    app.config["TESTING"] = True

    with patch("services.usage.usage_decorator.is_supabase_enabled", return_value=True), patch(
        "services.usage.usage_decorator.UsageService"
    ) as mock_usage:
        mock_usage.try_consume_atomic.return_value = (
            True,
            {"usage_count": 4, "can_use": True, "is_admin": False, "max_usage": 20},
        )
        mock_usage.refund.return_value = {"usage_count": 5, "can_use": True, "is_admin": False}

        @require_usage
        def dummy():
            return jsonify({"error": "bad"}), 400

        with app.test_request_context():
            g.user_id = "user-1"
            dummy()
        mock_usage.refund.assert_called_once_with("user-1")


def test_failed_consume_does_not_run_handler():
    app = Flask(__name__)
    ran = []

    with patch("services.usage.usage_decorator.is_supabase_enabled", return_value=True), patch(
        "services.usage.usage_decorator.UsageService"
    ) as mock_usage:
        mock_usage.try_consume_atomic.return_value = (
            False,
            {"usage_count": 0, "can_use": False, "is_admin": False},
        )

        @require_usage
        def dummy():
            ran.append(True)
            return jsonify({"ok": True})

        with app.test_request_context():
            g.user_id = "user-1"
            result = dummy()
        if isinstance(result, tuple):
            _, code = result
        else:
            code = result.status_code
        assert code == 429
        assert ran == []
