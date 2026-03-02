"""
블로그 콘텐츠 생성 API 라우트

핵심 생성 엔드포인트만 포함:
- /generate (단일 URL 생성)
- /regenerate (콘텐츠 재생성)
- /generate-batch (배치 처리)
- /api/generate-merged (통합 생성)
- /generate-stream (SSE 스트리밍)

유틸리티, 고급 생성, 내보내기, 통합 서비스 라우트는 별도 모듈:
- routes/utility_routes.py
- routes/advanced_routes.py
- routes/export_routes.py
- routes/integration_routes.py
"""
import concurrent.futures
import html as html_lib
import json
import time
import uuid

from flask import Blueprint, request, jsonify, current_app, g, Response, stream_with_context
from extensions import limiter
from utils.responses import handle_error, sanitize_error_for_client

from config import get_model_max_tokens
from services import ai_service, content_service
from services.supabase_service import (
    require_auth, is_supabase_enabled, save_history
)
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response

blog_bp = Blueprint('blog', __name__)

DEFAULT_MODEL = 'zhipuai/GLM-4.5-Air'
DEFAULT_STYLE = 'blog_seo'
MAX_BATCH_URLS = 10
MAX_BATCH_WORKERS = 5
BATCH_CONTENT_TOKEN_LIMIT = 3000
MAX_MERGED_URLS = 5

# 에러 응답 헬퍼 (기존 호출 호환)
_handle_error_response = handle_error
_sanitize_error_for_client = sanitize_error_for_client


def _extract_client_id(req) -> str:
    """요청에서 클라이언트 ID를 추출합니다."""
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data.get('clientId'):
        return str(data['clientId'])

    form_id = req.form.get('clientId')
    if form_id:
        return str(form_id)

    raw = (req.get_data(cache=False, as_text=True) or '').strip()
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and parsed.get('clientId'):
                return str(parsed['clientId'])
        except json.JSONDecodeError:
            pass  # 잘못된 JSON은 무시하고 빈 문자열 반환

    return ''


def _get_request_data(req):
    """JSON 또는 form 데이터에서 공통 파라미터를 추출하고 검증합니다.
    API 키는 서버 환경변수에서 관리되므로 요청에서 추출하지 않습니다.
    """
    data = req.get_json(silent=True)
    if isinstance(data, dict) and data:
        # modifiers 검증
        modifiers, _ = _validate_modifiers(data.get('modifiers'))
        # custom_prompt 검증
        custom_prompt, _ = _validate_custom_prompt(data.get('customPrompt'))

        # urls 검증 (리스트 형식 확인)
        urls = data.get('urls', [])
        if not isinstance(urls, list):
            urls = []
        urls = [u for u in urls if isinstance(u, str)][:MAX_BATCH_URLS]

        return {
            'url': data.get('url') if isinstance(data.get('url'), str) else None,
            'urls': urls,
            'content': data.get('content') if isinstance(data.get('content'), str) else None,
            'model': data.get('model', DEFAULT_MODEL) if isinstance(data.get('model'), str) else DEFAULT_MODEL,
            'style': data.get('style', DEFAULT_STYLE) if isinstance(data.get('style'), str) else DEFAULT_STYLE,
            'modifiers': modifiers,
            'custom_prompt': custom_prompt,
        }

    return {
        'url': req.form.get('url'),
        'urls': [],
        'content': req.form.get('content'),
        'model': req.form.get('model', DEFAULT_MODEL),
        'style': req.form.get('style', DEFAULT_STYLE),
        'modifiers': None,
        'custom_prompt': None,
    }


def _validate_modifiers(modifiers):
    """modifiers 파라미터의 유효성을 검증합니다.

    Args:
        modifiers: dict 또는 None

    Returns:
        tuple: (validated_modifiers, error_message)
    """
    if modifiers is None:
        return None, None

    if not isinstance(modifiers, dict):
        return None, 'modifiers는 객체 형식이어야 합니다.'

    # 허용된 키와 값 정의 (v3.0: 2개 모디파이어만 지원)
    allowed_keys = {'length', 'writing_style'}
    allowed_values = {
        'length': {'short', 'medium', 'long'},
        'writing_style': {'conversational', 'explanatory', 'casual', 'expert'}
    }

    validated = {}
    for key, value in modifiers.items():
        if key not in allowed_keys:
            continue  # 알 수 없는 키는 무시
        if not isinstance(value, str):
            continue
        # 값 검증
        if key in allowed_values and value not in allowed_values[key]:
            continue  # 잘못된 값은 무시
        validated[key] = value[:50]  # 길이 제한

    return validated, None


def _validate_custom_prompt(custom_prompt):
    """customPrompt 파라미터의 유효성을 검증합니다.

    Returns:
        tuple: (validated_prompt, error_message)
    """
    if custom_prompt is None:
        return None, None

    if not isinstance(custom_prompt, str):
        return None, 'customPrompt는 문자열이어야 합니다.'

    # 길이 제한 (2000자)
    return custom_prompt.strip()[:2000], None


def _get_style_prompt(style, custom_prompt=None):
    """스타일에 맞는 프롬프트를 반환합니다."""
    if custom_prompt and custom_prompt.strip():
        return custom_prompt.strip()[:2000]
    style_prompts = current_app.config.get('STYLE_PROMPTS', {})
    return style_prompts.get(style, '')


# ── 생성 헬퍼 (분리된 모듈에서 import) ──────────────────────────
from routes.generation_helpers import (
    _fetch_youtube_content, _build_combined_content,
    _handle_short_content_bypass, _handle_cache_hit,
    _call_ai_with_comments, _save_and_respond,
    _process_single_url
)


# ── 핵심 생성 엔드포인트 ──────────────────────────────────────


@blog_bp.route('/generate', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
@require_usage
def generate():
    """단일 YouTube URL에서 콘텐츠를 생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (관리자는 무제한).
    """
    try:
        start_time = time.time()
        params = _get_request_data(request)
        url = params['url']

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

        transcript_text, comments, error, raw_transcript, transcript_source = _fetch_youtube_content(video_id)
        if error:
            return jsonify({'error': error}), 400

        max_tokens = get_model_max_tokens(params['model'])
        main_content = f"[영상 자막]\n{transcript_text}"
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        # 짧은 콘텐츠 바이패스
        bypass_resp = _handle_short_content_bypass(
            transcript_text, params['style'], youtube_title,
            raw_transcript, transcript_source, start_time
        )
        if bypass_resp:
            return bypass_resp

        # 캐시 체크
        from services.cache_service import AICacheService
        force = (request.get_json(silent=True) or {}).get('force', False)
        modifiers = params['modifiers'] or {}
        cache_key = AICacheService.make_key(
            video_id, params['style'], params['model'],
            modifiers.get('length', 'medium'),
            modifiers.get('writing_style', 'conversational')
        )
        cache_resp = _handle_cache_hit(
            cache_key, force, youtube_title,
            raw_transcript, transcript_source, start_time
        )
        if cache_resp:
            return cache_resp

        # AI 호출 (auto/GLM/병렬 분기)
        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        result, used_prompt, comment_result = _call_ai_with_comments(
            truncated_content, params['model'], style_prompt, params,
            comments, transcript_text, max_tokens
        )

        # 캐시 저장 + 히스토리 + 응답
        return _save_and_respond(
            result, used_prompt, comment_result, cache_key,
            video_id, params, url, youtube_title,
            raw_transcript, transcript_source, comments, start_time
        )

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Generate failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/regenerate', methods=['POST'])
@require_auth
@require_usage
def regenerate():
    """기존 콘텐츠를 새로운 스타일로 재생성합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (관리자는 무제한).
    """
    try:
        params = _get_request_data(request)
        content = params['content']

        if not content:
            return jsonify({'error': '재생성할 콘텐츠가 없습니다'}), 400

        style_prompt = _get_style_prompt(params['style'])
        result, used_prompt = ai_service.create_content(
            content,
            params['model'],
            style_prompt,
            return_prompt=True
        )

        return jsonify({**result, "prompt": used_prompt, "usage": get_usage_for_response()})

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Regenerate failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/generate-batch', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
def generate_batch():
    """여러 URL을 배치로 처리합니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (배치 전체가 1회로 계산, 관리자는 무제한).
    """
    from services.usage.usage_service import UsageService

    try:
        # 원자적 사용량 체크 + 차감 (Race Condition 방지)
        can_use, usage = UsageService.try_consume_atomic(g.user_id)
        if not can_use:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'code': 'USAGE_LIMIT_EXCEEDED',
                'usage': usage
            }), 429

        current_app.logger.info("Batch generate request received")

        data = request.get_json()
        current_app.logger.info(f"Request data: {data}")

        if not data:
            current_app.logger.error("No JSON data received")
            return jsonify({'error': 'JSON 데이터가 제공되지 않았습니다'}), 400

        urls = data.get('urls', [])
        model = data.get('model', DEFAULT_MODEL)
        style = data.get('style', DEFAULT_STYLE)
        modifiers = data.get('modifiers')
        custom_prompt = data.get('customPrompt')

        current_app.logger.info(f"URLs to process: {urls}, Model: {model}, Style: {style}")

        if not urls or not isinstance(urls, list):
            return jsonify({'error': 'URL 목록이 제공되지 않았습니다'}), 400
        if len(urls) > MAX_BATCH_URLS:
            return jsonify({'error': f'최대 {MAX_BATCH_URLS}개의 URL만 처리할 수 있습니다'}), 400

        app = current_app._get_current_object()
        results = [None] * len(urls)
        combined_content = []

        # zhipuai/ 모델은 _glm_lock으로 직렬화되므로 순차 처리 (concurrent 경로는 락 대기만 하다 타임아웃)
        is_sequential_model = model.startswith('zhipuai/')

        if is_sequential_model:
            current_app.logger.info(f"Starting to process {len(urls)} URLs sequentially ({model})")
            for i, url in enumerate(urls):
                try:
                    result = _process_single_url(app, url, model, style, modifiers, custom_prompt)
                    results[i] = result
                    current_app.logger.info(f"Completed processing URL {i + 1}: {result.get('success', False)}")

                    if result['success'] and isinstance(result.get('content', ''), str):
                        combined_content.append(result['content'])
                except Exception as e:
                    current_app.logger.error(f"Exception for URL {i + 1}: {e}")
                    results[i] = {
                        'success': False,
                        'url': url,
                        'title': '오류 발생',
                        'error': _sanitize_error_for_client(str(e))
                    }
        else:
            current_app.logger.info(f"Starting to process {len(urls)} URLs concurrently")

            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_BATCH_WORKERS) as executor:
                future_to_index = {
                    executor.submit(
                        _process_single_url, app, url, model, style,
                        modifiers, custom_prompt
                    ): i for i, url in enumerate(urls)
                }

                try:
                    for future in concurrent.futures.as_completed(future_to_index, timeout=600):
                        index = future_to_index[future]
                        try:
                            result = future.result(timeout=300)
                            results[index] = result
                            current_app.logger.info(f"Completed processing URL {index + 1}: {result.get('success', False)}")

                            if result['success'] and isinstance(result.get('content', ''), str):
                                combined_content.append(result['content'])
                        except concurrent.futures.TimeoutError:
                            current_app.logger.error(f"Timeout for URL {index + 1}")
                            results[index] = {
                                'success': False,
                                'url': urls[index],
                                'title': '시간 초과',
                                'error': '[타임아웃] 처리 시간이 초과되었습니다.'
                            }
                        except Exception as e:
                            current_app.logger.error(f"Exception in future for URL {index + 1}: {e}")
                            results[index] = {
                                'success': False,
                                'url': urls[index],
                                'title': '오류 발생',
                                'error': _sanitize_error_for_client(str(e))
                            }
                except concurrent.futures.TimeoutError:
                    current_app.logger.error("Batch overall timeout (600s)")
                    for future, index in future_to_index.items():
                        if results[index] is None:
                            future.cancel()
                            results[index] = {
                                'success': False,
                                'url': urls[index],
                                'title': '시간 초과',
                                'error': '[타임아웃] 배치 전체 처리 시간이 초과되었습니다.'
                            }

        url_to_result = {result['url']: result for result in results if result}
        ordered_results = [
            url_to_result.get(url, {'success': False, 'url': url, 'error': '처리 실패'})
            for url in urls
        ]

        final_combined_content = "\n\n=== 다음 콘텐츠 ===\n\n".join(combined_content) if combined_content else ""
        success_count = sum(1 for r in ordered_results if r.get('success'))
        fail_count = len(ordered_results) - success_count

        current_app.logger.info(f"Batch processing completed. Success: {success_count}, Failed: {fail_count}")

        # 사용량은 try_consume_atomic()으로 이미 차감됨
        updated_usage = usage

        # P2 버그 #7 수정: 배치 히스토리 저장 (N+1 → 배치 INSERT)
        # 배치에서는 transcript, usage, elapsed_time이 None (P3 #13 문서화)
        if g.user_id:
            histories_to_save = []
            for result in ordered_results:
                if result.get('success'):
                    report_id = str(uuid.uuid4())
                    result['id'] = report_id
                    histories_to_save.append({
                        'id': report_id,
                        'url': result.get('url'),
                        'title': result.get('title'),
                        'style': style,
                        'content': result.get('content', ''),
                        'html': result.get('html', ''),
                        'transcript': None,
                        'usage': None,
                        'elapsed_time': None
                    })

            # 배치 INSERT (1회 DB 호출)
            if histories_to_save:
                from services.supabase_service import get_supabase
                supabase = get_supabase()
                if supabase:
                    try:
                        def sanitize_text(text, max_length=50000):
                            """입력 텍스트 검증 및 길이 제한"""
                            if not isinstance(text, str):
                                return ""
                            return text[:max_length]

                        batch_data = [{
                            'user_id': g.user_id,
                            'report_id': sanitize_text(h.get('id', ''), 100),
                            'url': sanitize_text(h.get('url', ''), 500),
                            'title': sanitize_text(h.get('title', ''), 500),
                            'style': sanitize_text(h.get('style', ''), 50),
                            'content': sanitize_text(h.get('content', ''), 100000),
                            'html': sanitize_text(h.get('html', ''), 200000),
                            'transcript': sanitize_text(h.get('transcript', ''), 10000),
                            'usage': h.get('usage'),
                            'elapsed_time': h.get('elapsed_time')
                        } for h in histories_to_save]
                        supabase.table('ie_histories').insert(batch_data).execute()
                    except Exception as e:
                        current_app.logger.warning(f"배치 히스토리 저장 실패: {e}")

        return jsonify({
            'success': True,
            'results': ordered_results,
            'content': final_combined_content,
            'total_processed': len(urls),
            'successful': success_count,
            'failed': fail_count,
            'usage': updated_usage
        })

    except ValueError as e:
        current_app.logger.error(f"ValueError in batch generate: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Batch generate failed: {e}", exc_info=True)
        return _handle_error_response(f'배치 처리 중 오류: {str(e)}')


@blog_bp.route('/api/generate-merged', methods=['POST'])
@limiter.limit("5/minute")
@require_auth
@require_usage
def generate_merged():
    """여러 YouTube URL의 자막을 합쳐 하나의 통합 콘텐츠를 생성합니다.
    2~5개 URL 지원, AI 호출 1회, 사용량 1회 차감.
    """
    try:
        start_time = time.time()
        params = _get_request_data(request)
        urls = params['urls']

        if len(urls) < 2:
            return jsonify({'error': '합쳐서 생성은 최소 2개 URL이 필요합니다.'}), 400
        if len(urls) > MAX_MERGED_URLS:
            return jsonify({'error': f'최대 {MAX_MERGED_URLS}개 URL까지 합칠 수 있습니다.'}), 400

        # URL 유효성 검사
        for url in urls:
            if not content_service.is_youtube_url(url):
                return jsonify({'error': f'유효하지 않은 YouTube URL: {url}'}), 400

        # 병렬로 자막+댓글 추출
        app = current_app._get_current_object()
        video_data = []  # (url, video_id, title, transcript, comments, source)

        def _fetch_one(url):
            with app.app_context():
                vid = content_service.get_video_id(url)
                if not vid:
                    return {'url': url, 'error': '유효하지 않은 YouTube URL'}
                title = content_service.get_content_title(url) or 'YouTube 영상'
                transcript_text, comments, error, _, source = _fetch_youtube_content(vid)
                if error:
                    return {'url': url, 'error': error, 'title': title}
                return {
                    'url': url, 'video_id': vid, 'title': title,
                    'transcript': transcript_text, 'comments': comments,
                    'transcript_source': source,
                }

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(MAX_MERGED_URLS, len(urls))) as executor:
            futures = {executor.submit(_fetch_one, u): u for u in urls}
            for future in concurrent.futures.as_completed(futures):
                video_data.append(future.result())

        # URL 순서 복원
        url_order = {u: i for i, u in enumerate(urls)}
        video_data.sort(key=lambda d: url_order.get(d['url'], 99))

        # 실패 URL 확인
        successes = [d for d in video_data if 'transcript' in d]
        if len(successes) < 2:
            errors = [f"{d['title']}: {d['error']}" for d in video_data if 'error' in d]
            return jsonify({
                'error': f'자막 추출 성공이 2개 미만입니다. 실패: {"; ".join(errors)}'
            }), 400

        # 토큰 예산 분배 후 합성
        max_tokens = get_model_max_tokens(params['model'])
        prompt_overhead = 4000
        available_tokens = max_tokens - prompt_overhead
        per_url_tokens = available_tokens // len(successes)

        merged_parts = []
        all_comments = []
        source_videos = []

        for d in successes:
            truncated = content_service.truncate_text(d['transcript'], per_url_tokens)
            merged_parts.append(f"[영상 {len(merged_parts) + 1}: {d['title']}]\n{truncated}")
            if d['comments']:
                all_comments.extend(d['comments'][:10])
            source_videos.append({
                'url': d['url'],
                'title': d['title'],
                'transcript_source': d['transcript_source'],
            })

        merged_content = '\n\n'.join(merged_parts)
        if all_comments:
            comments_text = '\n'.join(all_comments[:30])
            merged_content += f"\n\n[시청자 댓글 (종합)]\n{comments_text}"

        # AI 호출 1회
        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        result, used_prompt = ai_service.create_content(
            merged_content, params['model'], style_prompt,
            return_prompt=True, modifiers=params['modifiers'],
            style_id=params['style']
        )

        elapsed_time = round(time.time() - start_time, 2)
        report_id = str(uuid.uuid4())

        # 히스토리 저장 (첫 번째 URL 기준)
        if g.user_id:
            save_history(g.user_id, {
                'id': report_id,
                'url': urls[0],
                'title': result.get('title', '통합 분석'),
                'style': params['style'],
                'content': result.get('content', ''),
                'html': result.get('html', ''),
                'transcript': None,
                'usage': result.get('usage'),
                'elapsed_time': elapsed_time,
            })

        # SEO 메타데이터
        seo = None
        if params['style'] == 'blog_seo':
            seo = ai_service.extract_seo_metadata(result.get('content', ''))

        # GEO 메타데이터
        geo = None
        if params['style'] == 'geo_seo':
            geo = ai_service.extract_geo_metadata(result.get('content', ''))

        return jsonify({
            **result,
            'id': report_id,
            'prompt': used_prompt,
            'elapsed_time': elapsed_time,
            'source_videos': source_videos,
            'merged': True,
            'seo': seo,
            'geo': geo,
            'usage': get_usage_for_response(),
        })

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Generate merged failed: {e}")
        return _handle_error_response(str(e))


@blog_bp.route('/generate-stream', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
def generate_stream():
    """SSE 스트리밍으로 콘텐츠를 생성합니다.
    @require_usage 데코레이터 사용 불가 (generator 응답) → 수동 사용량 관리.
    GLM/auto 모델은 스트리밍 미지원 → 비스트리밍 /generate 사용 권장.
    """
    from services.usage.usage_service import UsageService
    import markdown as md_lib

    try:
        params = _get_request_data(request)
        url = params['url']

        if not url:
            return jsonify({'error': 'YouTube URL이 필요합니다.'}), 400
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        # 사용량 체크 (수동)
        user_id = getattr(g, 'user_id', None)
        if is_supabase_enabled() and user_id:
            can_use, usage = UsageService.check_can_use(user_id)
            if not can_use:
                return jsonify({
                    'error': '오늘 사용 가능 횟수를 모두 소진했습니다.',
                    'code': 'USAGE_LIMIT_EXCEEDED',
                    'usage': usage
                }), 429

        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'
        transcript_text, comments, error, raw_transcript, transcript_source = _fetch_youtube_content(video_id)
        if error:
            return jsonify({'error': error}), 400

        max_tokens = get_model_max_tokens(params['model'])
        main_content = f"[영상 자막]\n{transcript_text}"
        if comments:
            main_content = _build_combined_content(transcript_text, comments)
        truncated_content = content_service.truncate_text(main_content, max_tokens)

        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        model = params['model']

        app = current_app._get_current_object()

        def generate_sse():
            with app.app_context():
                try:
                    # meta 이벤트
                    meta = json.dumps({
                        'type': 'meta',
                        'youtube_title': youtube_title,
                        'transcript_source': transcript_source
                    }, ensure_ascii=False)
                    yield f"data: {meta}\n\n"

                    # 토큰 스트리밍
                    full_content = ''
                    for token in ai_service.create_content_stream(
                        truncated_content, model, style_prompt,
                        modifiers=params['modifiers'], style_id=params['style']
                    ):
                        if token is None:
                            break
                        full_content += token
                        token_event = json.dumps({
                            'type': 'token',
                            'content': token
                        }, ensure_ascii=False)
                        yield f"data: {token_event}\n\n"

                    # 완료: 제목/본문 분리 + HTML 변환
                    title = youtube_title
                    body = full_content
                    lines = full_content.split('\n')
                    if lines and lines[0].startswith('#'):
                        title = lines[0].lstrip('#').strip()
                        body = '\n'.join(lines[1:]).strip()

                    try:
                        html = md_lib.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])
                    except Exception:
                        html = f"<pre>{html_lib.escape(body)}</pre>"

                    # 사용량 차감 (성공 시)
                    if is_supabase_enabled() and user_id:
                        UsageService.decrement(user_id)

                    done_event = json.dumps({
                        'type': 'done',
                        'title': title,
                        'content': body,
                        'html': html,
                        'youtube_title': youtube_title,
                        'transcript_source': transcript_source,
                    }, ensure_ascii=False)
                    yield f"data: {done_event}\n\n"

                except Exception as e:
                    error_event = json.dumps({
                        'type': 'error',
                        'message': _sanitize_error_for_client(str(e))
                    }, ensure_ascii=False)
                    yield f"data: {error_event}\n\n"

        return Response(
            stream_with_context(generate_sse()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )

    except Exception as e:
        current_app.logger.error(f"Generate stream setup failed: {e}")
        return _handle_error_response(str(e))


# =============================================
# 프롬프트 템플릿 갤러리 API
# =============================================

@blog_bp.route('/api/templates', methods=['GET'])
@require_auth
def list_templates():
    """템플릿 목록 조회 (공개 + 본인 소유)

    Query params:
        page: 페이지 번호 (기본 1)
        search: 이름/설명 검색어
    """
    from services.prompt_template_service import get_templates

    user_id = getattr(g, 'user_id', None)
    page = max(1, int(request.args.get('page', 1)))
    search = request.args.get('search', '').strip()

    result = get_templates(user_id=user_id, page=page, search=search)
    return jsonify(result)


@blog_bp.route('/api/templates', methods=['POST'])
@require_auth
def create_template():
    """새 템플릿 생성"""
    from services.prompt_template_service import create_template as svc_create

    user_id = getattr(g, 'user_id', None)
    data = request.get_json(silent=True) or {}

    # 필수 필드 검증
    name = (data.get('name') or '').strip()
    prompt_text = (data.get('prompt_text') or '').strip()

    if not name:
        return jsonify({'error': '템플릿 이름을 입력하세요.'}), 400
    if not prompt_text:
        return jsonify({'error': '프롬프트를 입력하세요.'}), 400
    if len(name) > 50:
        return jsonify({'error': '이름은 50자 이내로 입력하세요.'}), 400
    if len(prompt_text) > 5000:
        return jsonify({'error': '프롬프트는 5000자 이내로 입력하세요.'}), 400

    try:
        template = svc_create(user_id=user_id, data={
            'name': name,
            'description': (data.get('description') or '').strip()[:200],
            'prompt_text': prompt_text,
            'style_base': data.get('style_base', 'blog_seo'),
            'is_public': bool(data.get('is_public', False)),
        })
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if template is None:
        return jsonify({'error': '템플릿 저장에 실패했습니다.'}), 500

    return jsonify(template), 201


@blog_bp.route('/api/templates/<template_id>', methods=['PUT'])
@require_auth
def update_template(template_id: str):
    """템플릿 수정 (소유자만)"""
    from services.prompt_template_service import update_template as svc_update

    user_id = getattr(g, 'user_id', None)
    data = request.get_json(silent=True) or {}

    # 수정 가능한 필드 검증
    update_data = {}
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({'error': '이름을 입력하세요.'}), 400
        if len(name) > 50:
            return jsonify({'error': '이름은 50자 이내로 입력하세요.'}), 400
        update_data['name'] = name

    if 'description' in data:
        update_data['description'] = (data.get('description') or '').strip()[:200]

    if 'prompt_text' in data:
        prompt_text = (data['prompt_text'] or '').strip()
        if not prompt_text:
            return jsonify({'error': '프롬프트를 입력하세요.'}), 400
        if len(prompt_text) > 5000:
            return jsonify({'error': '프롬프트는 5000자 이내로 입력하세요.'}), 400
        update_data['prompt_text'] = prompt_text

    if 'style_base' in data:
        update_data['style_base'] = data['style_base']

    if 'is_public' in data:
        update_data['is_public'] = bool(data['is_public'])

    result = svc_update(template_id=template_id, user_id=user_id, data=update_data)
    if result is None:
        return jsonify({'error': '템플릿을 찾을 수 없거나 수정 권한이 없습니다.'}), 404

    return jsonify(result)


@blog_bp.route('/api/templates/<template_id>', methods=['DELETE'])
@require_auth
def delete_template(template_id: str):
    """템플릿 삭제 (소유자만)"""
    from services.prompt_template_service import delete_template as svc_delete

    user_id = getattr(g, 'user_id', None)
    success = svc_delete(template_id=template_id, user_id=user_id)

    if not success:
        return jsonify({'error': '템플릿을 찾을 수 없거나 삭제 권한이 없습니다.'}), 404

    return jsonify({'success': True})


@blog_bp.route('/api/templates/<template_id>/use', methods=['POST'])
@require_auth
def use_template(template_id: str):
    """템플릿 사용 (사용 횟수 증가 + 내용 반환)"""
    from services.prompt_template_service import get_template_by_id, increment_usage

    user_id = getattr(g, 'user_id', None)
    template = get_template_by_id(template_id=template_id, user_id=user_id)

    if template is None:
        return jsonify({'error': '템플릿을 찾을 수 없습니다.'}), 404

    # 비동기적으로 사용 횟수 증가 (실패해도 무방)
    try:
        increment_usage(template_id)
    except Exception:
        pass

    return jsonify(template)
