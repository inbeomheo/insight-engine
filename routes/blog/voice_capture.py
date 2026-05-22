"""핸즈프리 음성 캡처 — 음성 텍스트 정돈/병합 라우트.

blog_routes.py에서 분리됨.
"""
from flask import request, jsonify

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth


@blog_bp.route('/api/capture/speech', methods=['POST'])
@require_auth
def capture_speech():
    """음성 텍스트를 정돈된 텍스트로 변환"""
    from services.content.handsfree_capture_service import capture_speech as do_capture
    data = request.get_json(silent=True) or {}
    raw_text = data.get('text', '')
    if not raw_text or not raw_text.strip():
        return jsonify({'error': '텍스트가 필요합니다.'}), 400
    result = do_capture(raw_text)
    return jsonify({
        'text': result.text,
        'word_count': result.word_count,
        'sentence_count': result.sentence_count,
        'original_length': result.original_length,
    })


@blog_bp.route('/api/capture/merge', methods=['POST'])
@require_auth
def capture_merge():
    """여러 캡처 결과를 병합"""
    from services.content.handsfree_capture_service import capture_speech as do_capture, merge_captures
    data = request.get_json(silent=True) or {}
    texts = data.get('texts', [])
    if not texts:
        return jsonify({'error': '병합할 텍스트 목록이 필요합니다.'}), 400
    captures = [do_capture(t) for t in texts]
    merged = merge_captures(captures)
    return jsonify({
        'text': merged.text,
        'word_count': merged.word_count,
        'sentence_count': merged.sentence_count,
        'original_length': merged.original_length,
    })
