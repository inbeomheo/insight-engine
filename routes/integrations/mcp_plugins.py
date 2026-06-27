"""MCP 플러그인/앱/SDK/서버 + CMS 발행 플러그인."""
from flask import request, jsonify, current_app

from routes.blog_routes import blog_bp
from routes.integrations._shared import sanitize_result_message
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import handle_error


# ── MCP 플러그인 ──────────────────────────────────────


@blog_bp.route('/api/mcp/plugins', methods=['GET'])
def mcp_list_plugins():
    """등록된 MCP 플러그인 목록을 반환합니다."""
    from services.mcp import plugin_registry
    return jsonify({"plugins": plugin_registry.list_plugins()})


@blog_bp.route('/api/mcp/publish', methods=['POST'])
@require_auth
def mcp_publish():
    """지정된 플러그인으로 콘텐츠를 발행합니다."""
    from services.mcp import plugin_registry

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "요청 데이터가 없습니다."}), 400

    plugin_id = data.get('plugin_id')
    title = data.get('title')
    content = data.get('content')

    if not plugin_id or not title or not content:
        return jsonify({"error": "plugin_id, title, content는 필수입니다."}), 400

    try:
        result = plugin_registry.execute(plugin_id, content, title)
    except Exception as e:
        current_app.logger.error('MCP publish failed: %s', e, exc_info=True)
        return jsonify({'error': '[서버 오류] 플러그인 발행 중 문제가 발생했습니다.'}), 500

    if not result.get('success'):
        result = sanitize_result_message(
            result,
            'message',
            '[서버 오류] 플러그인 발행에 실패했습니다.'
        )
    status_code = 200 if result.get("success") else 404
    return jsonify(result), status_code


# ── MCP Apps (인터랙티브 UI) ──────────────────────────────────────


@blog_bp.route('/api/mcp-apps', methods=['GET'])
def mcp_apps_list():
    """등록된 MCP 앱 목록을 반환합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401 — 앱 자동 등록 트리거
    return jsonify({"apps": app_registry.list_apps()})


@blog_bp.route('/api/mcp-apps/<app_name>/render', methods=['POST'])
@require_auth
def mcp_app_render(app_name: str):
    """지정된 MCP 앱으로 콘텐츠를 렌더링합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "요청 데이터가 없습니다."}), 400

    app = app_registry.get(app_name)
    if app is None:
        return jsonify({"error": f"앱 '{app_name}'을(를) 찾을 수 없습니다."}), 404

    try:
        result = app.render(data)
    except Exception as e:
        current_app.logger.error('MCP app render failed for %s: %s', app_name, e, exc_info=True)
        return jsonify({'error': '[서버 오류] 앱 렌더링 중 문제가 발생했습니다.'}), 500
    return jsonify(result)


@blog_bp.route('/api/mcp-apps/<app_name>/action', methods=['POST'])
@require_auth
def mcp_app_action(app_name: str):
    """MCP 앱의 사용자 액션을 처리합니다."""
    from services.mcp.mcp_apps import app_registry
    from services.mcp import apps as _  # noqa: F401

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "요청 데이터가 없습니다."}), 400

    action = data.get("action")
    if not action:
        return jsonify({"error": "'action' 필드가 필요합니다."}), 400

    app = app_registry.get(app_name)
    if app is None:
        return jsonify({"error": f"앱 '{app_name}'을(를) 찾을 수 없습니다."}), 404

    try:
        result = app.handle_action(action, data)
    except Exception as e:
        current_app.logger.error('MCP app action failed for %s: %s', app_name, e, exc_info=True)
        return jsonify({'error': '[서버 오류] 앱 작업 처리 중 문제가 발생했습니다.'}), 500
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


# ── 플러그인 SDK 정보 (F7-10) ──────────────────────────────────────


@blog_bp.route('/api/mcp/sdk/info', methods=['GET'])
def mcp_sdk_info():
    """플러그인 SDK 기본 정보 및 등록된 플러그인 목록"""
    from services.mcp.registry import plugin_registry
    plugins = plugin_registry.list_plugins()
    return jsonify({
        'sdk_version': '1.0.0',
        'base_class': 'PluginBase',
        'decorators': ['@plugin', '@require_env'],
        'mixins': ['HttpPluginMixin'],
        'registered_plugins': plugins,
    })


@blog_bp.route('/api/mcp/sdk/schema/<plugin_id>', methods=['GET'])
def mcp_sdk_plugin_schema(plugin_id):
    """특정 플러그인의 설정 스키마 반환"""
    from services.mcp.registry import plugin_registry
    plugin = plugin_registry.get(plugin_id)
    if not plugin:
        return jsonify({'error': f"플러그인 '{plugin_id}'을(를) 찾을 수 없습니다."}), 404
    return jsonify({
        'plugin_id': plugin_id,
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })


# ── 인라인 편집 앱 (MCP App) ──────────────────────────────────────


@blog_bp.route('/api/mcp/apps/inline-editor/render', methods=['POST'])
@require_auth
def inline_editor_render():
    """인라인 편집 앱 — 콘텐츠를 단락 단위로 렌더링"""
    from services.mcp.apps.inline_editor import InlineEditorApp

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    content_text = data.get('content', '').strip()
    if not content_text:
        return jsonify({'error': 'content가 필요합니다.'}), 400

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
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    action = data.get('action', '').strip()
    if not action:
        return jsonify({'error': 'action이 필요합니다.'}), 400

    try:
        app = InlineEditorApp()
        result = app.handle_action(action, data)
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        return handle_error(str(e))


# ── Ghost CMS 발행 플러그인 (F7-13) ──────────────────────────────────────


@blog_bp.route('/api/mcp/plugins/ghost/publish', methods=['POST'])
@require_auth
def ghost_publish():
    """Ghost CMS에 콘텐츠를 발행"""
    from services.mcp.plugins.ghost import GhostPlugin

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    try:
        plugin = GhostPlugin()
        result = plugin.execute(content, title, **{
            k: v for k, v in data.items() if k not in ('title', 'content')
        })
        result = sanitize_result_message(result, 'message', 'Ghost CMS 발행에 실패했습니다.')
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/mcp/plugins/ghost/schema', methods=['GET'])
def ghost_schema():
    """Ghost CMS 플러그인 설정 스키마"""
    from services.mcp.plugins.ghost import GhostPlugin
    plugin = GhostPlugin()
    return jsonify({
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })


# ── Instagram 발행 플러그인 (F7-17) ──────────────────────────────────────


@blog_bp.route('/api/mcp/plugins/instagram/publish', methods=['POST'])
@require_auth
def instagram_publish():
    """Instagram에 콘텐츠를 발행"""
    from services.mcp.plugins.instagram import InstagramPlugin

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    try:
        plugin = InstagramPlugin()
        result = plugin.execute(content, title, **{
            k: v for k, v in data.items() if k not in ('title', 'content')
        })
        result = sanitize_result_message(result, 'message', 'Instagram 발행에 실패했습니다.')
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/mcp/plugins/instagram/schema', methods=['GET'])
def instagram_schema():
    """Instagram 플러그인 설정 스키마"""
    from services.mcp.plugins.instagram import InstagramPlugin
    plugin = InstagramPlugin()
    return jsonify({
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })


# ── Shopify 발행 플러그인 (F7-14) ──────────────────────────────────────


@blog_bp.route('/api/mcp/plugins/shopify/publish', methods=['POST'])
@require_auth
def shopify_publish():
    """Shopify 블로그에 아티클을 발행"""
    from services.mcp.plugins.shopify import ShopifyPlugin

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    try:
        plugin = ShopifyPlugin()
        result = plugin.execute(content, title, **{
            k: v for k, v in data.items() if k not in ('title', 'content')
        })
        result = sanitize_result_message(result, 'message', 'Shopify 발행에 실패했습니다.')
        status_code = 200 if result.get('success') else 400
        return jsonify(result), status_code
    except Exception as e:
        return handle_error(str(e))


@blog_bp.route('/api/mcp/plugins/shopify/schema', methods=['GET'])
def shopify_schema():
    """Shopify 플러그인 설정 스키마"""
    from services.mcp.plugins.shopify import ShopifyPlugin
    plugin = ShopifyPlugin()
    return jsonify({
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })


# ── Substack 발행 (MCP 플러그인) ──────────────────────────────────────


@blog_bp.route('/api/mcp/substack/publish', methods=['POST'])
@require_auth
def substack_publish():
    """Substack에 Draft/Published 포스트를 생성합니다."""
    from services.mcp.plugins.substack import SubstackPlugin

    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    subdomain = data.get('subdomain', '').strip()
    api_key = data.get('api_key', '').strip()

    if not title or not content:
        return jsonify({'error': 'title과 content는 필수입니다.'}), 400
    if not subdomain or not api_key:
        return jsonify({'error': 'subdomain과 api_key는 필수입니다.'}), 400

    try:
        plugin = SubstackPlugin()
        result = plugin.execute(
            content=content,
            title=title,
            subdomain=subdomain,
            api_key=api_key,
            publish_status=data.get('publish_status', 'draft'),
        )
        result = sanitize_result_message(result, 'message', 'Substack 발행 처리 중 오류가 발생했습니다.')
        status = 200 if result.get('success') else 502
        return jsonify(result), status
    except Exception as e:
        return handle_error(e, 'Substack 발행')


@blog_bp.route('/api/mcp/substack/schema', methods=['GET'])
def substack_schema():
    """Substack 플러그인 스키마 조회"""
    from services.mcp.plugins.substack import SubstackPlugin
    plugin = SubstackPlugin()
    return jsonify({
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })


# ── Threads 발행 (MCP 플러그인) ──────────────────────────────────────


@blog_bp.route('/api/mcp/threads/publish', methods=['POST'])
@require_auth
def threads_publish():
    """Threads에 포스트를 게시합니다."""
    from services.mcp.plugins.threads import ThreadsPlugin

    data = request.get_json(silent=True) or {}
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()

    if not content:
        return jsonify({'error': 'content는 필수입니다.'}), 400

    access_token = data.get('access_token', '').strip()
    user_id = data.get('user_id', '').strip()

    if not access_token or not user_id:
        return jsonify({'error': 'access_token과 user_id는 필수입니다.'}), 400

    try:
        plugin = ThreadsPlugin()
        result = plugin.execute(
            content=content,
            title=title or '',
            access_token=access_token,
            user_id=user_id,
            media_type=data.get('media_type', 'TEXT'),
            image_url=data.get('image_url', ''),
        )
        result = sanitize_result_message(result, 'message', 'Threads 발행 처리 중 오류가 발생했습니다.')
        status = 200 if result.get('success') else 502
        return jsonify(result), status
    except Exception as e:
        return handle_error(e, 'Threads 발행')


@blog_bp.route('/api/mcp/threads/schema', methods=['GET'])
def threads_schema():
    """Threads 플러그인 스키마 조회"""
    from services.mcp.plugins.threads import ThreadsPlugin
    plugin = ThreadsPlugin()
    return jsonify({
        'name': plugin.name,
        'description': plugin.description,
        'schema': plugin.schema(),
    })
