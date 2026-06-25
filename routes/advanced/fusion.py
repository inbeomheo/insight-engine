"""퓨전 생성 라우트 — N개 URL을 1편으로 융합. advanced_routes.py에서 분리."""
from flask import current_app, g, jsonify, request

from routes.blog_routes import blog_bp
from extensions import limiter
from src.contexts.identity.interface.auth_decorators import require_auth
from services.usage import require_usage
from services.usage.usage_service import UsageService
from utils.responses import handle_error


@blog_bp.route('/api/generate-fusion', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_fusion():
    """퓨전 생성: N개 URL → 융합 1편"""
    data = request.get_json(silent=True) or {}
    urls = data.get('urls', [])
    style_id = data.get('style', 'blog_seo')
    model = data.get('model', '')
    modifiers = data.get('modifiers', {})
    enable_web_research = data.get('enable_web_research', True)
    enable_deep_comments = data.get('enable_deep_comments', True)

    if not urls or len(urls) < 2:
        return jsonify({'error': '[입력 오류] 퓨전 분석은 최소 2개 URL이 필요합니다'}), 400
    if len(urls) > 5:
        return jsonify({'error': '[입력 오류] 퓨전 분석은 최대 5개 URL까지 가능합니다'}), 400
    if not model:
        return jsonify({'error': '[입력 오류] 모델을 선택해주세요'}), 400

    use_background_job = bool(data.get('async') or data.get('background') or data.get('use_job'))
    if use_background_job:
        from services.core import fusion_service, job_service

        app = current_app._get_current_object()
        user_id = getattr(g, 'user_id', None)
        is_admin = bool(getattr(g, 'is_admin', False))

        def _run_fusion_job():
            with app.app_context():
                return fusion_service.generate_fusion(
                    urls=urls,
                    style_id=style_id,
                    model=model,
                    modifiers=modifiers,
                    enable_web_research=enable_web_research,
                    enable_deep_comments=enable_deep_comments
                )

        def _consume_usage(_result):
            if user_id and not is_admin:
                UsageService.decrement(user_id)

        job = job_service.create_job(
            'fusion',
            {
                'urls': urls,
                'style': style_id,
                'model': model,
                'modifiers': modifiers,
                'enable_web_research': enable_web_research,
                'enable_deep_comments': enable_deep_comments,
            },
            _run_fusion_job,
            owner_user_id=user_id,
            steps=['fusion'],
            on_success=_consume_usage,
        )
        g.skip_usage_decrement = True
        return jsonify({
            'async': True,
            'job_id': job['id'],
            'job': job,
            'status': job['status'],
        }), 202

    try:
        from services.core import fusion_service
        result = fusion_service.generate_fusion(
            urls=urls,
            style_id=style_id,
            model=model,
            modifiers=modifiers,
            enable_web_research=enable_web_research,
            enable_deep_comments=enable_deep_comments
        )

        return jsonify(result)

    except ValueError as e:
        return handle_error(f'[입력 오류] {str(e)}')
    except Exception as e:
        current_app.logger.error('퓨전 생성 실패: %s', e, exc_info=True)
        return handle_error(str(e))
