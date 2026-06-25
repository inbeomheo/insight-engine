"""플랫폼별 콘텐츠 리라이트 라우트 — advanced_routes.py에서 분리."""
import time

from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp, DEFAULT_MODEL
from src.contexts.identity.interface.auth_decorators import require_auth
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response
from utils.responses import api_error, handle_error, safe_error_or_fallback, validate_content_length


@blog_bp.route('/api/rewrite/platforms')
def rewrite_platforms():
    """지원하는 리라이트 플랫폼 목록을 반환합니다."""
    from config import PLATFORM_PRESETS
    platforms = []
    for name, preset in PLATFORM_PRESETS.items():
        platforms.append({
            'name': name,
            'max_chars': preset['max_chars'],
            'tone': preset['tone'],
            'format': preset['format'],
            'icon_emoji': preset.get('icon_emoji', ''),
        })
    return jsonify({'available_platforms': platforms})


@blog_bp.route('/api/rewrite', methods=['POST'])
@require_auth
@require_usage
def rewrite_content():
    """콘텐츠를 특정 플랫폼 형식으로 변환합니다."""
    try:
        start_time = time.time()
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        platform = data.get('platform', '')
        model = data.get('model', DEFAULT_MODEL)

        if not content:
            return api_error('변환할 콘텐츠가 필요합니다.', 400)
        length_error = validate_content_length(content)
        if length_error:
            return api_error(length_error, 400)
        if not platform:
            return api_error('대상 플랫폼을 선택해주세요.', 400)

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform(content, platform, model)

        if 'error' in result:
            safe_result = dict(result)
            safe_result['error'] = safe_error_or_fallback(
                result.get('error'),
                '[서버 오류] 콘텐츠 변환 중 문제가 발생했습니다.'
            )
            return jsonify(safe_result), 400

        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            **result,
            'elapsed_time': elapsed_time,
            'quota': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Rewrite failed: {e}")
        return handle_error(str(e))
