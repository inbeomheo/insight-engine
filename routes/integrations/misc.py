"""기타 통합 — 앱 피드백."""
from flask import request, jsonify, current_app
from utils.responses import api_error

from routes.blog_routes import blog_bp


# ── 앱 피드백 (F7-24) ──────────────────────────────────────
# 주의: 콘텐츠 품질 피드백(좋아요/싫어요)은 routes/utility/feedback_quality.py의
# `/api/feedback`이 담당. 여기는 앱 일반 의견(별점+코멘트)이므로 경로를 분리한다.


@blog_bp.route('/api/app-feedback', methods=['POST'])
def submit_feedback():
    """앱 내 일반 피드백 수신 (별점 + 코멘트 + 페이지)."""
    data = request.get_json(silent=True) or {}
    feedback_type = data.get('type', 'general')
    rating = data.get('rating', 0)
    comment = data.get('comment', '').strip()
    page = data.get('page', '/')

    if not comment:
        return api_error('코멘트가 필요합니다.', 400)
    if not (1 <= int(rating) <= 5):
        return api_error('별점은 1~5 사이여야 합니다.', 400)

    valid_types = {'bug', 'feature', 'general'}
    if feedback_type not in valid_types:
        return api_error(f'유효하지 않은 피드백 유형: {feedback_type}', 400)

    # 실제 운영 시 DB 저장 또는 운영 알림으로 연결
    current_app.logger.info(
        f"[피드백] type={feedback_type}, rating={rating}, page={page}, comment={comment[:100]}"
    )
    return jsonify({'success': True, 'message': '피드백이 접수되었습니다.'})
