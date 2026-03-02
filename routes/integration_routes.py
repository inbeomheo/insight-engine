"""
통합 서비스 라우트 — MCP 플러그인, 예약 발행, RAG 지식 베이스
"""
import uuid

from flask import request, jsonify, current_app, g

from routes.blog_routes import blog_bp
from services.supabase_service import require_auth

# ── MCP 플러그인 ──────────────────────────────────────



@blog_bp.route('/api/mcp/plugins', methods=['GET'])
def mcp_list_plugins():
    """등록된 MCP 플러그인 목록을 반환합니다."""
    from services.mcp import plugin_registry
    return jsonify({"plugins": plugin_registry.list_plugins()})


@blog_bp.route('/api/mcp/publish', methods=['POST'])
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

    result = plugin_registry.execute(plugin_id, content, title)
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

    result = app.render(data)
    return jsonify(result)


@blog_bp.route('/api/mcp-apps/<app_name>/action', methods=['POST'])
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

    result = app.handle_action(action, data)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


# ── 발행 큐 (재시도 정책) ──────────────────────────────────────


@blog_bp.route('/api/publish-queue', methods=['GET'])
@require_auth
def publish_queue_list():
    """현재 사용자의 발행 큐 목록 조회"""
    from services.publish_queue_service import publish_queue_service

    user_id = getattr(g, 'user_id', None)
    items = publish_queue_service.get_queue_status(user_id=user_id)
    return jsonify({'items': items})


@blog_bp.route('/api/publish-queue', methods=['POST'])
@require_auth
def publish_queue_enqueue():
    """발행 큐에 새 항목 추가"""
    from services.publish_queue_service import publish_queue_service

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    content_id = data.get('content_id')
    title = data.get('title')
    content = data.get('content')
    plugin_id = data.get('plugin_id')

    if not content_id or not title or not content or not plugin_id:
        return jsonify({
            'error': 'content_id, title, content, plugin_id는 필수입니다.',
        }), 400

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    item = publish_queue_service.enqueue(
        content_id=content_id,
        title=title,
        content=content,
        plugin_id=plugin_id,
        user_id=user_id,
    )
    return jsonify(item), 201


@blog_bp.route('/api/publish-queue/<item_id>/cancel', methods=['POST'])
@require_auth
def publish_queue_cancel(item_id: str):
    """큐 항목 취소"""
    from services.publish_queue_service import publish_queue_service

    result = publish_queue_service.cancel_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@blog_bp.route('/api/publish-queue/<item_id>/retry', methods=['POST'])
@require_auth
def publish_queue_retry(item_id: str):
    """실패 항목 수동 재시도"""
    from services.publish_queue_service import publish_queue_service

    result = publish_queue_service.retry_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── 예약 발행 ──────────────────────────────────────


@blog_bp.route('/api/schedule', methods=['POST'])
@require_auth
def schedule_create():
    """예약 발행 생성"""
    from services.schedule_service import schedule_service

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    title = data.get('title')
    content = data.get('content')
    html = data.get('html')
    target_plugin = data.get('target_plugin')
    scheduled_at = data.get('scheduled_at')

    if not title or not content or not target_plugin or not scheduled_at:
        return jsonify({'error': 'title, content, target_plugin, scheduled_at는 필수입니다.'}), 400

    post = schedule_service.create(
        user_id=g.user_id,
        title=title,
        content=content,
        html=html,
        target_plugin=target_plugin,
        scheduled_at=scheduled_at,
    )
    if post is None:
        return jsonify({'error': '예약 생성에 실패했습니다.'}), 500

    return jsonify(post), 201


@blog_bp.route('/api/schedule', methods=['GET'])
@require_auth
def schedule_list():
    """사용자 예약 목록 조회"""
    from services.schedule_service import schedule_service

    posts = schedule_service.list_by_user(g.user_id)
    return jsonify({'schedules': posts})


@blog_bp.route('/api/schedule/<post_id>', methods=['DELETE'])
@require_auth
def schedule_delete(post_id):
    """예약 삭제"""
    from services.schedule_service import schedule_service

    success = schedule_service.delete(post_id, g.user_id)
    if not success:
        return jsonify({'error': '삭제할 예약을 찾을 수 없습니다.'}), 404

    return jsonify({'success': True})


# ── 지식 베이스 (RAG) ──────────────────────────────────────

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB


@blog_bp.route('/api/knowledge/upload', methods=['POST'])
@require_auth
def knowledge_upload():
    """참고 문서 업로드 → 벡터 DB에 저장"""
    from config import RAG_ENABLED
    if not RAG_ENABLED:
        return jsonify({'error': 'RAG 기능이 비활성화되어 있습니다. RAG_ENABLED=true로 설정해주세요.'}), 400

    if 'file' not in request.files:
        return jsonify({'error': '파일이 필요합니다.'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400

    # 확장자 검증
    allowed_exts = {'txt', 'md', 'pdf'}
    ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ''
    if ext not in allowed_exts:
        return jsonify({'error': f'지원하지 않는 파일 형식입니다. ({", ".join(allowed_exts)}만 가능)'}), 400

    file_bytes = file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        return jsonify({'error': f'파일 크기가 제한을 초과합니다. (최대 {MAX_UPLOAD_SIZE // (1024*1024)}MB)'}), 400

    try:
        from services.rag.chunker import extract_text_from_file, chunk_text
        from services.rag import vector_store
        from datetime import datetime

        text = extract_text_from_file(file_bytes, file.filename)
        if not text.strip():
            return jsonify({'error': '파일에서 텍스트를 추출할 수 없습니다.'}), 400

        chunks = chunk_text(text)
        doc_id = str(uuid.uuid4())
        metadata = {
            'filename': file.filename,
            'uploaded_at': datetime.utcnow().isoformat(),
        }
        vector_store.add_document(g.user_id, doc_id, chunks, metadata)

        return jsonify({
            'id': doc_id,
            'filename': file.filename,
            'chunk_count': len(chunks),
        }), 201

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Knowledge upload failed: {e}")
        return jsonify({'error': '문서 업로드 중 오류가 발생했습니다.'}), 500


@blog_bp.route('/api/knowledge/list', methods=['GET'])
@require_auth
def knowledge_list():
    """업로드된 문서 목록 조회"""
    from config import RAG_ENABLED
    if not RAG_ENABLED:
        return jsonify({'documents': []})

    try:
        from services.rag import vector_store
        docs = vector_store.list_documents(g.user_id)
        return jsonify({'documents': docs})
    except Exception as e:
        current_app.logger.error(f"Knowledge list failed: {e}")
        return jsonify({'documents': []})


@blog_bp.route('/api/knowledge/<doc_id>', methods=['DELETE'])
@require_auth
def knowledge_delete(doc_id):
    """문서 삭제"""
    from config import RAG_ENABLED
    if not RAG_ENABLED:
        return jsonify({'error': 'RAG 기능이 비활성화되어 있습니다.'}), 400

    try:
        from services.rag import vector_store
        vector_store.delete_document(g.user_id, doc_id)
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Knowledge delete failed: {e}")
        return jsonify({'error': '문서 삭제 중 오류가 발생했습니다.'}), 500
