"""퓨전 생성 라우트 — N개 URL을 1편으로 융합. advanced_routes.py에서 분리."""
from flask import current_app, jsonify, request

from routes.blog_routes import blog_bp
from extensions import limiter
from src.contexts.identity.interface.auth_decorators import require_auth
from services.usage import capture_usage_charge_callback, require_usage
from services.usage.usage_lock import UsageLockUnavailable
from utils.responses import api_error, handle_error


@blog_bp.route('/api/generate-fusion', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_fusion():
    """퓨전 생성: N개 URL → 융합 1편"""
    data = request.get_json()
    urls = data.get('urls', [])
    style_id = data.get('style', 'blog_seo')
    from services.core.ai_service import resolve_public_model
    raw_model = data.get('model')
    modifiers = data.get('modifiers', {})
    enable_web_research = data.get('enable_web_research', True)
    enable_deep_comments = data.get('enable_deep_comments', True)

    if not urls or len(urls) < 2:
        return api_error('[입력 오류] 퓨전 분석은 최소 2개 URL이 필요합니다', 400)
    if len(urls) > 5:
        return api_error('[입력 오류] 퓨전 분석은 최대 5개 URL까지 가능합니다', 400)
    if not raw_model:
        return api_error('[입력 오류] 모델을 선택해주세요', 400)
    try:
        model = resolve_public_model(raw_model, allow_auto=False)
    except ValueError as exc:
        return api_error(f'[입력 오류] {exc}', 400, 'UNSUPPORTED_MODEL')

    try:
        from services.core import fusion_service
        result = fusion_service.generate_fusion(
            urls=urls,
            style_id=style_id,
            model=model,
            modifiers=modifiers,
            enable_web_research=enable_web_research,
            enable_deep_comments=enable_deep_comments,
            on_cost_start=capture_usage_charge_callback(),
        )

        return jsonify(result)

    except UsageLockUnavailable:
        # @require_usage가 표준 503 응답과 미비용 예약 환불을 처리한다.
        raise
    except ValueError as e:
        return handle_error(f'[입력 오류] {str(e)}')
    except Exception as e:
        current_app.logger.error('퓨전 생성 실패: %s', e, exc_info=True)
        return handle_error(str(e))
