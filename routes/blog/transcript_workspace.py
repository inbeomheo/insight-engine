"""F13 자막 워크스페이스 — 문장 단위 분리/편집 라우트.

blog_routes.py에서 분리됨.
"""
import re

from flask import current_app, jsonify

from routes.blog_routes import blog_bp
from routes import blog_routes as _blog_routes
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import sanitize_error_for_client


@blog_bp.route('/api/transcript/<video_id>', methods=['GET'])
@require_auth
def get_structured_transcript(video_id):
    """구조화된 자막 데이터를 반환합니다 (문장 단위 분리 + 타임스탬프).

    응답 형식:
        {
            "sentences": [{"index": 0, "text": "...", "start_time": 12.5}, ...],
            "video_id": "...",
            "source": "api" | "watch" | "supadata" | "whisper" | "cache",
            "source_meta": { ... }  # F15 품질 메타 (존재 시)
        }
    """
    if not video_id or not re.match(r'^[A-Za-z0-9_-]{11}$', video_id):
        return jsonify({'error': '유효하지 않은 video_id 형식입니다.'}), 400

    try:
        transcript_data = _blog_routes.content_service.get_transcript(video_id)
    except Exception as exc:
        current_app.logger.error(f'자막 조회 오류: {exc}')
        return jsonify({'error': '자막 조회에 실패했습니다.'}), 500

    # 에러 응답 처리
    if isinstance(transcript_data, dict) and 'error' in transcript_data:
        error_message = sanitize_error_for_client(transcript_data['error'])
        if error_message.startswith('[서버 오류]'):
            error_message = '[서버 오류] 자막 조회 중 문제가 발생했습니다.'
        return jsonify({'error': error_message}), 422

    # 자막 텍스트 및 세그먼트 추출
    if isinstance(transcript_data, dict):
        text = transcript_data.get('text', '')
        source = transcript_data.get('source', 'unknown')
        segments = transcript_data.get('segments', [])
        source_meta = transcript_data.get('source_meta')
    elif isinstance(transcript_data, str):
        text = transcript_data
        source = 'unknown'
        segments = []
        source_meta = None
    else:
        return jsonify({'error': '자막 데이터 형식이 올바르지 않습니다.'}), 500

    if not text or not text.strip():
        return jsonify({'error': '자막이 비어 있습니다.'}), 422

    # 문장 단위 분리
    try:
        from services.transcript.transcript_workspace_service import parse_transcript_sentences
        sentences = parse_transcript_sentences(text, segments if segments else None)
    except Exception as exc:
        current_app.logger.error(f'자막 가공 오류: {exc}', exc_info=True)
        return jsonify({'error': '[서버 오류] 자막 가공 중 문제가 발생했습니다.'}), 500

    result = {
        'sentences': sentences,
        'sentence_count': len(sentences),
        'video_id': video_id,
        'source': source,
    }
    if source_meta:
        result['source_meta'] = source_meta

    return jsonify(result)
