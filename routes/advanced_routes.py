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
from config import get_model_max_tokens, CAMPAIGN_PACKS
from services import ai_service, content_service, fusion_service
from services.supabase_service import require_auth
from services.usage import require_usage, check_usage
from services.usage.usage_decorator import get_usage_for_response
from utils.responses import handle_error


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
            'elapsed_time': elapsed_time,
            'usage': get_usage_for_response()
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Mindmap generation failed: {e}")
        return handle_error(str(e))


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
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400
        if not styles or not isinstance(styles, list) or len(styles) < 1:
            return jsonify({'error': '최소 1개 이상의 스타일을 선택해주세요.'}), 400
        if len(styles) > 5:
            return jsonify({'error': '최대 5개 스타일까지 선택할 수 있습니다.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

        transcript_text, comments, error, raw_transcript, transcript_source, _ = _fetch_youtube_content(video_id)
        if error:
            return jsonify({'error': error}), 400

        max_tokens = get_model_max_tokens(model)
        main_content = _build_combined_content(transcript_text, comments) if comments else f"[영상 자막]\n{transcript_text}"
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        # 유효 스타일 필터링
        style_prompts_dict = current_app.config.get('STYLE_PROMPTS', {})
        valid_styles = [s for s in styles if s in style_prompts_dict]
        if not valid_styles:
            return jsonify({'error': '유효한 스타일이 없습니다.'}), 400

        # 병렬 생성
        app = current_app._get_current_object()
        results = []

        def _gen_for_style(style_id):
            with app.app_context():
                try:
                    sp = style_prompts_dict.get(style_id, '')
                    result = ai_service.create_content(
                        truncated_content, model, sp,
                        style_id=style_id
                    )
                    result['style'] = style_id
                    return result
                except Exception as e:
                    return {'style': style_id, 'error': str(e)}

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

        return jsonify({
            'success': True,
            'results': results,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'elapsed_time': elapsed_time,
            'usage': get_usage_for_response()
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Generate multi failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-campaign', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_campaign():
    """캠페인 팩으로 1 URL × N 스타일 동시 생성 (사용량 1회 차감)"""
    try:
        start_time = time.time()
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)
        pack_id = data.get('pack_id')
        modifiers = data.get('modifiers', {})

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400
        if not pack_id or pack_id not in CAMPAIGN_PACKS:
            return jsonify({'error': f'유효하지 않은 캠페인 팩: {pack_id}'}), 400

        pack = CAMPAIGN_PACKS[pack_id]
        styles = pack['styles']

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

        # YouTube 콘텐츠 1회 가져오기
        transcript_text, comments, error, raw_transcript, transcript_source, _ = _fetch_youtube_content(video_id)
        if error:
            return jsonify({'error': error}), 400

        max_tokens = get_model_max_tokens(model)
        main_content = _build_combined_content(transcript_text, comments) if comments else f"[영상 자막]\n{transcript_text}"
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        # 유효 스타일 필터링
        style_prompts_dict = current_app.config.get('STYLE_PROMPTS', {})
        valid_styles = [s for s in styles if s in style_prompts_dict]
        if not valid_styles:
            return jsonify({'error': '캠페인 팩에 유효한 스타일이 없습니다.'}), 400

        # 병렬 생성 (generate_multi 패턴 동일)
        app = current_app._get_current_object()
        results = []

        def _gen_for_style(style_id):
            with app.app_context():
                try:
                    sp = style_prompts_dict.get(style_id, '')
                    result = ai_service.create_content(
                        truncated_content, model, sp,
                        style_id=style_id, modifiers=modifiers
                    )
                    result['style'] = style_id
                    return result
                except Exception as e:
                    return {'style': style_id, 'error': str(e)}

        is_glm = model.startswith('zhipuai/')
        if is_glm:
            for style_id in valid_styles:
                results.append(_gen_for_style(style_id))
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(3, len(valid_styles))) as executor:
                futures = {executor.submit(_gen_for_style, s): s for s in valid_styles}
                for future in concurrent.futures.as_completed(futures):
                    results.append(future.result())

        # 팩 스타일 순서대로 정렬
        style_order = {s: i for i, s in enumerate(valid_styles)}
        results.sort(key=lambda r: style_order.get(r.get('style', ''), 99))

        # 전체 토큰 사용량 합산
        total_usage = {'total_tokens': 0, 'input_tokens': 0, 'output_tokens': 0}
        for r in results:
            u = r.get('usage', {})
            total_usage['total_tokens'] += u.get('total_tokens', 0)
            total_usage['input_tokens'] += u.get('input_tokens', u.get('prompt_tokens', 0))
            total_usage['output_tokens'] += u.get('output_tokens', u.get('completion_tokens', 0))

        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            'success': True,
            'pack_id': pack_id,
            'pack_name': pack['name'],
            'results': results,
            'total_usage': total_usage,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'elapsed_time': elapsed_time,
            'usage': get_usage_for_response()
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Campaign generation failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-fusion', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@check_usage
def generate_fusion():
    """퓨전 생성: N개 URL → 융합 1편"""
    data = request.get_json()
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

    try:
        result = fusion_service.generate_fusion(
            urls=urls,
            style_id=style_id,
            model=model,
            modifiers=modifiers,
            enable_web_research=enable_web_research,
            enable_deep_comments=enable_deep_comments
        )

        # 사용량 차감 (1회)
        if hasattr(g, 'usage') and g.usage:
            from services.usage import UsageService
            UsageService.decrement(g.usage.get('user_id'))

        return jsonify(result)

    except ValueError as e:
        return jsonify({'error': f'[입력 오류] {str(e)}'}), 400
    except Exception as e:
        current_app.logger.error('퓨전 생성 실패: %s', e, exc_info=True)
        return handle_error(e)


@blog_bp.route('/api/rewrite', methods=['POST'])
@require_auth
@require_usage
def rewrite_content():
    """콘텐츠를 특정 플랫폼 형식으로 변환합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        platform = data.get('platform', '')
        model = data.get('model', DEFAULT_MODEL)

        if not content:
            return jsonify({'error': '변환할 콘텐츠가 필요합니다.'}), 400
        if not platform:
            return jsonify({'error': '대상 플랫폼을 선택해주세요.'}), 400

        from services.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform(content, platform, model)

        if 'error' in result:
            return jsonify(result), 400

        return jsonify({
            **result,
            'usage': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Rewrite failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/qa-check', methods=['POST'])
def qa_check():
    """콘텐츠 QA 검증을 실행합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        rules = data.get('rules')

        if not content:
            return jsonify({'error': '검증할 콘텐츠가 필요합니다.'}), 400

        from services.qa_gate_service import check_quality
        result = check_quality(content, rules)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"QA check failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/pipeline', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
def run_pipeline():
    """파이프라인 실행 SSE 엔드포인트.

    요청: { pipeline_id, url, model, style, modifiers }
    응답: text/event-stream (각 스텝 진행률 이벤트)
    """
    from services.pipeline_service import PipelineEngine, PIPELINE_PRESETS
    from services.usage.usage_service import UsageService
    from services.supabase_service import is_supabase_enabled

    try:
        params = _get_request_data(request)
        data = request.get_json(silent=True) or {}
        pipeline_id = data.get('pipeline_id', 'blog_automation')

        if pipeline_id not in PIPELINE_PRESETS:
            return jsonify({'error': f'알 수 없는 파이프라인: {pipeline_id}'}), 400

        url = params['url']
        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

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
            return jsonify({'error': '콘텐츠와 선택 영역이 필요합니다.'}), 400
        if not instruction:
            return jsonify({'error': '편집 지시가 필요합니다.'}), 400

        result = ai_service.inline_edit(content, selection, instruction, model)
        return jsonify({
            **result,
            'usage': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Inline edit failed: {e}")
        return handle_error(str(e))
