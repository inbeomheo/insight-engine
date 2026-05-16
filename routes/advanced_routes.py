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
from utils.responses import handle_error, sanitize_error_for_client, sanitize_path, clamp_query_int, validate_content_length


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
            return jsonify({'error': '변환할 콘텐츠가 필요합니다.'}), 400
        length_error = validate_content_length(content)
        if length_error:
            return jsonify({'error': length_error}), 400
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

        elapsed_time = round(time.time() - start_time, 2)

        return jsonify({
            **result,
            'elapsed_time': elapsed_time,
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

        succeeded = sum(1 for r in results.values() if 'error' not in r)
        failed = len(results) - succeeded

        return jsonify({
            'success': True,
            'results': results,
            'youtube_title': youtube_title,
            'transcript_source': transcript_source,
            'language_count': len(results),
            'succeeded': succeeded,
            'failed': failed,
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
        length_error = validate_content_length(content)
        if length_error:
            return jsonify({'error': length_error}), 400
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
        max_sources = clamp_query_int(data.get('max_sources'), default=5, min_val=1, max_val=10)

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
    days_back = clamp_query_int(data.get('days_back'), default=30, min_val=1, max_val=365)
    limit = clamp_query_int(data.get('limit'), default=1000, min_val=1, max_val=5000)

    # 경로 순회 방어: output_dir을 허용 범위 내로 제한
    try:
        safe_output_dir = sanitize_path(
            data.get('output_dir', 'finetune'), './data'
        )
    except ValueError:
        return jsonify({'error': '출력 경로가 허용 범위를 벗어났습니다.'}), 400

    try:
        collector = AutoDataCollector(
            output_dir=safe_output_dir,
            min_quality_score=float(data.get('min_quality_score', 0.6)),
            min_content_length=clamp_query_int(data.get('min_content_length'), default=500, min_val=50, max_val=100000),
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

    # 경로 순회 방어: cache_db_path와 output_dir을 허용 범위 내로 제한
    try:
        safe_cache_path = sanitize_path(cache_db_path, './data')
    except ValueError:
        return jsonify({'error': '캐시 DB 경로가 허용 범위를 벗어났습니다.'}), 400

    try:
        safe_output_dir = sanitize_path(
            data.get('output_dir', 'finetune'), './data'
        )
    except ValueError:
        return jsonify({'error': '출력 경로가 허용 범위를 벗어났습니다.'}), 400

    try:
        collector = AutoDataCollector(
            output_dir=safe_output_dir,
            min_quality_score=float(data.get('min_quality_score', 0.6)),
            min_content_length=clamp_query_int(data.get('min_content_length'), default=500, min_val=50, max_val=100000),
        )
        result = collector.collect_from_local_cache(safe_cache_path)

        if 'error' in result:
            return jsonify({'error': result['error']}), 400

        return jsonify({'success': True, **result})
    except Exception as e:
        current_app.logger.error(f"Finetune collect-local failed: {e}")
        return handle_error(str(e))


# === 톤 분석 및 조정 ===

@blog_bp.route('/api/tone/analyze', methods=['POST'])
@require_auth
def analyze_tone():
    """콘텐츠의 현재 톤을 분석합니다."""
    from services.content.tone_adjuster_service import analyze_tone as _analyze

    data = _get_request_data()
    content = data.get('content', '')
    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _analyze(content)
    return jsonify(result)


@blog_bp.route('/api/tone/adjust', methods=['POST'])
@require_auth
@require_usage
def adjust_tone():
    """콘텐츠를 목표 톤으로 변환합니다."""
    from services.content.tone_adjuster_service import adjust_tone as _adjust, SUPPORTED_TONES

    data = _get_request_data()
    content = data.get('content', '')
    target_tone = data.get('target_tone', '')
    model = data.get('model', DEFAULT_MODEL)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400
    if not target_tone:
        return jsonify({'error': f'target_tone이 필요합니다. 지원: {SUPPORTED_TONES}'}), 400

    result = _adjust(content, target_tone, model)
    if 'error' in result:
        return jsonify({'error': result['error']}), 400

    usage = get_usage_for_response()
    return jsonify({**result, 'usage': usage})


@blog_bp.route('/api/tone/list')
def list_tones():
    """지원하는 톤 목록을 반환합니다."""
    from services.content.tone_adjuster_service import get_tone_list
    return jsonify({'tones': get_tone_list()})


# === 핵심 요약 추출 ===

@blog_bp.route('/api/extract-takeaways', methods=['POST'])
@require_auth
def extract_takeaways():
    """콘텐츠에서 핵심 요약 포인트를 추출합니다."""
    from services.content.takeaway_extractor_service import extract_takeaways as _extract

    data = _get_request_data()
    content = data.get('content', '')
    count = clamp_query_int(data.get('count'), default=5, min_val=1, max_val=10)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _extract(content, count)
    return jsonify(result)


# === 일괄 플랫폼 리라이트 ===

@blog_bp.route('/api/rewrite/batch', methods=['POST'])
@require_auth
@require_usage
def batch_rewrite():
    """콘텐츠를 여러 플랫폼으로 동시 변환합니다."""
    from services.content.batch_rewrite_service import batch_rewrite as _batch, get_available_platforms, get_platform_groups

    data = _get_request_data()
    content = data.get('content', '')
    platforms = data.get('platforms', [])
    model = data.get('model', DEFAULT_MODEL)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400
    if not platforms:
        return jsonify({'error': '플랫폼을 지정해주세요.', 'available': get_available_platforms(), 'groups': get_platform_groups()}), 400

    result = _batch(content, platforms, model)
    if 'error' in result:
        return jsonify({'error': result['error']}), 400

    usage = get_usage_for_response()
    return jsonify({**result, 'usage': usage})


@blog_bp.route('/api/rewrite/platform-groups')
def list_platforms_extended():
    """지원 플랫폼 및 그룹 프리셋을 반환합니다."""
    from services.content.batch_rewrite_service import get_available_platforms, get_platform_groups
    return jsonify({
        'platforms': get_available_platforms(),
        'groups': get_platform_groups(),
    })


# === 콘텐츠 비교 ===

@blog_bp.route('/api/content/diff', methods=['POST'])
@require_auth
def content_diff():
    """두 콘텐츠 버전을 비교합니다."""
    from services.content.content_diff_service import compare_content, generate_unified_diff

    data = _get_request_data()
    original = data.get('original', '')
    revised = data.get('revised', '')
    include_unified = data.get('include_unified', False)

    if not original and not revised:
        return jsonify({'error': '비교할 콘텐츠가 필요합니다.'}), 400

    result = compare_content(original, revised)
    if include_unified:
        result['unified_diff'] = generate_unified_diff(original, revised)

    return jsonify(result)


# === 콘텐츠 병합 ===

@blog_bp.route('/api/content/merge', methods=['POST'])
@require_auth
def content_merge():
    """여러 콘텐츠를 하나로 병합합니다."""
    from services.content.content_merge_service import merge_contents

    data = _get_request_data()
    contents = data.get('contents', [])
    deduplicate = data.get('deduplicate', True)

    if not contents or not isinstance(contents, list):
        return jsonify({'error': 'contents 배열이 필요합니다.'}), 400
    if len(contents) < 2:
        return jsonify({'error': '최소 2개 콘텐츠가 필요합니다.'}), 400

    result = merge_contents(contents, deduplicate=deduplicate)
    return jsonify(result)


# === 가독성 분석 ===

@blog_bp.route('/api/content/readability', methods=['POST'])
@require_auth
def analyze_readability():
    """콘텐츠의 가독성을 분석하고 개선 제안을 반환합니다."""
    from services.content.readability_optimizer_service import analyze_readability as _analyze

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _analyze(content)
    return jsonify(result)


@blog_bp.route('/api/content/readability/levels')
def readability_levels():
    """지원하는 가독성 수준 목록을 반환합니다."""
    from services.content.readability_optimizer_service import get_readability_levels
    return jsonify({'levels': get_readability_levels()})


# === 해시태그 생성 ===

@blog_bp.route('/api/content/hashtags', methods=['POST'])
@require_auth
def generate_hashtags():
    """콘텐츠에서 해시태그를 생성합니다."""
    from services.content.hashtag_generator_service import generate_hashtags as _gen

    data = _get_request_data()
    content = data.get('content', '')
    count = clamp_query_int(data.get('count'), default=10, min_val=1, max_val=30)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _gen(content, count=count)
    return jsonify(result)


# === 스니펫 생성 ===

@blog_bp.route('/api/content/snippet', methods=['POST'])
@require_auth
def generate_snippet():
    """콘텐츠에서 스니펫(발췌문)을 생성합니다."""
    from services.content.snippet_generator_service import generate_snippet as _gen, generate_multi_snippets

    data = _get_request_data()
    content = data.get('content', '')
    preset = data.get('preset', 'meta')
    multi = data.get('multi', False)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    if multi:
        result = generate_multi_snippets(content)
    else:
        max_chars = clamp_query_int(data.get('max_chars'), default=0, min_val=0, max_val=1000)
        result = _gen(content, preset=preset, max_chars=max_chars)

    return jsonify(result)


@blog_bp.route('/api/content/snippet/presets')
def snippet_presets():
    """스니펫 프리셋 목록을 반환합니다."""
    from services.content.snippet_generator_service import get_snippet_presets
    return jsonify({'presets': get_snippet_presets()})


# === 구조 분석 ===

@blog_bp.route('/api/content/structure', methods=['POST'])
@require_auth
def analyze_structure():
    """마크다운 콘텐츠의 구조를 분석합니다."""
    from services.content.structure_analyzer_service import analyze_structure as _analyze

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _analyze(content)
    return jsonify(result)


# === 발행 체크리스트 ===

@blog_bp.route('/api/content/checklist', methods=['POST'])
@require_auth
def publish_checklist():
    """발행 전 체크리스트를 생성합니다."""
    from services.content.publish_checklist_service import generate_checklist

    data = _get_request_data()
    content = data.get('content', '')
    title = data.get('title', '')
    has_meta = bool(data.get('has_meta', False))
    has_hashtags = bool(data.get('has_hashtags', False))
    has_thumbnail = bool(data.get('has_thumbnail', False))

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = generate_checklist(content, title=title, has_meta=has_meta,
                                has_hashtags=has_hashtags, has_thumbnail=has_thumbnail)
    return jsonify(result)


# === 통계 집계 ===

@blog_bp.route('/api/content/stats/aggregate', methods=['POST'])
@require_auth
def aggregate_content_stats():
    """여러 콘텐츠의 통계를 집계합니다."""
    from services.content.stats_aggregator_service import aggregate_stats

    data = _get_request_data()
    contents = data.get('contents', [])

    if not contents or not isinstance(contents, list):
        return jsonify({'error': 'contents 배열이 필요합니다.'}), 400

    result = aggregate_stats(contents)
    return jsonify(result)


# === 용어집 추출 ===

@blog_bp.route('/api/content/glossary', methods=['POST'])
@require_auth
def extract_glossary():
    """콘텐츠에서 전문 용어와 정의를 추출합니다."""
    from services.content.glossary_extractor_service import extract_glossary as _extract

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _extract(content)
    return jsonify(result)


# === 마크다운 정리 ===

@blog_bp.route('/api/content/sanitize', methods=['POST'])
@require_auth
def sanitize_markdown():
    """마크다운을 자동 정리합니다."""
    from services.content.markdown_sanitizer_service import sanitize_markdown as _sanitize

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _sanitize(content)
    return jsonify(result)


# === 순수 텍스트 변환 ===

@blog_bp.route('/api/content/plaintext', methods=['POST'])
@require_auth
def convert_plaintext():
    """마크다운을 순수 텍스트로 변환합니다."""
    from services.content.plaintext_converter_service import convert_to_plaintext

    data = _get_request_data()
    content = data.get('content', '')
    preserve = data.get('preserve_structure', True)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = convert_to_plaintext(content, preserve_structure=preserve)
    return jsonify(result)


# === A/B 변형 생성 ===

@blog_bp.route('/api/content/ab-variants', methods=['POST'])
@require_auth
def generate_ab_variants():
    """A/B 테스트 변형을 생성합니다."""
    from services.content.ab_variant_service import generate_variants

    data = _get_request_data()
    content = data.get('content', '')
    title = data.get('title', '')
    variant_types = data.get('variant_types', None)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = generate_variants(content, title=title, variant_types=variant_types)
    return jsonify(result)


# === 워터마크 ===

@blog_bp.route('/api/content/watermark', methods=['POST'])
@require_auth
def add_watermark():
    """콘텐츠에 보이지 않는 워터마크를 삽입합니다."""
    from services.content.watermark_service import add_invisible_watermark, add_attribution

    data = _get_request_data()
    content = data.get('content', '')
    mode = data.get('mode', 'invisible')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    if mode == 'attribution':
        result = add_attribution(content, author=data.get('author', ''),
                                  source_url=data.get('source_url', ''),
                                  license_text=data.get('license_text', ''))
    else:
        result = add_invisible_watermark(content, identifier=data.get('identifier', ''))

    return jsonify(result)


@blog_bp.route('/api/content/watermark/detect', methods=['POST'])
@require_auth
def detect_watermark():
    """콘텐츠에서 워터마크를 탐지합니다."""
    from services.content.watermark_service import detect_watermark as _detect

    data = _get_request_data()
    content = data.get('content', '')

    if not content:
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _detect(content)
    return jsonify(result)


# === 단어 반복 감지 ===

@blog_bp.route('/api/content/repetitions', methods=['POST'])
@require_auth
def detect_word_repetitions():
    """과다 반복 단어를 감지합니다."""
    from services.content.word_repetition_service import detect_repetitions

    data = _get_request_data()
    content = data.get('content', '')
    threshold = clamp_query_int(data.get('threshold'), default=3, min_val=2, max_val=20)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = detect_repetitions(content, threshold=threshold)
    return jsonify(result)


# === 유사도 측정 ===

@blog_bp.route('/api/content/similarity', methods=['POST'])
@require_auth
def content_similarity():
    """두 콘텐츠의 유사도를 측정합니다."""
    from services.content.similarity_scorer_service import score_similarity

    data = _get_request_data()
    content_a = data.get('content_a', '')
    content_b = data.get('content_b', '')

    if not content_a or not content_b:
        return jsonify({'error': 'content_a와 content_b가 모두 필요합니다.'}), 400

    result = score_similarity(content_a, content_b)
    return jsonify(result)


# === 링크 추출 ===

@blog_bp.route('/api/content/links', methods=['POST'])
@require_auth
def extract_links():
    """콘텐츠에서 모든 링크를 추출합니다."""
    from services.content.link_extractor_service import extract_links as _extract

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _extract(content)
    return jsonify(result)


# === 마크다운→HTML 변환 ===

@blog_bp.route('/api/content/to-html', methods=['POST'])
@require_auth
def convert_md_to_html():
    """마크다운을 HTML로 변환합니다."""
    from services.content.md_to_html_service import convert_to_html

    data = _get_request_data()
    content = data.get('content', '')
    title = data.get('title', '')
    standalone = data.get('standalone', True)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = convert_to_html(content, title=title, standalone=standalone)
    return jsonify(result)


# === 주석 관리 ===

@blog_bp.route('/api/content/annotations', methods=['POST'])
@require_auth
def manage_annotations():
    """콘텐츠 주석을 관리합니다 (추가/추출/제거)."""
    from services.content.annotation_service import (
        add_annotation as _add, extract_annotations as _extract,
        remove_annotations as _remove,
    )

    data = _get_request_data()
    action = data.get('action', 'extract')
    content = data.get('content', '')

    if not content:
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    if action == 'add':
        position = int(data.get('position', -1))
        ann_type = data.get('type', 'note')
        text = data.get('text', '')
        if not text:
            return jsonify({'error': '주석 내용(text)이 필요합니다.'}), 400
        result = _add(content, position, ann_type, text)
    elif action == 'remove':
        ann_type = data.get('type', '')
        result = _remove(content, annotation_type=ann_type)
    else:
        result = _extract(content)

    return jsonify(result)


# === 콘텐츠 분할 ===

@blog_bp.route('/api/content/split', methods=['POST'])
@require_auth
def split_content():
    """콘텐츠를 파트로 분할합니다."""
    from services.content.content_splitter_service import split_by_headings, split_by_length

    data = _get_request_data()
    content = data.get('content', '')
    mode = data.get('mode', 'headings')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    if mode == 'length':
        max_chars = clamp_query_int(data.get('max_chars'), default=2000, min_val=500, max_val=10000)
        result = split_by_length(content, max_chars=max_chars)
    else:
        split_level = clamp_query_int(data.get('split_level'), default=2, min_val=1, max_val=3)
        result = split_by_headings(content, split_level=split_level)

    return jsonify(result)


# === 텍스트 정리 ===

@blog_bp.route('/api/content/clean', methods=['POST'])
@require_auth
def clean_text():
    """텍스트 아티팩트를 자동 정리합니다."""
    from services.content.text_cleaner_service import clean_text as _clean

    data = _get_request_data()
    content = data.get('content', '')
    options = data.get('options', None)

    if not content:
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _clean(content, options=options)
    return jsonify(result)


# === 메타데이터 추출 ===

@blog_bp.route('/api/content/metadata', methods=['POST'])
@require_auth
def extract_metadata():
    """콘텐츠에서 메타데이터를 자동 추출합니다."""
    from services.content.metadata_extractor_service import extract_metadata as _extract

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = _extract(content)
    return jsonify(result)


# === RSS 피드 생성 ===

@blog_bp.route('/api/content/rss', methods=['POST'])
@require_auth
def generate_rss_feed():
    """콘텐츠 컬렉션으로 RSS/Atom 피드를 생성합니다."""
    from services.content.rss_feed_generator_service import generate_rss

    data = _get_request_data()
    contents = data.get('contents', [])
    feed_title = data.get('feed_title', 'Insight Engine Feed')
    feed_link = data.get('feed_link', '')
    format_type = data.get('format', 'rss')

    if not contents or not isinstance(contents, list):
        return jsonify({'error': 'contents 배열이 필요합니다.'}), 400

    result = generate_rss(contents, feed_title=feed_title,
                          feed_link=feed_link, format_type=format_type)
    return jsonify(result)


# === 소셜 카드 생성 ===

@blog_bp.route('/api/content/social-card', methods=['POST'])
@require_auth
def generate_social_card():
    """Open Graph + Twitter Card 메타태그를 생성합니다."""
    from services.content.social_card_service import generate_social_card as _gen

    data = _get_request_data()
    content = data.get('content', '')
    title = data.get('title', '')
    url = data.get('url', '')
    image_url = data.get('image_url', '')
    preset = data.get('preset', 'default')

    if not content and not title:
        return jsonify({'error': '콘텐츠 또는 제목이 필요합니다.'}), 400

    result = _gen(content, title=title, url=url, image_url=image_url, preset=preset)
    return jsonify(result)


# === 검색 인덱스 ===

@blog_bp.route('/api/content/search', methods=['POST'])
@require_auth
def content_search():
    """콘텐츠 컬렉션을 인덱싱하고 검색합니다."""
    from services.content.search_index_service import build_index, search

    data = _get_request_data()
    contents = data.get('contents', [])
    query = data.get('query', '')

    if not contents or not isinstance(contents, list):
        return jsonify({'error': 'contents 배열이 필요합니다.'}), 400
    if not query or not query.strip():
        return jsonify({'error': '검색어(query)가 필요합니다.'}), 400

    max_results = clamp_query_int(data.get('max_results'), default=10, min_val=1, max_val=50)
    index = build_index(contents)
    result = search(index, query, max_results=max_results)
    return jsonify(result)


# === 변경 로그 ===

@blog_bp.route('/api/content/changelog', methods=['POST'])
@require_auth
def generate_changelog():
    """변경 이력으로 변경 로그를 생성합니다."""
    from services.content.changelog_generator_service import generate_changelog as _gen

    data = _get_request_data()
    entries = data.get('entries', [])
    title = data.get('title', '변경 이력')

    if not entries or not isinstance(entries, list):
        return jsonify({'error': 'entries 배열이 필요합니다.'}), 400

    result = _gen(entries, title=title)
    return jsonify(result)


# === 콘텐츠 템플릿 ===

@blog_bp.route('/api/content/templates', methods=['GET'])
@require_auth
def get_content_templates():
    """빌트인 콘텐츠 템플릿 목록을 반환합니다."""
    from services.content.content_template_service import list_templates
    return jsonify({'templates': list_templates()})


@blog_bp.route('/api/content/templates/apply', methods=['POST'])
@require_auth
def apply_content_template():
    """템플릿을 적용하여 마크다운 스켈레톤을 생성합니다."""
    from services.content.content_template_service import apply_template

    data = _get_request_data()
    template_id = data.get('template_id', '')
    custom_sections = data.get('custom_sections', None)
    placeholders = data.get('placeholders', {})

    result = apply_template(template_id=template_id, custom_sections=custom_sections,
                             placeholders=placeholders)
    if not result['markdown']:
        return jsonify({'error': 'template_id 또는 custom_sections가 필요합니다.'}), 400

    return jsonify(result)


@blog_bp.route('/api/content/templates/extract', methods=['POST'])
@require_auth
def extract_content_template():
    """콘텐츠에서 구조 템플릿을 추출합니다."""
    from services.content.content_template_service import extract_template

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = extract_template(content, template_name=data.get('template_name', ''))
    return jsonify(result)


# === 내보내기 번들 ===

@blog_bp.route('/api/content/export-bundle', methods=['POST'])
@require_auth
def create_export_bundle():
    """콘텐츠를 내보내기 번들로 패키징합니다."""
    from services.content.export_bundle_service import create_bundle

    data = _get_request_data()
    contents = data.get('contents', [])
    bundle_name = data.get('bundle_name', '')

    if not contents or not isinstance(contents, list):
        return jsonify({'error': 'contents 배열이 필요합니다.'}), 400

    result = create_bundle(contents, bundle_name=bundle_name)
    return jsonify(result)


@blog_bp.route('/api/content/export-bundle/validate', methods=['POST'])
@require_auth
def validate_export_bundle():
    """번들 JSON의 유효성을 검증합니다."""
    from services.content.export_bundle_service import validate_bundle

    data = _get_request_data()
    bundle_json = data.get('bundle_json', '')

    if not bundle_json:
        return jsonify({'error': 'bundle_json이 필요합니다.'}), 400

    result = validate_bundle(bundle_json)
    return jsonify(result)


# === 감성 타임라인 ===

@blog_bp.route('/api/content/sentiment-timeline', methods=['POST'])
@require_auth
def sentiment_timeline():
    """콘텐츠의 감성 타임라인을 분석합니다."""
    from services.content.sentiment_timeline_service import analyze_sentiment_timeline

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = analyze_sentiment_timeline(content)
    return jsonify(result)


# === 참고문헌 포맷팅 ===

@blog_bp.route('/api/content/citations', methods=['POST'])
@require_auth
def format_citations():
    """참고문헌을 지정 스타일로 포맷팅합니다."""
    from services.content.citation_formatter_service import format_citation, format_bibliography

    data = _get_request_data()
    sources = data.get('sources', [])
    source = data.get('source', None)
    style = data.get('style', 'apa')

    if source:
        result = format_citation(source, style=style)
    elif sources:
        result = format_bibliography(sources, style=style)
    else:
        return jsonify({'error': 'source 또는 sources가 필요합니다.'}), 400

    return jsonify(result)


@blog_bp.route('/api/content/citations/styles')
def citation_styles():
    """지원하는 인용 스타일 목록."""
    from services.content.citation_formatter_service import get_citation_styles
    return jsonify({'styles': get_citation_styles()})


# === 진행률 추적 ===

@blog_bp.route('/api/content/progress', methods=['POST'])
@require_auth
def track_content_progress():
    """콘텐츠 작성 진행률을 추적합니다."""
    from services.content.progress_tracker_service import track_progress

    data = _get_request_data()
    content = data.get('content', '')
    goals = data.get('goals', {})

    if not content:
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = track_progress(content, goals=goals)
    return jsonify(result)


# === 접근성 검사 ===

@blog_bp.route('/api/content/accessibility', methods=['POST'])
@require_auth
def check_content_accessibility():
    """콘텐츠의 접근성을 검사합니다."""
    from services.content.accessibility_checker_service import check_accessibility

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = check_accessibility(content)
    return jsonify(result)


# === 현지화 검사 ===

@blog_bp.route('/api/content/localization', methods=['POST'])
@require_auth
def check_content_localization():
    """콘텐츠의 현지화 준비도를 검사합니다."""
    from services.content.localization_checker_service import check_localization

    data = _get_request_data()
    content = data.get('content', '')
    target_locales = data.get('target_locales', [])

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    result = check_localization(content, target_locales=target_locales)
    return jsonify(result)


# === 발행 시간 추천 ===

@blog_bp.route('/api/content/publish-time', methods=['POST'])
@require_auth
def suggest_publish_time_route():
    """콘텐츠 유형별 최적 발행 시간을 추천합니다."""
    from services.content.publish_time_service import suggest_publish_time

    data = _get_request_data()
    content_type = data.get('content_type', 'blog')
    platforms = data.get('platforms', None)

    result = suggest_publish_time(content_type=content_type, platforms=platforms)
    return jsonify(result)


@blog_bp.route('/api/content/publish-time/platforms')
def publish_time_platforms():
    """사용 가능한 플랫폼 목록."""
    from services.content.publish_time_service import get_platform_options
    return jsonify({'platforms': get_platform_options()})


# === 읽기 시간 추정 ===

@blog_bp.route('/api/content/reading-time', methods=['POST'])
@require_auth
def estimate_reading_time_route():
    """콘텐츠의 예상 읽기 시간을 추정합니다."""
    from services.content.reading_time_estimator_service import estimate_reading_time

    data = _get_request_data()
    content = data.get('content', '')
    language = data.get('language', 'ko')
    wpm_override = data.get('wpm_override')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    try:
        override_int = int(wpm_override) if wpm_override is not None else None
    except (TypeError, ValueError):
        return jsonify({'error': 'wpm_override는 정수여야 합니다.'}), 400

    result = estimate_reading_time(content, language=language, wpm_override=override_int)
    return jsonify(result)


@blog_bp.route('/api/content/reading-time/languages')
def reading_time_languages():
    """지원하는 언어 목록을 반환합니다."""
    from services.content.reading_time_estimator_service import get_supported_languages
    return jsonify({'languages': get_supported_languages()})


# === 제목 계층 검증 ===

@blog_bp.route('/api/content/headings/validate', methods=['POST'])
@require_auth
def validate_heading_hierarchy_route():
    """마크다운 콘텐츠의 제목 계층을 검증합니다."""
    from services.content.heading_hierarchy_validator_service import validate_heading_hierarchy

    data = _get_request_data()
    content = data.get('content', '')
    max_h1 = data.get('max_h1', 1)
    min_len = data.get('min_title_length', 3)
    max_len = data.get('max_title_length', 80)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    try:
        max_h1 = int(max_h1)
        min_len = int(min_len)
        max_len = int(max_len)
    except (TypeError, ValueError):
        return jsonify({'error': 'max_h1/min_title_length/max_title_length는 정수여야 합니다.'}), 400

    if max_h1 < 0 or min_len < 0 or max_len <= min_len:
        return jsonify({
            'error': 'max_h1/min_title_length는 0 이상, max_title_length는 min_title_length보다 커야 합니다.',
        }), 400

    result = validate_heading_hierarchy(
        content, max_h1=max_h1, min_title_length=min_len, max_title_length=max_len,
    )
    return jsonify(result)


@blog_bp.route('/api/content/headings/outline', methods=['POST'])
@require_auth
def get_heading_outline_route():
    """콘텐츠에서 마크다운 목차(Outline)를 추출합니다."""
    from services.content.heading_hierarchy_validator_service import get_outline_markdown

    data = _get_request_data()
    content = data.get('content', '')

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    outline = get_outline_markdown(content)
    return jsonify({'outline': outline})


# === 문단 균형 분석 ===

@blog_bp.route('/api/content/paragraph-balance', methods=['POST'])
@require_auth
def analyze_paragraph_balance_route():
    """콘텐츠의 문단 길이 균형을 분석합니다."""
    from services.content.paragraph_balance_analyzer_service import analyze_paragraph_balance

    data = _get_request_data()
    content = data.get('content', '')
    min_chars = data.get('min_chars', 40)
    max_chars = data.get('max_chars', 220)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    try:
        min_chars = int(min_chars)
        max_chars = int(max_chars)
    except (TypeError, ValueError):
        return jsonify({'error': 'min_chars/max_chars는 정수여야 합니다.'}), 400

    if min_chars < 0 or max_chars <= min_chars:
        return jsonify({'error': 'max_chars는 min_chars보다 커야 합니다.'}), 400

    result = analyze_paragraph_balance(content, min_chars=min_chars, max_chars=max_chars)
    return jsonify(result)


# === Pull Quote 추출 ===

@blog_bp.route('/api/content/pull-quotes', methods=['POST'])
@require_auth
def extract_pull_quotes_route():
    """콘텐츠에서 강조할 pull quote 후보를 추출합니다."""
    from services.content.pull_quote_extractor_service import extract_pull_quotes

    data = _get_request_data()
    content = data.get('content', '')
    top_n = data.get('top_n', 5)
    language = data.get('language', 'ko')
    min_length = data.get('min_length', 20)
    max_length = data.get('max_length', 250)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    try:
        top_n = int(top_n)
        min_length = int(min_length)
        max_length = int(max_length)
    except (TypeError, ValueError):
        return jsonify({'error': 'top_n/min_length/max_length는 정수여야 합니다.'}), 400

    if min_length < 1 or max_length <= min_length:
        return jsonify({'error': 'max_length는 min_length보다 커야 합니다.'}), 400
    if top_n < 0:
        return jsonify({'error': 'top_n은 0 이상이어야 합니다.'}), 400

    result = extract_pull_quotes(
        content, top_n=top_n, language=language,
        min_length=min_length, max_length=max_length,
    )
    return jsonify(result)


# === 각주(Footnote) ===

@blog_bp.route('/api/content/footnotes/parse', methods=['POST'])
@require_auth
def parse_footnotes_route():
    """마크다운 각주 참조와 정의를 파싱합니다."""
    from services.content.footnote_service import parse_footnotes

    data = _get_request_data()
    content = data.get('content', '')
    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    return jsonify(parse_footnotes(content))


@blog_bp.route('/api/content/footnotes/validate', methods=['POST'])
@require_auth
def validate_footnotes_route():
    """각주 정의/참조 일관성을 검증합니다."""
    from services.content.footnote_service import validate_footnotes

    data = _get_request_data()
    content = data.get('content', '')
    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    return jsonify(validate_footnotes(content))


@blog_bp.route('/api/content/footnotes/render', methods=['POST'])
@require_auth
def render_footnotes_route():
    """각주를 HTML로 렌더링합니다."""
    from services.content.footnote_service import render_footnotes_html

    data = _get_request_data()
    content = data.get('content', '')
    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    return jsonify(render_footnotes_html(content))


@blog_bp.route('/api/content/footnotes/renumber', methods=['POST'])
@require_auth
def renumber_footnotes_route():
    """각주 ID를 1..N으로 재번호합니다."""
    from services.content.footnote_service import renumber_footnotes

    data = _get_request_data()
    content = data.get('content', '')
    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400

    return jsonify(renumber_footnotes(content))


# === 약어 용어집 ===

@blog_bp.route('/api/content/abbreviations/extract', methods=['POST'])
@require_auth
def extract_abbreviations_route():
    """콘텐츠에서 약어 정의를 추출해 용어집을 만듭니다."""
    from services.content.abbreviation_glossary_service import extract_abbreviations

    data = _get_request_data()
    content = data.get('content', '')
    user_glossary = data.get('user_glossary') or {}
    min_occurrences = data.get('min_occurrences', 1)

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400
    if not isinstance(user_glossary, dict):
        return jsonify({'error': 'user_glossary는 객체여야 합니다.'}), 400

    try:
        min_occurrences = int(min_occurrences)
    except (TypeError, ValueError):
        return jsonify({'error': 'min_occurrences는 정수여야 합니다.'}), 400
    if min_occurrences < 1:
        return jsonify({'error': 'min_occurrences는 1 이상이어야 합니다.'}), 400

    return jsonify(extract_abbreviations(
        content, user_glossary=user_glossary, min_occurrences=min_occurrences,
    ))


@blog_bp.route('/api/content/abbreviations/annotate', methods=['POST'])
@require_auth
def annotate_abbreviations_route():
    """약어 첫 사용 시 풀네임 표기 제안을 반환합니다."""
    from services.content.abbreviation_glossary_service import annotate_first_use

    data = _get_request_data()
    content = data.get('content', '')
    glossary = data.get('glossary') or {}
    only_missing = bool(data.get('only_missing', True))

    if not content or not content.strip():
        return jsonify({'error': '콘텐츠가 필요합니다.'}), 400
    if not isinstance(glossary, dict):
        return jsonify({'error': 'glossary는 객체여야 합니다.'}), 400

    return jsonify(annotate_first_use(content, glossary, only_missing=only_missing))
