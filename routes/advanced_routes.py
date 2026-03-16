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
from services.core import ai_service, content_service
from services.data.supabase_service import require_auth
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response
from utils.responses import handle_error, api_error_from_exception, sanitize_error_for_client


def _sanitize_generation_error(error: Exception | str, fallback_message: str) -> str:
    """중첩 결과/SSE 응답에 들어가는 예외 메시지를 정리합니다."""
    safe_message = sanitize_error_for_client(str(error or ''))
    if safe_message.startswith('[서버 오류]'):
        return fallback_message
    return safe_message


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
            'quota': get_usage_for_response()
        })

    except ValueError as e:
        return handle_error(str(e))
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
                style_start = time.time()
                try:
                    sp = style_prompts_dict.get(style_id, '')
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
                        'error': _sanitize_generation_error(
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
                    style_start = time.time()
                    sp = style_prompts_dict.get(style_id, '')
                    result = ai_service.create_content(
                        truncated_content, model, sp,
                        style_id=style_id, modifiers=modifiers
                    )
                    result['style'] = style_id
                    result['elapsed_time'] = round(time.time() - style_start, 2)
                    return result
                except Exception as e:
                    return {
                        'style': style_id,
                        'error': _sanitize_generation_error(
                            e,
                            '[서버 오류] 캠페인 스타일 생성 중 문제가 발생했습니다.'
                        )
                    }

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

        total_elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            'success': True,
            'pack_id': pack_id,
            'pack_name': pack['name'],
            'results': results,
            'total_usage': total_usage,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'elapsed_time': total_elapsed_time,
            'total_elapsed_time': total_elapsed_time,
            'quota': get_usage_for_response()
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Campaign generation failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-fusion', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
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
        })
    return jsonify({'available_platforms': platforms})


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

        from services.content.rewrite_service import rewrite_for_platform
        result = rewrite_for_platform(content, platform, model)

        if 'error' in result:
            safe_result = dict(result)
            safe_result['error'] = _sanitize_generation_error(
                result.get('error'),
                '[서버 오류] 콘텐츠 변환 중 문제가 발생했습니다.'
            )
            return jsonify(safe_result), 400

        return jsonify({
            **result,
            'quota': get_usage_for_response(),
        })
    except Exception as e:
        current_app.logger.error(f"Rewrite failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/qa-check', methods=['POST'])
def qa_check():
    """콘텐츠 QA 검증을 실행합니다."""
    try:
        import time as _time
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        rules = data.get('rules')

        if not content:
            return jsonify({'error': '검증할 콘텐츠가 필요합니다.'}), 400

        from services.quality.qa_gate_service import check_quality
        t0 = _time.monotonic()
        result = check_quality(content, rules)
        result['check_duration_ms'] = round((_time.monotonic() - t0) * 1000, 1)
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
    from services.core.pipeline_service import PipelineEngine, PIPELINE_PRESETS
    from services.usage.usage_service import UsageService
    from services.data.supabase_service import is_supabase_enabled

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


@blog_bp.route('/api/channel-analysis', methods=['POST'])
@require_auth
def channel_analysis():
    """YouTube 채널 전체 분석 (영상 목록, 주제 클러스터, 통계)"""
    try:
        data = request.get_json(silent=True) or {}
        channel_url = data.get('url', '').strip()

        if not channel_url:
            return jsonify({'error': '채널 URL이 필요합니다.'}), 400

        from services.content.channel_analysis_service import analyze_channel
        result = analyze_channel(channel_url)
        return jsonify({'success': True, **result})

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Channel analysis failed: {e}")
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
            return jsonify({'error': '제목이 필요합니다.'}), 400

        from services.media.thumbnail_service import generate_thumbnail as _gen_thumb
        result = _gen_thumb(title, keywords, size)

        if not result.get('success'):
            return jsonify({
                'error': _sanitize_generation_error(
                    result.get('error', '썸네일 생성 실패'),
                    '[서버 오류] 썸네일 생성 중 문제가 발생했습니다.'
                )
            }), 400

        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Thumbnail generation failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-clips', methods=['POST'])
@limiter.limit("3/minute")
@require_auth
@require_usage
def generate_clips():
    """YouTube 영상에서 Shorts 클립을 추출합니다."""
    try:
        data = request.get_json(silent=True) or {}
        video_url = data.get('url', '')
        clips = data.get('clips', [])

        if not video_url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not clips:
            return jsonify({'error': '추출할 클립 목록이 필요합니다.'}), 400

        from services.media.video_clip_service import extract_clips
        clip_paths = extract_clips(video_url, clips)

        import base64
        results = []
        for i, path in enumerate(clip_paths):
            with open(path, 'rb') as f:
                video_b64 = base64.b64encode(f.read()).decode('ascii')
            results.append({
                'index': i,
                'video_base64': video_b64,
                'start': clips[i].get('start', ''),
                'end': clips[i].get('end', ''),
            })

        from services.media.video_clip_service import cleanup_clips
        cleanup_clips(clip_paths)

        return jsonify({
            'success': True,
            'clips': results,
            'quota': get_usage_for_response(),
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Clip extraction failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-podcast', methods=['POST'])
@limiter.limit("3/minute")
@require_auth
@require_usage
def generate_podcast():
    """콘텐츠로 팟캐스트 에피소드를 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        title = data.get('title', '팟캐스트 에피소드')
        model = data.get('model', DEFAULT_MODEL)

        if not content:
            return jsonify({'error': '팟캐스트로 변환할 콘텐츠가 필요합니다.'}), 400

        from services.media.podcast_service import generate_podcast_episode
        result = generate_podcast_episode(content, title, model)

        return jsonify({
            'success': True,
            **result,
            'quota': get_usage_for_response(),
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Podcast generation failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/generate-multilang', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_multilang():
    """한/영/일 3개 언어로 동시 생성합니다."""
    try:
        start_time = time.time()
        data = request.get_json(silent=True) or {}
        url = data.get('url')
        model = data.get('model', DEFAULT_MODEL)
        style = data.get('style', 'blog_seo')
        languages = data.get('languages', ['ko', 'en', 'ja'])

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

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

        style_prompts_dict = current_app.config.get('STYLE_PROMPTS', {})
        sp = style_prompts_dict.get(style, '')
        if not sp:
            return jsonify({'error': f'유효하지 않은 스타일: {style}'}), 400

        app = current_app._get_current_object()
        results = {}

        def _gen_for_lang(lang):
            with app.app_context():
                try:
                    modifiers = {'language': lang}
                    result = ai_service.create_content(
                        truncated_content, model, sp,
                        style_id=style, modifiers=modifiers,
                    )
                    result['language'] = lang
                    return lang, result
                except Exception as e:
                    return lang, {
                        'language': lang,
                        'error': _sanitize_generation_error(
                            e,
                            '[서버 오류] 다국어 콘텐츠 생성 중 문제가 발생했습니다.'
                        )
                    }

        is_glm = model.startswith('zhipuai/')
        if is_glm:
            for lang in languages:
                l, r = _gen_for_lang(lang)
                results[l] = r
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = {executor.submit(_gen_for_lang, lang): lang for lang in languages}
                for future in concurrent.futures.as_completed(futures):
                    lang, result = future.result()
                    results[lang] = result

        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            'success': True,
            'results': results,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'elapsed_time': elapsed_time,
            'quota': get_usage_for_response(),
        })

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Multilang generation failed: {e}")
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
        max_sources = min(int(data.get('max_sources', 5)), 10)

        if not topic:
            return jsonify({'error': '리서치 주제가 필요합니다.'}), 400

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
                        _sanitize_generation_error(
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
            return jsonify({'error': '콘텐츠 주제가 필요합니다.'}), 400

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
            return jsonify({'error': '메모리 키가 필요합니다.'}), 400

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
            return jsonify({'error': '태그를 추출할 콘텐츠가 필요합니다.'}), 400

        from services.data.auto_tag_service import generate_tags
        result = generate_tags(content)
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Auto-tag failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-21: 콘텐츠 브리프 생성
# =============================================

@blog_bp.route('/api/content-brief', methods=['POST'])
@require_auth
@require_usage
def content_brief():
    """주제에 대한 콘텐츠 브리프를 생성합니다."""
    try:
        data = request.get_json(silent=True) or {}
        topic = data.get('topic', '')
        keywords = data.get('keywords')

        if not topic:
            return jsonify({'error': '주제를 입력해주세요.'}), 400

        from services.content.brief_service import generate_brief
        result = generate_brief(topic, keywords)
        return jsonify(result)

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Content brief failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-22: 경쟁 콘텐츠 분석
# =============================================

@blog_bp.route('/api/competitor-analysis', methods=['POST'])
@require_auth
def competitor_analysis():
    """키워드로 경쟁 콘텐츠를 분석합니다."""
    try:
        data = request.get_json(silent=True) or {}
        keyword = data.get('keyword', '')
        my_content = data.get('my_content')

        if not keyword:
            return jsonify({'error': '분석할 키워드를 입력해주세요.'}), 400

        from services.seo.competitor_analysis_service import analyze_competitors
        result = analyze_competitors(keyword, my_content)
        return jsonify(result)

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Competitor analysis failed: {e}")
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
            return jsonify({'error': '점수를 계산할 콘텐츠가 필요합니다.'}), 400

        from services.quality.quality_service import calculate_comprehensive_score
        result = calculate_comprehensive_score(content)
        return jsonify(result)

    except Exception as e:
        current_app.logger.error(f"Content score failed: {e}")
        return handle_error(str(e))


# =============================================
# F3-24: AI 코멘터리
# =============================================

@blog_bp.route('/api/commentary', methods=['POST'])
@require_auth
@require_usage
def add_commentary():
    """콘텐츠에 AI 해설 주석을 추가합니다."""
    try:
        data = request.get_json(silent=True) or {}
        content = data.get('content', '')
        model = data.get('model')

        if not content:
            return jsonify({'error': '해설을 추가할 콘텐츠가 필요합니다.'}), 400

        from services.content.commentary_service import add_commentary as _add_commentary
        result = _add_commentary(content, model)
        return jsonify(result)

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Commentary failed: {e}")
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
            return jsonify({'error': '요약할 콘텐츠가 필요합니다.'}), 400

        from services.content.progressive_summary_service import generate_progressive_summary
        result = generate_progressive_summary(content, model)
        return jsonify(result)

    except ValueError as e:
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Progressive summary failed: {e}")
        return handle_error(str(e))


# =============================================
# 파인튜닝 데이터 수집 API (F10-15)
# =============================================

@blog_bp.route('/api/finetune/collect', methods=['POST'])
@require_auth
def finetune_collect():
    """Supabase 히스토리에서 학습 데이터 수집"""
    from services.finetune.data_collector import AutoDataCollector

    data = request.get_json(silent=True) or {}
    days_back = min(int(data.get('days_back', 30)), 365)
    limit = min(int(data.get('limit', 1000)), 5000)

    try:
        collector = AutoDataCollector(
            output_dir=data.get('output_dir', './data/finetune'),
            min_quality_score=float(data.get('min_quality_score', 0.6)),
            min_content_length=int(data.get('min_content_length', 500)),
        )
        result = collector.collect_from_supabase(days_back=days_back, limit=limit)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        return jsonify({'success': True, **result})
    except Exception as e:
        current_app.logger.error(f"Finetune collect failed: {e}")
        return handle_error(str(e))


@blog_bp.route('/api/finetune/collect-local', methods=['POST'])
@require_auth
def finetune_collect_local():
    """로컬 SQLite 캐시에서 학습 데이터 수집"""
    from services.finetune.data_collector import AutoDataCollector

    data = request.get_json(silent=True) or {}
    cache_db_path = data.get('cache_db_path', '')
    if not cache_db_path:
        return jsonify({'error': '캐시 DB 경로가 필요합니다.'}), 400

    try:
        collector = AutoDataCollector(
            output_dir=data.get('output_dir', './data/finetune'),
            min_quality_score=float(data.get('min_quality_score', 0.6)),
            min_content_length=int(data.get('min_content_length', 500)),
        )
        result = collector.collect_from_local_cache(cache_db_path)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        return jsonify({'success': True, **result})
    except Exception as e:
        current_app.logger.error(f"Finetune collect-local failed: {e}")
        return handle_error(str(e))
