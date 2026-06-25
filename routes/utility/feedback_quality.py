"""사용자 피드백 + 콘텐츠 품질 분석 라우트.

utility_routes.py에서 분리됨:
- AI 캐시 삭제
- 피드백/통계/NPS
- 팩트체크 / SEO 최적화 / 표절 / 가독성 / 감정 흐름
"""
from flask import current_app, g, jsonify, request
from utils.responses import api_error

from routes.blog_routes import blog_bp
from src.contexts.identity.interface.auth_decorators import require_auth


@blog_bp.route('/api/cache/ai', methods=['DELETE'])
@require_auth
def api_clear_ai_cache():
    """AI 결과 캐시를 삭제합니다. videoId가 있으면 해당 영상만."""
    data = request.get_json(silent=True) or {}
    video_id = data.get('videoId')
    deleted = current_app.ai_cache.clear(video_id)
    return jsonify({'success': True, 'deleted': deleted})


# === 피드백 (F3-06) ===

@blog_bp.route('/api/feedback', methods=['POST'])
def api_feedback():
    """사용자 피드백(좋아요/싫어요)을 저장합니다."""
    data = request.get_json(silent=True) or {}
    style_id = data.get('style_id', '')
    content_id = data.get('content_id', '')
    rating = data.get('rating', '')
    comment = data.get('comment')

    if not style_id or not content_id or rating not in ('like', 'dislike'):
        return api_error('style_id, content_id, rating(like/dislike) 필수', 400)

    from services.data.prompt_optimizer_service import save_feedback
    result = save_feedback(
        style_id=style_id,
        content_id=content_id,
        rating=rating,
        comment=comment,
    )
    return jsonify(result)


@blog_bp.route('/api/feedback/stats/<style_id>', methods=['GET'])
def api_feedback_stats(style_id: str):
    """스타일별 피드백 통계를 반환합니다."""
    from services.data.prompt_optimizer_service import get_feedback_stats
    return jsonify(get_feedback_stats(style_id))


# === 팩트체크 (F3-07) ===

@blog_bp.route('/api/fact-check', methods=['POST'])
def api_fact_check():
    """콘텐츠의 팩트체크를 수행합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return api_error('content 필수', 400)

    from services.agents.fact_check_agent import fact_check
    result = fact_check(content)
    return jsonify(result)


# === SEO 최적화 (F3-08) ===

@blog_bp.route('/api/seo-optimize', methods=['POST'])
def api_seo_optimize():
    """콘텐츠의 SEO를 분석하고 최적화 제안을 반환합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    keywords = data.get('keywords', [])
    if not content:
        return api_error('content 필수', 400)

    from services.agents.seo_optimize_agent import optimize_seo
    result = optimize_seo(content, keywords)
    return jsonify(result)


# === 표절 감지 (F3-09) ===

@blog_bp.route('/api/plagiarism-check', methods=['POST'])
def api_plagiarism_check():
    """콘텐츠의 표절/중복 여부를 검사합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return api_error('content 필수', 400)

    from services.quality.plagiarism_service import check_plagiarism
    result = check_plagiarism(content)
    return jsonify(result)


# === 가독성 분석 (F3-10) ===

@blog_bp.route('/api/readability', methods=['POST'])
def api_readability():
    """콘텐츠의 가독성 점수를 분석합니다."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    if not text:
        return api_error('text 필수', 400)

    from services.analysis.readability_service import analyze_readability
    result = analyze_readability(text)
    return jsonify(result)


# === 감정 흐름 분석 (F3-11) ===

@blog_bp.route('/api/sentiment-flow', methods=['POST'])
def api_sentiment_flow():
    """콘텐츠의 문단별 감정 흐름을 분석합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return api_error('content 필수', 400)

    from services.analysis.nlp_analysis_service import analyze_sentiment_flow
    result = analyze_sentiment_flow(content)
    return jsonify(result)


# === NPS 피드백 (F4-20) ===

@blog_bp.route('/api/feedback/nps', methods=['POST'])
def submit_nps_feedback():
    """NPS 점수 + 피드백 제출"""
    data = request.get_json(silent=True) or {}
    score = data.get('score')
    feedback = data.get('feedback', '')

    if score is None or not (0 <= int(score) <= 10):
        return api_error('score는 0~10 사이여야 합니다.', 400)

    # 인메모리 저장 (프로덕션에서는 DB)
    entry = {
        'user_id': getattr(g, 'user_id', 'anonymous'),
        'score': int(score),
        'feedback': feedback,
    }
    return jsonify({'success': True, **entry})
