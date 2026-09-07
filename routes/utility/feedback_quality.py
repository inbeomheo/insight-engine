"""사용자 피드백 + 콘텐츠 품질 분석 라우트.

utility_routes.py에서 분리됨:
- 피드백
- 팩트체크 / 표절 / 가독성 / 감정 흐름
"""
from flask import jsonify, request
from extensions import limiter
from services.usage import capture_usage_charge_callback, require_usage
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error

from routes.blog_routes import blog_bp


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


# === 팩트체크 (F3-07) ===

@blog_bp.route('/api/fact-check', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def api_fact_check():
    """콘텐츠의 팩트체크를 수행합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return api_error('content 필수', 400)

    from services.agents.fact_check_agent import fact_check
    result = fact_check(content)
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
@limiter.limit("5/minute")
@require_auth
@require_usage
def api_sentiment_flow():
    """콘텐츠의 문단별 감정 흐름을 분석합니다."""
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    if not content:
        return api_error('content 필수', 400)

    from services.core.ai_service import resolve_public_model
    try:
        model = resolve_public_model(data.get('model'))
    except ValueError as exc:
        return api_error(str(exc), 400)

    from services.analysis.nlp_analysis_service import analyze_sentiment_flow
    result = analyze_sentiment_flow(
        content,
        model=model,
        on_cost_start=capture_usage_charge_callback(),
    )
    return jsonify(result)
