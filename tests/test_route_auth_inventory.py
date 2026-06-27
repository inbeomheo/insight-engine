"""Inventory guard for intentionally unauthenticated POST routes."""

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

INTENTIONAL_UNAUTHENTICATED_POST_ROUTES = {
    # Auth and SSO entry points.
    '/api/auth/signup',
    '/api/auth/reset-password',
    '/api/auth/oauth/callback',
    '/api/auth/login',
    '/api/auth/refresh',
    '/api/sso/<workspace_id>/login',
    '/api/sso/<workspace_id>/callback',

    # Provider-signed or shared-secret inbound webhooks.
    '/api/payment/webhook',
    '/api/paddle/webhook',
    '/api/crypto/webhook',
    '/api/webhooks/slack',
    '/api/webhooks/discord',
    '/api/webhooks/telegram',
    '/api/zapier/trigger',
    '/api/make/webhook',
    '/api/ifttt/trigger',

    # OAuth protocol endpoints.
    '/oauth/register',
    '/oauth/token',
    '/oauth/revoke',

    # Public feedback/support intake with rate limits and handoff approval gates.
    '/api/app-feedback',
    '/api/support/chat',
    '/api/support/tickets/<ticket_id>/create-github-issue',
    '/api/support/tickets/<ticket_id>/create-draft-pr',

    # Browser connection lifecycle telemetry.
    '/api/heartbeat',
    '/api/close',
}


def _literal(value):
    try:
        return ast.literal_eval(value)
    except Exception:
        return None


def _route_path(call: ast.Call) -> str:
    if not call.args:
        return ''
    literal = _literal(call.args[0])
    return literal if isinstance(literal, str) else ast.unparse(call.args[0])


def _route_methods(call: ast.Call) -> set[str]:
    for keyword in call.keywords:
        if keyword.arg != 'methods':
            continue
        literal = _literal(keyword.value)
        if isinstance(literal, (list, tuple, set)):
            return {str(method).upper() for method in literal}
        return {ast.unparse(keyword.value)}
    return {'GET'}


def _decorator_name(decorator: ast.expr) -> str:
    call = decorator if isinstance(decorator, ast.Call) else None
    target = call.func if call else decorator
    if isinstance(target, ast.Attribute):
        return target.attr
    if isinstance(target, ast.Name):
        return target.id
    return ast.unparse(target)


def _unauthenticated_post_routes() -> set[str]:
    routes: set[str] = set()
    for path in sorted((ROOT / 'routes').rglob('*.py')) + [ROOT / 'app.py']:
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decorator_names = [_decorator_name(decorator) for decorator in node.decorator_list]
            if 'require_auth' in decorator_names:
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if _decorator_name(decorator) != 'route':
                    continue
                if 'POST' in _route_methods(decorator):
                    routes.add(_route_path(decorator))
    return routes


def test_unauthenticated_post_route_inventory_is_intentional():
    routes = _unauthenticated_post_routes()

    assert routes == INTENTIONAL_UNAUTHENTICATED_POST_ROUTES
