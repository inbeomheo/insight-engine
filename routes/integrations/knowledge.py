"""RAG 지식 베이스 — 벡터 스토어, GraphRAG, 멀티모달."""
import uuid

from flask import request, jsonify, current_app, g

from routes.blog_routes import blog_bp
from services.data.supabase_service import require_auth
from utils.responses import handle_error, clamp_query_int


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
        from datetime import datetime, timezone

        text = extract_text_from_file(file_bytes, file.filename)
        if not text.strip():
            return jsonify({'error': '파일에서 텍스트를 추출할 수 없습니다.'}), 400

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


# ── GraphRAG 엔진 ──────────────────────────────────────


@blog_bp.route('/api/rag/graph/ingest', methods=['POST'])
@require_auth
def graph_rag_ingest():
    """텍스트에서 엔티티/관계를 자동 추출하여 그래프에 추가합니다."""
    from services.rag.graph_rag_engine import GraphRAGEngine

    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'text는 필수입니다.'}), 400

    try:
        engine = GraphRAGEngine()
        result = engine.ingest(g.user_id, text)
        return jsonify(result)
    except Exception as e:
        return handle_error(e, 'GraphRAG 인제스트')


@blog_bp.route('/api/rag/graph/search/local', methods=['POST'])
@require_auth
def graph_rag_local_search():
    """엔티티 중심 로컬 검색 (BFS 탐색)"""
    from services.rag.graph_rag_engine import GraphRAGEngine

    data = request.get_json(silent=True) or {}
    entities = data.get('entities', [])
    if not entities:
        return jsonify({'error': 'entities 목록은 필수입니다.'}), 400

    try:
        engine = GraphRAGEngine()
        results = engine.local_search(
            g.user_id,
            entities,
            max_depth=clamp_query_int(data.get('max_depth'), default=2, min_val=1, max_val=10),
            max_results=clamp_query_int(data.get('max_results'), default=20, min_val=1, max_val=100),
        )
        return jsonify({'results': results})
    except Exception as e:
        return handle_error(e, 'GraphRAG 로컬 검색')


@blog_bp.route('/api/rag/graph/search/global', methods=['GET'])
@require_auth
def graph_rag_global_search():
    """전체 그래프 요약 — 연결이 많은 상위 노드 반환"""
    from services.rag.graph_rag_engine import GraphRAGEngine

    top_n = clamp_query_int(request.args.get('top_n'), default=10, min_val=1, max_val=100)
    try:
        engine = GraphRAGEngine()
        result = engine.global_search(g.user_id, top_n=top_n)
        return jsonify(result)
    except Exception as e:
        return handle_error(e, 'GraphRAG 글로벌 검색')


# ── 멀티모달 RAG ──────────────────────────────────────


@blog_bp.route('/api/rag/multimodal/detect-type', methods=['POST'])
@require_auth
def multimodal_detect_type():
    """파일 경로의 타입을 감지합니다."""
    from services.rag.multimodal_rag import MultimodalRAG

    data = request.get_json(silent=True) or {}
    file_path = data.get('file_path', '').strip()
    if not file_path:
        return jsonify({'error': 'file_path는 필수입니다.'}), 400

    rag = MultimodalRAG()
    file_type = rag.detect_file_type(file_path)
    return jsonify({'file_path': file_path, 'file_type': file_type})


@blog_bp.route('/api/rag/multimodal/ingest', methods=['POST'])
@require_auth
def multimodal_ingest():
    """파일을 RAG 시스템에 통합합니다."""
    from services.rag.multimodal_rag import MultimodalRAG

    data = request.get_json(silent=True) or {}
    file_path = data.get('file_path', '').strip()
    if not file_path:
        return jsonify({'error': 'file_path는 필수입니다.'}), 400

    try:
        rag = MultimodalRAG()
        result = rag.ingest_file(
            file_path,
            metadata=data.get('metadata'),
            file_type=data.get('file_type'),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return handle_error(e, '멀티모달 RAG 인제스트')


@blog_bp.route('/api/rag/multimodal/query', methods=['POST'])
@require_auth
def multimodal_query():
    """멀티모달 쿼리 (텍스트 + 이미지)"""
    from services.rag.multimodal_rag import MultimodalRAG

    data = request.get_json(silent=True) or {}
    query = data.get('query', '').strip()
    if not query:
        return jsonify({'error': 'query는 필수입니다.'}), 400

    try:
        rag = MultimodalRAG()
        result = rag.query_multimodal(
            query=query,
            image_path=data.get('image_path'),
            top_k=clamp_query_int(data.get('top_k'), default=5, min_val=1, max_val=50),
        )
        return jsonify(result)
    except Exception as e:
        return handle_error(e, '멀티모달 RAG 쿼리')
