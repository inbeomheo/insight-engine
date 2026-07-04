"""MCP 앱/서버(인라인 편집 등 인터랙티브 기능). 발행 플러그인 시스템은 제거됨(Dep-5)."""
from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, handle_error


# ── MCP Apps (인터랙티브 UI) ──────────────────────────────────────


@blog_bp.route('/api/mcp-apps', methods=['GET'])
def mcp_apps_list():
    """등록된 MCP 앱 목록을 반환합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401 — 앱 자동 등록 트리거
    return jsonify({"apps": app_registry.list_apps()})


@blog_bp.route('/api/mcp-apps/<app_name>/render', methods=['POST'])
def mcp_app_render(app_name: str):
    """지정된 MCP 앱으로 콘텐츠를 렌더링합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("요청 데이터가 없습니다.", 400)

    app = app_registry.get(app_name)
    if app is None:
        return api_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다.", 404)

    try:
        result = app.render(data)
    except Exception as e:
        current_app.logger.error('MCP app render failed for %s: %s', app_name, e, exc_info=True)
        return api_error('[서버 오류] 앱 렌더링 중 문제가 발생했습니다.', 500)
    return jsonify(result)


@blog_bp.route('/api/mcp-apps/<app_name>/action', methods=['POST'])
def mcp_app_action(app_name: str):
    """MCP 앱의 사용자 액션을 처리합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return api_error("요청 데이터가 없습니다.", 400)

    action = data.get("action")
    if not action:
        return api_error("'action' 필드가 필요합니다.", 400)

    app = app_registry.get(app_name)
    if app is None:
        return api_error(f"앱 '{app_name}'을(를) 찾을 수 없습니다.", 404)

    try:
        result = app.handle_action(action, data)
    except Exception as e:
        current_app.logger.error('MCP app action failed for %s: %s', app_name, e, exc_info=True)
        return api_error('[서버 오류] 앱 작업 처리 중 문제가 발생했습니다.', 500)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


# ── MCP 서버 상태/도구 (F10-09) ──────────────────────────────────────


@blog_bp.route('/api/mcp/status', methods=['GET'])
def mcp_server_status():
    """MCP 서버 상태 및 SDK 설치 여부 확인"""
    from services.mcp.mcp_server import _MCP_AVAILABLE
    return jsonify({
        'mcp_available': _MCP_AVAILABLE,
        'server_name': 'insight-engine',
        'server_version': '1.0.0',
    })


@blog_bp.route('/api/mcp/tools', methods=['GET'])
def mcp_list_tools():
    """MCP 서버에서 제공하는 도구 스키마 목록"""
    from services.mcp.mcp_server import get_mcp_tools_schema
    try:
        tools = get_mcp_tools_schema()
        return jsonify({'tools': tools})
    except Exception as e:
        return handle_error(str(e))


# ── 인라인 편집 앱 (MCP App) ──────────────────────────────────────


@blog_bp.route('/api/mcp/apps/inline-editor/render', methods=['POST'])
@require_auth
def inline_editor_render():
    """인라인 편집 앱 — 콘텐츠를 단락 단위로 렌더링"""
    from services.mcp.apps.inline_editor import InlineEditorApp

    data = request.get_json(silent=True)
    if not data:
        return api_error('요청 데이터가 없습니다.', 400)

    content_text = data.get('content', '').strip()
    if not content_text:
        return api_error('content가 필요합니다.', 400)

    try:
        app = InlineEditorApp()
        result = app.render(data)
        return jsonify(result)
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/mcp/apps/inline-editor/action', methods=['POST'])
@require_auth
def inline_editor_action():
    """인라인 편집 앱 — 편집 액션 처리 (save_edit/undo/reset/get_result)"""
    from services.mcp.apps.inline_editor import InlineEditorApp

    data = request.get_json(silent=True)
    if not data:
        return api_error('요청 데이터가 없습니다.', 400)

    action = data.get('action', '').strip()
    if not action:
        return api_error('action이 필요합니다.', 400)

    try:
        app = InlineEditorApp()
        result = app.handle_action(action, data)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        return handle_error(str(e))
