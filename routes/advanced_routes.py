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
from utils.responses import api_error, handle_error, safe_error_or_fallback, clamp_query_int, validate_content_length
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

        is_glm = model.startswith('zhipuai/')
        if is_glm:
            # GLM: 순차 실행
            for style_id in valid_styles:
                results.append(_gen_for_style(style_id))
        else:
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


@blog_bp.route('/api/generate-thumbnail', methods=['POST'])
@require_auth
def generate_thumbnail():
    """제목+키워드로 AI 썸네일 이미지를 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', '')
        keywords = data.get('keywords', [])
        size = data.get('size', '1792x1024')

        if not title:
            return api_error('제목이 필요합니다.', 400)

        from services.media.thumbnail_service import generate_thumbnail as _gen_thumb
        result = _gen_thumb(title, keywords, size)

        if not result.get('success'):
            return jsonify({
                'error': safe_error_or_fallback(
                    result.get('error', '썸네일 생성 실패'),
                    '[서버 오류] 썸네일 생성 중 문제가 발생했습니다.'
                )
            }), 400

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Thumbnail generation failed: {e}")
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


# === 에이전트 API ===

@blog_bp.route('/api/agent/research', methods=['POST'])
@require_auth
@require_usage
def agent_research():
    """리서치 에이전트를 실행합니다 (SSE 스트리밍).

    Request body:
        topic (str): 리서치 주제
        model (str): AI 모델 ID
        max_sources (int): 최대 소스 수 (기본 5)

    Returns:
        SSE 이벤트 스트림 (진행 상황 + 최종 결과)
    """
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '').strip()
        model = data.get('model', DEFAULT_MODEL)
        max_sources = clamp_query_int(data.get('max_sources'), default=5, min_val=1, max_val=10)

        if not topic:
            return api_error('리서치 주제가 필요합니다.', 400)

        from services.agents.web_research_agent import ResearchAgent

        def generate_events():
            agent = ResearchAgent(model=model, max_sources=max_sources)
            events = []

            def on_event(event):
                events.append(event)

            agent.on_event(on_event)

            # SSE 스트리밍
            import queue
            import threading
            event_queue = queue.Queue()

            def event_listener(event):
                event_queue.put(event)

            agent.on_event(event_listener)

            def run_agent():
                try:
                    result = agent.run(topic)
                    event_queue.put(('result', result))
                except Exception as e:
                    event_queue.put((
                        'error',
                        safe_error_or_fallback(
                            e,
                            '[서버 오류] 리서치 에이전트 실행 중 문제가 발생했습니다.'
                        )
                    ))

            thread = threading.Thread(target=run_agent, daemon=True)
            thread.start()

            while True:
                try:
                    item = event_queue.get(timeout=300)
                    if isinstance(item, tuple):
                        event_type, data = item
                        if event_type == 'result':
                            yield f"data: {json.dumps({'type': 'result', 'data': data}, ensure_ascii=False)}\n\n"
                            break
                        elif event_type == 'error':
                            yield f"data: {json.dumps({'type': 'error', 'message': data}, ensure_ascii=False)}\n\n"
                            break
                    else:
                        yield f"data: {json.dumps({'type': 'progress', 'event': item.to_dict()}, ensure_ascii=False)}\n\n"
                except Exception:
                    break

        return Response(
            stream_with_context(generate_events()),
            mimetype='text/event-stream',
            headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
        )
    except Exception as e:
        current_app.logger.error(f"Agent research failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/agent/pipeline', methods=['POST'])
@require_auth
@require_usage
def agent_pipeline():
    """멀티에이전트 파이프라인을 실행합니다.

    Request body:
        topic (str): 콘텐츠 주제
        model (str): AI 모델 ID
        style_id (str): 출력 스타일 (기본 blog_seo)
        skip_research (bool): 리서치 단계 건너뛰기

    Returns:
        파이프라인 실행 결과 (순차 응답)
    """
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '').strip()
        model = data.get('model', DEFAULT_MODEL)
        style_id = data.get('style_id', 'blog_seo')
        skip_research = data.get('skip_research', False)

        if not topic:
            return api_error('콘텐츠 주제가 필요합니다.', 400)

        from services.agents.web_research_agent import ResearchAgent
        from services.agents.content_pipeline_agent import WriterAgent, EditorAgent, SeoAgent
        from services.agents.pipeline_orchestrator import AgentOrchestrator

        # 에이전트 체인 구성
        agents = []
        initial_context = {}

        if not skip_research:
            agents.append(ResearchAgent(model=model, max_sources=5))

        agents.extend([
            WriterAgent(model=model, style_id=style_id),
            EditorAgent(model=model),
            SeoAgent(model=model),
        ])

        orchestrator = AgentOrchestrator()
        result = orchestrator.run_pipeline(agents, topic, initial_context=initial_context)

        return jsonify({
            'pipeline_results': result.get('pipeline_results', []),
            'final': {
                'title': result.get('final', {}).get('title', ''),
                'content': result.get('final', {}).get('edited', result.get('final', {}).get('draft', '')),
                'seo': result.get('final', {}).get('seo', {}),
                'sources': result.get('final', {}).get('sources', []),
            },
            'elapsed_seconds': result.get('elapsed_seconds', 0),
            'agent_count': result.get('agent_count', 0),
            'quota': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Agent pipeline failed: {e}")
        return handle_error(str(e))


# === 메모리 API ===

@blog_bp.route('/api/memory', methods=['GET'])
@require_auth
def get_user_memory():
    """사용자 메모리를 조회합니다."""
    try:
        from services.data.memory_service import memory_service
        user_id = g.user_id
        memory = memory_service.get_memory(user_id)
        return jsonify({'memory': memory})
    except Exception as e:
        current_app.logger.error(f"Get memory failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/memory', methods=['PUT'])
@require_auth
def update_user_memory():
    """사용자 메모리를 업데이트합니다."""
    try:
        from services.data.memory_service import memory_service
        user_id = g.user_id
        data = request.get_json(silent=True) or {}
        key = data.get('key', '').strip()
        value = data.get('value')

        if not key:
            return api_error('메모리 키가 필요합니다.', 400)

        memory_service.update_memory(user_id, key, value)
        return jsonify({'success': True, 'memory': memory_service.get_memory(user_id)})
    except Exception as e:
        current_app.logger.error(f"Update memory failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/memory', methods=['DELETE'])
@require_auth
def clear_user_memory():
    """사용자 메모리를 초기화합니다."""
    try:
        from services.data.memory_service import memory_service
        user_id = g.user_id
        memory_service.clear(user_id)
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Clear memory failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-20: 자동 태깅
# =============================================

@blog_bp.route('/api/auto-tags', methods=['POST'])
@require_auth
def auto_tags():
    """콘텐츠에서 자동으로 태그와 카테고리를 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content:
            return api_error('태그를 추출할 콘텐츠가 필요합니다.', 400)

        from services.data.auto_tag_service import generate_tags
        result = generate_tags(content)
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Auto-tag failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-23: 콘텐츠 점수 카드
# =============================================

@blog_bp.route('/api/content-score', methods=['POST'])
@require_auth
def content_score():
    """콘텐츠 종합 점수를 계산합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')

        if not content:
            return api_error('점수를 계산할 콘텐츠가 필요합니다.', 400)

        from services.quality.quality_service import calculate_comprehensive_score
        result = calculate_comprehensive_score(content)
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Content score failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-25: 스마트 요약
# =============================================

@blog_bp.route('/api/progressive-summary', methods=['POST'])
@require_auth
@require_usage
def progressive_summary():
    """콘텐츠를 3단계 요약으로 변환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        model = data.get('model')

        if not content:
            return api_error('요약할 콘텐츠가 필요합니다.', 400)

        from services.content.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary(content, model)
        return jsonify(result)

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Progressive summary failed: {e}")
        return handle_error(str(e))


# ============================================================
# 분리된 라우트 패키지 — 부수효과 import로 자동 등록
# - routes/advanced/mindmap.py
# - routes/advanced/fusion.py
# - routes/advanced/qa.py
# ============================================================
from routes import advanced as _advanced_subroutes  # noqa: E402,F401
