"""마인드맵 변환 라우트 — advanced_routes.py에서 분리."""
import time

from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp, DEFAULT_MODEL
from config import get_model_max_tokens
from services.core import ai_service, content_service
from services.data.supabase_service import require_auth
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response
from utils.responses import handle_error, validate_content_length


@blog_bp.route('/api/mindmap', methods=['POST'])
@require_auth
@require_usage
def generate_mindmap():
    """기존 콘텐츠를 마인드맵 형식의 마크다운으로 변환합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (관리자는 무제한).
    """
    try:
        start_time = time.time()
        data = request.get_json(silent=True) or {}
        content = data.get('content')
        model = data.get('model', DEFAULT_MODEL)

        if not content:
            return jsonify({'error': '마인드맵으로 변환할 콘텐츠가 필요합니다.'}), 400

        length_error = validate_content_length(content)
        if length_error:
            return jsonify({'error': length_error}), 400

        # MINDMAP_PROMPT 가져오기
        style_prompts = current_app.config.get('STYLE_PROMPTS', {})
        mindmap_prompt = style_prompts.get('mindmap', '')

        if not mindmap_prompt:
            return jsonify({'error': '마인드맵 프롬프트가 설정되지 않았습니다.'}), 500

        # 콘텐츠 길이 제한 (토큰 절약)
        max_tokens = get_model_max_tokens(model)
        truncated_content = content_service.truncate_text(content, min(max_tokens, 50000))

        result = ai_service.create_content(
            truncated_content,
            model,
            mindmap_prompt
        )

        elapsed_time = round(time.time() - start_time, 2)

        # 마인드맵용 마크다운 콘텐츠 반환
        return jsonify({
            'success': True,
            'markdown': result.get('content', ''),
            'usage': result.get('usage'),
            'elapsed_time': elapsed_time,
            'quota': get_usage_for_response()
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Mindmap generation failed: {e}")
        return handle_error(str(e))
