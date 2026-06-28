"""QA 게이트 라우트 — 발행 전 콘텐츠 품질 검증. advanced_routes.py에서 분리."""
import time

from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp
from utils.responses import api_error, handle_error


@blog_bp.route('/api/qa-check', methods=['POST'])
def qa_check():
    """콘텐츠 QA 검증을 실행합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        rules = data.get('rules')

        if not content:
            return api_error('검증할 콘텐츠가 필요합니다.', 400)

        from services.quality.qa_gate_service import check_quality
        t0 = time.monotonic()
        result = check_quality(content, rules)
        result['check_duration_ms'] = round((time.monotonic() - t0) * 1000, 1)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"QA check failed: {e}")
        return handle_error(str(e))
