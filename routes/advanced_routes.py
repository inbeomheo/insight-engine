"""
고급 생성 라우트 — 멀티스타일, 퓨전, 마인드맵, 파이프라인
"""
import concurrent.futures
import json
import time

from flask import request, jsonify, current_app, g, Response, stream_with_context

from routes.blog_routes import blog_bp, _get_request_data, DEFAULT_MODEL
from routes.generation_helpers import (
    _fetch_youtube_content, _build_combined_content
)
from extensions import limiter
from config import get_model_max_tokens
from services.core import ai_service, content_service
from src.contexts.identity.interface.auth_decorators import require_auth
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response
from utils.responses import api_error, handle_error, safe_error_or_fallback, validate_content_length
from prompts import compose_style_prompt


@blog_bp.route('/api/generate-multi', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_multi():
    """하나의 URL을 여러 스타일로 동시에 생성합니다.
    사용량: 멀티 생성 전체 = 1회 차감.
    """
    try:
        start_time = time.time()
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)
        styles = data.get('styles', [])

        if not url:
            return api_error('YouTube URL이 필요합니다.', 400)
        if not content_service.is_youtube_url(url):
            return api_error('유효한 YouTube URL을 입력해주세요.', 400)
        if not styles or not isinstance(styles, list) or len(styles) < 1:
            return api_error('최소 1개 이상의 스타일을 선택해주세요.', 400)
        if len(styles) > 5:
            return api_error('최대 5개 스타일까지 선택할 수 있습니다.', 400)

        video_id = content_service.get_video_id(url)
        if not video_id:
            return api_error('유효하지 않은 YouTube URL입니다.', 400)

        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

        transcript_text, comments, error, raw_transcript, transcript_source, _ = _fetch_youtube_content(video_id)
        if error:
            return api_error(error, 400)

        max_tokens = get_model_max_tokens(model)
        main_content = _build_combined_content(transcript_text, comments) if comments else f"[영상 자막]\n{transcript_text}"
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        # 유효 스타일 필터링
        style_prompts_dict = current_app.config.get('STYLE_PROMPTS', {})
        valid_styles = [s for s in styles if s in style_prompts_dict]
        if not valid_styles:
            return api_error('유효한 스타일이 없습니다.', 400)

        # 병렬 생성
        app = current_app._get_current_object()
        results = []

        def _gen_for_style(style_id):
            with app.app_context():
                style_start = time.time()
                try:
                    sp = compose_style_prompt(style_id, style_prompts_dict.get(style_id, ''))
                    result = ai_service.create_content(
                        truncated_content, model, sp,
                        style_id=style_id
                    )
                    result['style'] = style_id
                    result['style_elapsed_time'] = round(time.time() - style_start, 2)
                    return result
                except Exception as e:
                    return {
                        'style': style_id,
                        'style_elapsed_time': round(time.time() - style_start, 2),
                        'error': safe_error_or_fallback(
                            e,
                            '[서버 오류] 스타일별 콘텐츠 생성 중 문제가 발생했습니다.'
                        )
                    }

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(valid_styles))) as executor:
            futures = {executor.submit(_gen_for_style, s): s for s in valid_styles}
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())

        # 스타일 순서 정렬
        style_order = {s: i for i, s in enumerate(valid_styles)}
        results.sort(key=lambda r: style_order.get(r.get('style', ''), 99))

        elapsed_time = round(time.time() - start_time, 2)

        # 성공/실패 요약
        fail_count = sum(1 for r in results if 'error' in r)
        success_count = len(results) - fail_count

        # 가장 빠른/느린 스타일 식별
        timed = [r for r in results if 'style_elapsed_time' in r and 'error' not in r]
        fastest_style = None
        slowest_style = None
        if timed:
            fastest = min(timed, key=lambda r: r['style_elapsed_time'])
            slowest = max(timed, key=lambda r: r['style_elapsed_time'])
            fastest_style = {'style': fastest['style'], 'elapsed_time': fastest['style_elapsed_time']}
            slowest_style = {'style': slowest['style'], 'elapsed_time': slowest['style_elapsed_time']}

        return jsonify({
            'success': True,
            'results': results,
            'success_count': success_count,
            'fail_count': fail_count,
            'fastest_style': fastest_style,
            'slowest_style': slowest_style,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'elapsed_time': elapsed_time,
            'quota': get_usage_for_response()
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Generate multi failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/pipeline', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
def run_pipeline():
    """파이프라인 실행 SSE 엔드포인트.

    요청: { pipeline_id, url, model, style, modifiers }
    응답: text/event-stream (각 스텝 진행률 이벤트)
    """
    from services.core.pipeline_service import PipelineEngine, PIPELINE_PRESETS
    from services.usage.usage_service import UsageService
    from src.shared.infrastructure.supabase_client import is_supabase_enabled

    try:
        params = _get_request_data(request)
        data = request.get_json(silent=True) or {}
        pipeline_id = data.get('pipeline_id', 'blog_automation')

        if pipeline_id not in PIPELINE_PRESETS:
            return api_error(f'알 수 없는 파이프라인: {pipeline_id}', 400)

        url = params['url']
        if not url:
            return api_error('YouTube URL이 필요합니다.', 400)
        if not content_service.is_youtube_url(url):
            return api_error('유효한 YouTube URL을 입력해주세요.', 400)

        # 사용량 체크
        user_id = getattr(g, 'user_id', None)
        if is_supabase_enabled() and user_id:
            can_use, usage = UsageService.check_can_use(user_id)
            if not can_use:
                return jsonify({
                    'error': '오늘 사용 가능 횟수를 모두 소진했습니다.',
                    'code': 'USAGE_LIMIT_EXCEEDED',
                    'usage': usage
                }), 429

        config = PIPELINE_PRESETS[pipeline_id]
        context = {
            'url': url,
            'model': params['model'],
            'style': params['style'],
            'modifiers': params['modifiers'],
            'custom_prompt': params['custom_prompt'],
        }

        app = current_app._get_current_object()

        def pipeline_sse():
            with app.app_context():
                engine = PipelineEngine(config)
                for event in engine.execute(context):
                    # pipeline_complete 이벤트에서 사용량 차감
                    if event.get('type') == 'pipeline_complete':
                        if is_supabase_enabled() and user_id:
                            UsageService.decrement(user_id)
                        # result에서 불필요한 대용량 필드 제거 (SSE 전송용)
                        result = event.get('result', {})
                        event['result'] = {
                            k: result[k] for k in
                            ('title', 'content', 'html', 'usage', 'prompt',
                             'youtube_title', 'transcript_source', 'seo', 'geo')
                            if k in result
                        }
                    line = json.dumps(event, ensure_ascii=False)
                    yield f"data: {line}\n\n"

        return Response(
            stream_with_context(pipeline_sse()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        current_app.logger.error(f"Pipeline setup failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/inline-edit', methods=['POST'])
@require_auth
@require_usage
def inline_edit_content():
    """선택 영역을 AI로 부분 편집합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        selection = data.get('selection', '')
        instruction = data.get('instruction', '')
        model = data.get('model', DEFAULT_MODEL)

        if not content or not selection:
            return api_error('콘텐츠와 선택 영역이 필요합니다.', 400)
        length_error = validate_content_length(content)
        if length_error:
            return api_error(length_error, 400)
        if not instruction:
            return api_error('편집 지시가 필요합니다.', 400)

        result = ai_service.inline_edit(content, selection, instruction, model)
        return jsonify({
            **result,
            'quota': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Inline edit failed: {e}")
        return handle_error(str(e))


# ============================================================
# 분리된 라우트 패키지 — 부수효과 import로 자동 등록
# - routes/advanced/mindmap.py
# - routes/advanced/fusion.py
# - routes/advanced/qa.py
# ============================================================
from routes import advanced as _advanced_subroutes  # noqa: E402,F401
