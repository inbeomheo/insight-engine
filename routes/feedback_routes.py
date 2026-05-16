"""Feedback API routes."""

from flask import jsonify, request

from routes.blog_routes import blog_bp


@blog_bp.route('/api/feedback', methods=['POST'])
def api_feedback():
    """Store style/content feedback for prompt optimization."""
    data = request.get_json(silent=True) or {}
    style_id = data.get('style_id', '')
    content_id = data.get('content_id', '')
    rating = data.get('rating', '')
    comment = data.get('comment')

    if not style_id or not content_id or rating not in ('like', 'dislike'):
        return jsonify({'error': 'style_id, content_id, rating(like/dislike) required'}), 400

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
    """Return feedback stats for a style."""
    from services.data.prompt_optimizer_service import get_feedback_stats

    return jsonify(get_feedback_stats(style_id))
