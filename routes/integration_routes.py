"""
통합 서비스 라우트 — MCP 플러그인, 예약 발행, RAG 지식 베이스, RSS 구독, 북마크, 외부 소스 연동
"""
import os
import uuid

from flask import request, jsonify, current_app, g

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error


# ── Notion 연동 ──────────────────────────────────────


@blog_bp.route('/api/notion/import', methods=['POST'])
@require_auth
def notion_import():
    """Notion 페이지 URL → 콘텐츠 추출"""
    from services.export.notion_service import extract_notion_page

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    page_url = data.get('url', '').strip()
    if not page_url:
        return jsonify({'error': 'Notion 페이지 URL이 필요합니다.'}), 400

    # API 키: 요청 본문 > 환경변수
    api_key = data.get('api_key') or os.getenv('NOTION_API_KEY', '')
    if not api_key:
        return jsonify({'error': 'Notion API 키가 설정되지 않았습니다.'}), 400

    try:
        result = extract_notion_page(page_url, api_key)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Notion import failed: {e}')
        return jsonify({'error': 'Notion 페이지 가져오기 중 오류가 발생했습니다.'}), 500


@blog_bp.route('/api/notion/status', methods=['GET'])
def notion_status():
    """Notion API 키 설정 여부 확인"""
    configured = bool(os.getenv('NOTION_API_KEY', ''))
    return jsonify({'configured': configured})


# ── Google Docs 연동 ──────────────────────────────────────


@blog_bp.route('/api/gdocs/import', methods=['POST'])
@require_auth
def gdocs_import():
    """Google Docs URL → 콘텐츠 추출"""
    from services.export.gdocs_service import extract_google_doc

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    doc_url = data.get('url', '').strip()
    if not doc_url:
        return jsonify({'error': 'Google Docs URL이 필요합니다.'}), 400

    api_key = data.get('api_key') or os.getenv('GOOGLE_API_KEY', '')

    try:
        result = extract_google_doc(doc_url, api_key or None)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Google Docs import failed: {e}')
        return jsonify({'error': 'Google Docs 가져오기 중 오류가 발생했습니다.'}), 500


# ── RSS 구독 ──────────────────────────────────────


@blog_bp.route('/api/rss/subscribe', methods=['POST'])
@require_auth
def rss_subscribe():
    """RSS 피드 구독 추가"""
    from services.platform.rss_subscription_service import subscribe

    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '요청 데이터가 없습니다.'}), 400

    feed_url = data.get('feed_url')
    if not feed_url:
        return jsonify({'error': 'feed_url은 필수입니다.'}), 400

    title = data.get('title', '')
    user_id = getattr(g, 'user_id', None) or 'anonymous'

    try:
        sub = subscribe(user_id, feed_url, title)
        return jsonify(sub), 201
    except ValueError as e:
        return handle_error(str(e))


@blog_bp.route('/api/rss/list', methods=['GET'])
@require_auth
def rss_list():
    """구독 목록 조회"""
    from services.platform.rss_subscription_service import list_subscriptions

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    subs = list_subscriptions(user_id)
    return jsonify({'subscriptions': subs})


@blog_bp.route('/api/rss/unsubscribe/<feed_id>', methods=['DELETE'])
@require_auth
def rss_unsubscribe(feed_id: str):
    """RSS 구독 해제"""
    from services.platform.rss_subscription_service import unsubscribe

    user_id = getattr(g, 'user_id', None) or 'anonymous'
    success = unsubscribe(user_id, feed_id)
    if not success:
        return jsonify({'error': '해당 구독을 찾을 수 없습니다.'}), 404
    return jsonify({'success': True})


# ── 북마크 가져오기 ──────────────────────────────────────


@blog_bp.route('/api/bookmarks/parse', methods=['POST'])
@require_auth
def bookmarks_parse():
    """북마크 HTML 파일 파싱"""
    from services.data.bookmark_import_service import parse_bookmarks

    if 'file' not in request.files:
        return jsonify({'error': '파일이 필요합니다.'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': '파일명이 비어 있습니다.'}), 400

    # HTML 파일 검증
    if not file.filename.lower().endswith(('.html', '.htm')):
        return jsonify({'error': 'HTML 파일만 지원합니다.'}), 400

    try:
        html_content = file.read().decode('utf-8', errors='replace')
        bookmarks = parse_bookmarks(html_content)
        return jsonify({'bookmarks': bookmarks, 'count': len(bookmarks)})
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Bookmark parse failed: {e}")
        return jsonify({'error': '북마크 파싱 중 오류가 발생했습니다.'}), 500


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
    from services.data.publish_queue_service import publish_queue_service

    user_id = getattr(g, 'user_id', None)
    items = publish_queue_service.get_queue_status(user_id=user_id)
    return jsonify({'items': items})


@blog_bp.route('/api/publish-queue', methods=['POST'])
@require_auth
def publish_queue_enqueue():
    """발행 큐에 새 항목 추가"""
    from services.data.publish_queue_service import publish_queue_service

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
    from services.data.publish_queue_service import publish_queue_service

    result = publish_queue_service.cancel_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


@blog_bp.route('/api/publish-queue/<item_id>/retry', methods=['POST'])
@require_auth
def publish_queue_retry(item_id: str):
    """실패 항목 수동 재시도"""
    from services.data.publish_queue_service import publish_queue_service

    result = publish_queue_service.retry_item(item_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── 예약 발행 ──────────────────────────────────────


@blog_bp.route('/api/schedule', methods=['POST'])
@require_auth
def schedule_create():
    """예약 발행 생성"""
    from services.data.schedule_service import schedule_service

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
    from services.data.schedule_service import schedule_service

    posts = schedule_service.list_by_user(g.user_id)
    return jsonify({'schedules': posts})


@blog_bp.route('/api/schedule/<post_id>', methods=['DELETE'])
@require_auth
def schedule_delete(post_id):
    """예약 삭제"""
    from services.data.schedule_service import schedule_service

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
        return handle_error(str(e))
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


# ── 이메일 뉴스레터 인제스트 ──────────────────────────────────────


@blog_bp.route('/api/email/ingest', methods=['POST'])
@require_auth
def email_ingest():
    """이메일 뉴스레터에서 콘텐츠를 추출합니다.

    - .eml 파일 업로드: multipart/form-data의 'file' 필드
    - 포워딩 텍스트: JSON의 'raw_text' 필드
    """
    from services.content.email_ingest_service import parse_email_file, parse_forwarded_email

    # 파일 업로드 모드
    if 'file' in request.files:
        file = request.files['file']
        if not file.filename:
            return jsonify({'error': '파일명이 비어 있습니다.'}), 400
        if not file.filename.lower().endswith('.eml'):
            return jsonify({'error': '.eml 파일만 지원합니다.'}), 400

        try:
            result = parse_email_file(file)
            return jsonify(result)
        except ValueError as e:
            return handle_error(str(e))
        except Exception as e:
            current_app.logger.error(f'Email ingest failed: {e}')
            return jsonify({'error': '이메일 파싱 중 오류가 발생했습니다.'}), 500

    # 텍스트 모드 (포워딩된 이메일)
    data = request.get_json(silent=True)
    if not data:
        return jsonify({'error': '.eml 파일 또는 raw_text가 필요합니다.'}), 400

    raw_text = data.get('raw_text', '').strip()
    if not raw_text:
        return jsonify({'error': 'raw_text가 비어 있습니다.'}), 400

    try:
        result = parse_forwarded_email(raw_text)
        return jsonify(result)
    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f'Email ingest (text) failed: {e}')
        return jsonify({'error': '이메일 텍스트 파싱 중 오류가 발생했습니다.'}), 500


# ── 버전 히스토리 (F5-04) ────────────────────────────


@blog_bp.route('/api/content/<content_id>/versions', methods=['GET'])
def list_content_versions(content_id):
    """콘텐츠의 버전 목록을 반환합니다."""
    from services.data.version_service import list_versions
    return jsonify({'versions': list_versions(content_id)})


@blog_bp.route('/api/content/<content_id>/versions', methods=['POST'])
def save_content_version(content_id):
    """콘텐츠의 새 버전을 저장합니다."""
    from services.data.version_service import save_version
    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    if not content:
        return jsonify({'error': '콘텐츠가 비어 있습니다.'}), 400

    version = save_version(
        content_id=content_id,
        title=title,
        content=content,
        html=data.get('html', ''),
        author_id=data.get('author_id', ''),
        note=data.get('note', ''),
    )
    return jsonify(version), 201


@blog_bp.route('/api/content/<content_id>/versions/<version_id>', methods=['GET'])
def get_content_version(content_id, version_id):
    """특정 버전의 전체 데이터를 반환합니다."""
    from services.data.version_service import get_version
    ver = get_version(content_id, version_id)
    if not ver:
        return jsonify({'error': '버전을 찾을 수 없습니다.'}), 404
    return jsonify(ver)


@blog_bp.route('/api/content/<content_id>/versions/diff', methods=['GET'])
def diff_content_versions(content_id):
    """두 버전의 차이를 반환합니다."""
    from services.data.version_service import diff_versions
    a = request.args.get('a', '')
    b = request.args.get('b', '')
    if not a or not b:
        return jsonify({'error': 'a, b 버전 ID가 필요합니다.'}), 400

    result = diff_versions(content_id, a, b)
    if not result:
        return jsonify({'error': '버전을 찾을 수 없습니다.'}), 404
    return jsonify(result)


@blog_bp.route('/api/content/<content_id>/versions/<version_id>/restore', methods=['POST'])
def restore_content_version(content_id, version_id):
    """특정 버전을 복원합니다."""
    from services.data.version_service import restore_version
    ver = restore_version(content_id, version_id)
    if not ver:
        return jsonify({'error': '버전을 찾을 수 없습니다.'}), 404
    return jsonify(ver), 201


# ── 전문 검색 (F5-09) ────────────────────────────────


@blog_bp.route('/api/search', methods=['GET'])
def search_content():
    """콘텐츠를 검색합니다."""
    from services.seo.search_service import search
    query = request.args.get('q', '')
    style = request.args.get('style', None)
    limit = min(int(request.args.get('limit', '20')), 50)
    offset = int(request.args.get('offset', '0'))

    result = search(query, style_filter=style, limit=limit, offset=offset)
    return jsonify(result)


# ── 폴더/카테고리 (F5-11) ────────────────────────────


@blog_bp.route('/api/folders', methods=['GET'])
def list_content_folders():
    """폴더 목록을 반환합니다."""
    from services.data.folder_service import list_folders
    parent_id = request.args.get('parent_id', None)
    return jsonify({'folders': list_folders(parent_id=parent_id)})


@blog_bp.route('/api/folders', methods=['POST'])
def create_content_folder():
    """폴더를 생성합니다."""
    from services.data.folder_service import create_folder
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': '폴더 이름이 필요합니다.'}), 400

    folder = create_folder(name=name, parent_id=data.get('parent_id'))
    return jsonify(folder), 201


@blog_bp.route('/api/folders/<folder_id>', methods=['PUT'])
def update_content_folder(folder_id):
    """폴더를 수정합니다."""
    from services.data.folder_service import update_folder
    data = request.get_json(silent=True) or {}
    folder = update_folder(folder_id, name=data.get('name'))
    if not folder:
        return jsonify({'error': '폴더를 찾을 수 없습니다.'}), 404
    return jsonify(folder)


@blog_bp.route('/api/folders/<folder_id>', methods=['DELETE'])
def delete_content_folder(folder_id):
    """폴더를 삭제합니다."""
    from services.data.folder_service import delete_folder
    if not delete_folder(folder_id):
        return jsonify({'error': '폴더를 찾을 수 없습니다.'}), 404
    return jsonify({'success': True})


@blog_bp.route('/api/folders/<folder_id>/contents', methods=['GET'])
def list_folder_content_ids(folder_id):
    """폴더의 콘텐츠 ID 목록을 반환합니다."""
    from services.data.folder_service import list_folder_contents
    return jsonify({'content_ids': list_folder_contents(folder_id)})


@blog_bp.route('/api/content/<content_id>/folder', methods=['PUT'])
def move_content_to_folder(content_id):
    """콘텐츠를 폴더로 이동합니다."""
    from services.data.folder_service import move_content
    data = request.get_json(silent=True) or {}
    folder_id = data.get('folder_id')  # None이면 미분류
    if not move_content(content_id, folder_id):
        return jsonify({'error': '폴더를 찾을 수 없습니다.'}), 404
    return jsonify({'success': True})


# ── 알림 센터 (F5-13) ────────────────────────────────


@blog_bp.route('/api/notifications', methods=['GET'])
def get_notifications():
    """알림 목록을 반환합니다."""
    from services.data.notification_service import list_notifications
    user_id = request.args.get('user_id', 'anonymous')
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    limit = min(int(request.args.get('limit', '20')), 50)
    offset = int(request.args.get('offset', '0'))

    result = list_notifications(user_id, unread_only=unread_only,
                                limit=limit, offset=offset)
    return jsonify(result)


@blog_bp.route('/api/notifications/<notification_id>/read', methods=['POST'])
def mark_notification_read(notification_id):
    """알림을 읽음으로 표시합니다."""
    from services.data.notification_service import mark_read
    user_id = request.args.get('user_id', 'anonymous')
    mark_read(user_id, notification_id)
    return jsonify({'success': True})


@blog_bp.route('/api/notifications/read-all', methods=['POST'])
def mark_all_notifications_read():
    """모든 알림을 읽음으로 표시합니다."""
    from services.data.notification_service import mark_all_read
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    count = mark_all_read(user_id)
    return jsonify({'success': True, 'count': count})


# ── 협업 세션 (F5-02) ────────────────────────────────


@blog_bp.route('/api/collab/session', methods=['POST'])
def create_collab_session():
    """협업 세션을 생성하거나 참가합니다."""
    from services.data.collaboration_service import create_session
    data = request.get_json(silent=True) or {}
    content_id = data.get('content_id', '')
    user_id = data.get('user_id', 'anonymous')
    user_name = data.get('user_name', '')
    if not content_id:
        return jsonify({'error': 'content_id가 필요합니다.'}), 400

    result = create_session(content_id, user_id, user_name)
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>', methods=['GET'])
def poll_collab_session(session_id):
    """협업 세션 상태를 폴링합니다."""
    from services.data.collaboration_service import get_session
    result = get_session(session_id)
    if not result:
        return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>/update', methods=['POST'])
def update_collab_content(session_id):
    """협업 콘텐츠를 업데이트합니다."""
    from services.data.collaboration_service import update_content
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    content = data.get('content', '')
    cursor = data.get('cursor_position', 0)

    result = update_content(session_id, user_id, content, cursor)
    if not result:
        return jsonify({'error': '세션을 찾을 수 없습니다.'}), 404
    return jsonify(result)


@blog_bp.route('/api/collab/session/<session_id>/heartbeat', methods=['POST'])
def collab_heartbeat(session_id):
    """협업 세션 하트비트."""
    from services.data.collaboration_service import heartbeat
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    cursor = data.get('cursor_position', 0)

    heartbeat(session_id, user_id, cursor)
    return jsonify({'success': True})


@blog_bp.route('/api/collab/session/<session_id>/leave', methods=['POST'])
def leave_collab_session(session_id):
    """협업 세션에서 나갑니다."""
    from services.data.collaboration_service import leave_session
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id', 'anonymous')
    leave_session(session_id, user_id)
    return jsonify({'success': True})


# ── OpenAPI 문서 (F7-08) ──────────────────────────────────────


@blog_bp.route('/api/openapi.json', methods=['GET'])
def openapi_spec():
    """OpenAPI 3.0 스펙 JSON 반환"""
    from services.data.openapi_service import build_openapi_spec
    server_url = request.host_url.rstrip('/')
    spec = build_openapi_spec(server_url=server_url)
    return jsonify(spec)


@blog_bp.route('/api/docs', methods=['GET'])
def api_docs():
    """Swagger UI 렌더링"""
    spec_url = '/api/openapi.json'
    html = f"""<!DOCTYPE html>
<html>
<head>
  <title>Insight Engine API 문서</title>
  <meta charset="utf-8"/>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist/swagger-ui-bundle.js"></script>
  <script>
    SwaggerUIBundle({{
      url: '{spec_url}',
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
      layout: 'BaseLayout'
    }});
  </script>
</body>
</html>"""
    return html, 200, {'Content-Type': 'text/html'}


# ── Slack 봇 웹훅 (F7-02) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/slack', methods=['POST'])
def slack_webhook():
    """Slack Event API 웹훅 수신"""
    from services.integrations.slack_bot_service import slack_bot_service

    body = request.get_data()
    timestamp = request.headers.get('X-Slack-Request-Timestamp', '')
    signature = request.headers.get('X-Slack-Signature', '')

    if not slack_bot_service.verify_signature(body, timestamp, signature):
        return jsonify({'error': 'Slack 서명 검증 실패'}), 401

    payload = request.get_json(silent=True) or {}
    result = slack_bot_service.handle_event(payload)
    return jsonify(result)


# ── Discord 봇 웹훅 (F7-03) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/discord', methods=['POST'])
def discord_webhook():
    """Discord Interactions 엔드포인트"""
    from services.integrations.discord_bot_service import discord_bot_service

    body = request.get_data()
    timestamp = request.headers.get('X-Signature-Timestamp', '')
    signature = request.headers.get('X-Signature-Ed25519', '')

    if not discord_bot_service.verify_signature(body, timestamp, signature):
        return jsonify({'error': 'Discord 서명 검증 실패'}), 401

    payload = request.get_json(silent=True) or {}
    result = discord_bot_service.handle_interaction(payload)
    return jsonify(result)


# ── Telegram 봇 웹훅 (F7-04) ──────────────────────────────────────


@blog_bp.route('/api/webhooks/telegram', methods=['POST'])
def telegram_webhook():
    """Telegram 웹훅 수신"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    update = request.get_json(silent=True) or {}

    # 콜백 쿼리 (인라인 버튼)
    if 'callback_query' in update:
        result = telegram_bot_service.handle_callback_query(update['callback_query'])
    else:
        result = telegram_bot_service.handle_update(update)

    return jsonify(result)


@blog_bp.route('/api/webhooks/telegram/setwebhook', methods=['POST'])
def telegram_set_webhook():
    """Telegram 웹훅 URL 등록"""
    from services.integrations.telegram_bot_service import telegram_bot_service

    data = request.get_json(silent=True) or {}
    webhook_url = data.get('webhook_url', '')
    if not webhook_url:
        return jsonify({'error': 'webhook_url이 필요합니다.'}), 400

    success = telegram_bot_service.set_webhook(webhook_url)
    return jsonify({'success': success})


# ── Zapier 통합 (F7-05) ──────────────────────────────────────


@blog_bp.route('/api/zapier/trigger', methods=['POST'])
def zapier_trigger():
    """Zapier 트리거 — URL과 스타일을 받아 콘텐츠 생성 결과를 반환합니다.

    Zapier Action에서 이 엔드포인트를 호출하면 됩니다.
    """
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')

    if not url:
        return jsonify({'error': 'url이 필요합니다.'}), 400

    # 동기 생성 (Zapier는 동기 응답 필요)
    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return jsonify({'error': '자막을 가져올 수 없습니다.'}), 400

        result = create_content(transcript, style_id)
        return jsonify({
            'title': result.get('title', ''),
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"Zapier 트리거 오류: {e}")
        return jsonify({'error': '콘텐츠 생성 중 오류가 발생했습니다.'}), 500


@blog_bp.route('/api/zapier/auth/test', methods=['GET'])
def zapier_auth_test():
    """Zapier 인증 테스트 엔드포인트"""
    return jsonify({'status': 'ok', 'service': 'Insight Engine'})


# ── Make (Integromat) 통합 (F7-06) ──────────────────────────────────────


@blog_bp.route('/api/make/webhook', methods=['POST'])
def make_webhook():
    """Make (Integromat) 호환 웹훅

    Make 시나리오의 Custom Webhook 모듈에서 이 URL을 트리거로 사용합니다.
    """
    data = request.get_json(silent=True) or {}
    url = data.get('url', '').strip()
    style_id = data.get('style_id', 'blog_seo')
    language = data.get('language', 'ko')
    callback_url = data.get('callback_url', '')  # Make 응답 URL

    if not url:
        return jsonify({'error': 'url이 필요합니다.'}), 400

    # 즉시 수락 응답 (Make는 비동기 처리 가능)
    import threading

    app = current_app._get_current_object()

    def _process():
        with app.app_context():
            try:
                from services.core.content_service import get_transcript
                from services.core.ai_service import create_content
                transcript = get_transcript(url)
                if not transcript:
                    return
                result = create_content(transcript, style_id, modifiers={'language': language})

                # callback_url이 있으면 결과 전달
                if callback_url:
                    import json
                    import urllib.request
                    payload = json.dumps({
                        'title': result.get('title', ''),
                        'content': result.get('content', ''),
                        'source_url': url,
                    }).encode()
                    req = urllib.request.Request(
                        callback_url,
                        data=payload,
                        headers={'Content-Type': 'application/json'},
                    )
                    urllib.request.urlopen(req, timeout=30)
            except Exception as e:
                app.logger.error(f"Make 웹훅 처리 오류: {e}")

    threading.Thread(target=_process, daemon=True).start()
    return jsonify({'accepted': True, 'message': '처리를 시작했습니다.'})


# ── IFTTT 연동 (F7-20) ──────────────────────────────────────


@blog_bp.route('/api/ifttt/trigger', methods=['POST'])
def ifttt_trigger():
    """IFTTT Webhook 트리거

    IFTTT Webhooks 서비스에서 이 URL로 POST 요청을 보내면
    콘텐츠 생성을 시작합니다.

    IFTTT Webhooks 형식: {"value1": "URL", "value2": "스타일", "value3": "언어"}
    """
    data = request.get_json(silent=True) or {}
    url = (data.get('value1') or data.get('url', '')).strip()
    style_id = data.get('value2') or data.get('style_id', 'blog_seo')
    language = data.get('value3') or data.get('language', 'ko')

    if not url:
        return jsonify({'error': 'value1(URL)이 필요합니다.'}), 400

    try:
        from services.core.content_service import get_transcript
        from services.core.ai_service import create_content
        transcript = get_transcript(url)
        if not transcript:
            return jsonify({'error': '자막을 가져올 수 없습니다.'}), 400

        result = create_content(transcript, style_id, modifiers={'language': language})
        return jsonify({
            'title': result.get('title', ''),
            'content_preview': result.get('content', '')[:500],
            'source_url': url,
        })
    except Exception as e:
        current_app.logger.error(f"IFTTT 트리거 오류: {e}")
        return jsonify({'error': '처리 중 오류가 발생했습니다.'}), 500


# ── Airtable 동기화 (F7-21) ──────────────────────────────────────


@blog_bp.route('/api/sync/airtable', methods=['POST'])
def sync_to_airtable():
    """생성된 콘텐츠를 Airtable에 동기화"""
    from services.integrations.airtable_service import airtable_service

    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    style = data.get('style', '')
    url = data.get('url', '')
    table_name = data.get('table_name', 'Contents')

    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    result = airtable_service.sync_content(title, content, style, url, table_name)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── Google Sheets 동기화 (F7-22) ──────────────────────────────────────


@blog_bp.route('/api/sync/gsheets', methods=['POST'])
def sync_to_gsheets():
    """생성된 콘텐츠를 Google Sheets에 동기화"""
    from services.integrations.gsheets_service import gsheets_service

    data = request.get_json(silent=True) or {}
    title = data.get('title', '')
    content = data.get('content', '')
    style = data.get('style', '')
    url = data.get('url', '')
    sheet_name = data.get('sheet_name', 'Contents')

    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    result = gsheets_service.sync_content(title, content, style, url, sheet_name)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code


# ── CMS 통합 허브 (F7-23) ──────────────────────────────────────


@blog_bp.route('/api/cms/publish-all', methods=['POST'])
def cms_publish_all():
    """여러 CMS에 동시에 콘텐츠를 발행합니다."""
    from services.mcp.cms_hub import cms_hub

    data = request.get_json(silent=True) or {}
    plugin_ids = data.get('plugin_ids', [])
    title = data.get('title', '')
    content = data.get('content', '')
    plugin_configs = data.get('plugin_configs', {})

    if not plugin_ids:
        return jsonify({'error': 'plugin_ids 목록이 필요합니다.'}), 400
    if not title or not content:
        return jsonify({'error': 'title과 content가 필요합니다.'}), 400

    result = cms_hub.publish_to_all(plugin_ids, title, content, plugin_configs)
    return jsonify(result)


@blog_bp.route('/api/cms/plugins', methods=['GET'])
def cms_list_plugins():
    """CMS 허브에서 사용 가능한 플러그인 목록"""
    from services.mcp.cms_hub import cms_hub
    return jsonify({'plugins': cms_hub.get_available_plugins()})


@blog_bp.route('/api/cms/validate-config', methods=['POST'])
def cms_validate_config():
    """플러그인 설정 유효성 검사"""
    from services.mcp.cms_hub import cms_hub

    data = request.get_json(silent=True) or {}
    plugin_id = data.get('plugin_id', '')
    config = data.get('config', {})

    if not plugin_id:
        return jsonify({'error': 'plugin_id가 필요합니다.'}), 400

    result = cms_hub.validate_plugin_config(plugin_id, config)
    return jsonify(result)


# ── Webhook Relay (F7-19) ──────────────────────────────────────


@blog_bp.route('/api/webhook-relay', methods=['POST'])
def webhook_relay():
    """다수의 웹훅 URL에 동시 발송"""
    from services.platform.webhook_relay_service import webhook_relay_service

    data = request.get_json(silent=True) or {}
    urls = data.get('urls', [])
    payload = data.get('payload', {})
    headers = data.get('headers', {})
    timeout = min(int(data.get('timeout', 15)), 60)

    if not urls:
        return jsonify({'error': 'urls 목록이 필요합니다.'}), 400
    if not payload:
        return jsonify({'error': 'payload가 필요합니다.'}), 400
    if len(urls) > 50:
        return jsonify({'error': 'URL은 최대 50개까지 허용됩니다.'}), 400

    result = webhook_relay_service.send_all(urls, payload, headers, timeout)
    return jsonify(result)


# ── 앱 피드백 (F7-24) ──────────────────────────────────────


@blog_bp.route('/api/feedback', methods=['POST'])
def submit_feedback():
    """앱 내 피드백 수신"""
    data = request.get_json(silent=True) or {}
    feedback_type = data.get('type', 'general')
    rating = data.get('rating', 0)
    comment = data.get('comment', '').strip()
    page = data.get('page', '/')

    if not comment:
        return jsonify({'error': '코멘트가 필요합니다.'}), 400
    if not (1 <= int(rating) <= 5):
        return jsonify({'error': '별점은 1~5 사이여야 합니다.'}), 400

    valid_types = {'bug', 'feature', 'general'}
    if feedback_type not in valid_types:
        return jsonify({'error': f'유효하지 않은 피드백 유형: {feedback_type}'}), 400

    # 실제 운영 시 DB 저장 / Slack 알림 등으로 연결
    current_app.logger.info(
        f"[피드백] type={feedback_type}, rating={rating}, page={page}, comment={comment[:100]}"
    )
    return jsonify({'success': True, 'message': '피드백이 접수되었습니다.'})


# ── OAuth 2.0 공급자 (F7-25) ──────────────────────────────────────


@blog_bp.route('/oauth/register', methods=['POST'])
def oauth_register_client():
    """OAuth 2.0 클라이언트 등록"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or {}
    name = data.get('client_name', '').strip()
    redirect_uris = data.get('redirect_uris', [])
    scopes = data.get('scopes', ['read'])

    if not name:
        return jsonify({'error': 'client_name이 필요합니다.'}), 400
    if not redirect_uris:
        return jsonify({'error': 'redirect_uris가 필요합니다.'}), 400

    result = oauth_provider_service.register_client(name, redirect_uris, scopes)
    return jsonify(result), 201


@blog_bp.route('/oauth/authorize', methods=['GET', 'POST'])
@require_auth
def oauth_authorize():
    """OAuth 2.0 인가 엔드포인트"""
    from services.auth.oauth_provider_service import oauth_provider_service
    from urllib.parse import urlencode

    if request.method == 'GET':
        # 인가 페이지 (실제로는 로그인 확인 후 동의 화면 표시)
        client_id = request.args.get('client_id', '')
        redirect_uri = request.args.get('redirect_uri', '')
        scope = request.args.get('scope', 'read')
        state = request.args.get('state', '')
        code_challenge = request.args.get('code_challenge', '')
        code_challenge_method = request.args.get('code_challenge_method', 'S256')

        # 인증된 사용자 ID 사용
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            return jsonify({'error': '인증이 필요합니다.'}), 401
        code = oauth_provider_service.create_authorization_code(
            client_id=client_id,
            user_id=user_id,
            scope=scope,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge or None,
            code_challenge_method=code_challenge_method,
        )

        if not code:
            return jsonify({'error': '인가 실패 — 클라이언트 또는 redirect_uri 검증 오류'}), 400

        params = {'code': code}
        if state:
            params['state'] = state
        return jsonify({'redirect_to': f'{redirect_uri}?{urlencode(params)}'})

    return jsonify({'error': 'GET 메서드를 사용하세요.'}), 405


@blog_bp.route('/oauth/token', methods=['POST'])
def oauth_token():
    """OAuth 2.0 토큰 엔드포인트"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or request.form.to_dict()
    grant_type = data.get('grant_type', '')

    if grant_type == 'authorization_code':
        result = oauth_provider_service.exchange_code_for_token(
            code=data.get('code', ''),
            client_id=data.get('client_id', ''),
            client_secret=data.get('client_secret', ''),
            redirect_uri=data.get('redirect_uri', ''),
            code_verifier=data.get('code_verifier'),
        )
    elif grant_type == 'client_credentials':
        result = oauth_provider_service.client_credentials_token(
            client_id=data.get('client_id', ''),
            client_secret=data.get('client_secret', ''),
            scope=data.get('scope', 'read'),
        )
    else:
        result = {'error': 'unsupported_grant_type', 'error_description': f'지원하지 않는 grant_type: {grant_type}'}

    if 'error' in result:
        return jsonify(result), 400
    return jsonify(result)


@blog_bp.route('/oauth/revoke', methods=['POST'])
def oauth_revoke():
    """OAuth 2.0 토큰 폐기"""
    from services.auth.oauth_provider_service import oauth_provider_service

    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    if not token:
        return jsonify({'error': 'token이 필요합니다.'}), 400

    oauth_provider_service.revoke_token(token)
    return jsonify({'success': True})


@blog_bp.route('/oauth/clients', methods=['GET'])
def oauth_list_clients():
    """등록된 OAuth 클라이언트 목록"""
    from services.auth.oauth_provider_service import oauth_provider_service
    return jsonify({'clients': oauth_provider_service.list_clients()})
