"""RAG 지식 베이스 — 벡터 스토어, GraphRAG."""
import uuid

from flask import request, jsonify, current_app, g

from extensions import limiter
from routes.blog_routes import blog_bp
from services.usage import capture_usage_charge_callback, require_usage
from services.usage.usage_lock import UsageLockUnavailable
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error, handle_error


# ── 지식 베이스 (RAG) ──────────────────────────────────────

MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10MB
MAX_GRAPH_INGEST_CHARS = 200_000


@blog_bp.route('/api/knowledge/upload', methods=['POST'])
@limiter.limit("10/minute")
@require_auth
def knowledge_upload():
    """참고 문서 업로드 → 벡터 DB에 저장"""
    from config import RAG_ENABLED
    if not RAG_ENABLED:
        return api_error('RAG 기능이 비활성화되어 있습니다. RAG_ENABLED=true로 설정해주세요.', 400)

    if 'file' not in request.files:
        return api_error('파일이 필요합니다.', 400)

    file = request.files['file']
    if not file.filename:
        return api_error('파일명이 비어 있습니다.', 400)

    # 확장자 검증
    allowed_exts = {'txt', 'md', 'pdf'}
    ext = file.filename.lower().rsplit('.', 1)[-1] if '.' in file.filename else ''
    if ext not in allowed_exts:
        return api_error(f'지원하지 않는 파일 형식입니다. ({", ".join(allowed_exts)}만 가능)', 400)

    file_bytes = file.read()
    if len(file_bytes) > MAX_UPLOAD_SIZE:
        return api_error(f'파일 크기가 제한을 초과합니다. (최대 {MAX_UPLOAD_SIZE // (1024*1024)}MB)', 400)

    try:
        from services.rag.chunker import extract_text_from_file, chunk_text
        from services.rag import vector_store
        from datetime import datetime, timezone

        text = extract_text_from_file(file_bytes, file.filename)
        if not text.strip():
            return api_error('파일에서 텍스트를 추출할 수 없습니다.', 400)

        chunks = chunk_text(text)
        doc_id = str(uuid.uuid4())
        metadata = {
            'filename': file.filename,
            'uploaded_at': datetime.now(timezone.utc).isoformat(),
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
        return api_error('문서 업로드 중 오류가 발생했습니다.', 500)


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
        return api_error('RAG 기능이 비활성화되어 있습니다.', 400)

    try:
        from services.rag import vector_store
        vector_store.delete_document(g.user_id, doc_id)
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Knowledge delete failed: {e}")
        return api_error('문서 삭제 중 오류가 발생했습니다.', 500)


# ── GraphRAG 엔진 ──────────────────────────────────────


@blog_bp.route('/api/rag/graph/ingest', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def graph_rag_ingest():
    """텍스트에서 엔티티/관계를 자동 추출하여 그래프에 추가합니다."""
    from services.rag.graph_rag_engine import GraphRAGEngine

    data = request.get_json(silent=True) or {}
    raw_text = data.get('text', '')
    if not isinstance(raw_text, str):
        return api_error('text는 문자열이어야 합니다.', 400)
    text = raw_text.strip()
    if not text:
        return api_error('text는 필수입니다.', 400)
    if len(text) > MAX_GRAPH_INGEST_CHARS:
        return api_error(
            f'text는 최대 {MAX_GRAPH_INGEST_CHARS:,}자까지 허용됩니다.',
            400,
        )

    try:
        engine = GraphRAGEngine()
        result = engine.ingest(
            g.user_id,
            text,
            on_cost_start=capture_usage_charge_callback(),
        )
        return jsonify(result)
    except UsageLockUnavailable:
        raise
    except Exception as e:
        return handle_error(e, 'GraphRAG 인제스트')
