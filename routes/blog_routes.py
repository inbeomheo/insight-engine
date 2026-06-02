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
import os
import time
import uuid

from flask import Blueprint, request, jsonify, current_app, g, Response, stream_with_context
from extensions import limiter
from utils.responses import handle_error, sanitize_error_for_client, api_error_from_exception

from config import get_model_max_tokens
from services.core import ai_service, content_service
from src.contexts.identity.interface.auth_decorators import require_auth
from src.shared.infrastructure.supabase_client import is_supabase_enabled, get_supabase
from src.contexts.content_library import save_history_entry as save_history
from services.usage import require_usage
from services.usage.usage_decorator import get_usage_for_response

blog_bp = Blueprint('blog', __name__)

DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'chatmock/gpt-5.5')
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

        # source_type 검증
        _allowed_source_types = {'youtube', 'webpage', 'rss', 'arxiv', 'twitter', 'reddit', 'github', 'hackernews', 'podcast'}
        raw_source_type = data.get('source_type')
        source_type = raw_source_type if raw_source_type in _allowed_source_types else None

        # detail_level 검증 (허용값: brief, standard, deep)
        _allowed_detail_levels = {'brief', 'standard', 'deep'}
        raw_detail = data.get('detail_level')
        detail_level = raw_detail if isinstance(raw_detail, str) and raw_detail in _allowed_detail_levels else 'standard'

        # output_format 검증 (허용값: html, markdown, plain)
        _allowed_formats = {'html', 'markdown', 'plain'}
        raw_format = data.get('output_format')
        output_format = raw_format if isinstance(raw_format, str) and raw_format in _allowed_formats else 'html'

        # max_chars 검증 (정수, 100~50000)
        raw_max_chars = data.get('max_chars')
        max_chars = None
        if raw_max_chars is not None:
            try:
                max_chars = int(raw_max_chars)
                if max_chars < 100 or max_chars > 50000:
                    max_chars = None
            except (ValueError, TypeError):
                max_chars = None

        # include_transcript 검증
        include_transcript = bool(data.get('include_transcript', False))

        # enable_citations 검증 (인용 타임스탬프 모드)
        enable_citations = bool(data.get('enable_citations', False))

        return {
            'url': data.get('url') if isinstance(data.get('url'), str) else None,
            'urls': urls,
            'content': data.get('content') if isinstance(data.get('content'), str) else None,
            'model': data.get('model', DEFAULT_MODEL) if isinstance(data.get('model'), str) else DEFAULT_MODEL,
            'style': data.get('style', DEFAULT_STYLE) if isinstance(data.get('style'), str) else DEFAULT_STYLE,
            'modifiers': modifiers,
            'custom_prompt': custom_prompt,
            'analyze': bool(data.get('analyze', False)),
            'source_type': source_type,
            'detail_level': detail_level,
            'output_format': output_format,
            'max_chars': max_chars,
            'include_transcript': include_transcript,
            'enable_citations': enable_citations,
            'web_search': bool(data.get('web_search', False)),
            'agent_mode': bool(data.get('agent_mode', False)),
        }

    # form 데이터에서 modifiers JSON 파싱 (파일 업로드 시 FormData로 전송)
    form_modifiers = None
    raw_modifiers = req.form.get('modifiers')
    if raw_modifiers:
        try:
            parsed = json.loads(raw_modifiers)
            if isinstance(parsed, dict):
                form_modifiers, _ = _validate_modifiers(parsed)
        except (json.JSONDecodeError, ValueError):
            pass

    return {
        'url': req.form.get('url'),
        'urls': [],
        'content': req.form.get('content'),
        'model': req.form.get('model', DEFAULT_MODEL),
        'style': req.form.get('style', DEFAULT_STYLE),
        'modifiers': form_modifiers,
        'custom_prompt': req.form.get('customPrompt'),
        'analyze': False,
        'source_type': None,
        'detail_level': req.form.get('detail_level', 'standard'),
        'output_format': req.form.get('output_format', 'html'),
        'max_chars': None,
        'include_transcript': False,
        'enable_citations': False,
        'web_search': str(req.form.get('web_search', '')).lower() == 'true',
        'agent_mode': str(req.form.get('agent_mode', '')).lower() == 'true',
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

    # 허용된 키와 값 정의 (v3.1: 3개 모디파이어 지원)
    allowed_keys = {'length', 'writing_style', 'language'}
    allowed_values = {
        'length': {'short', 'medium', 'long'},
        'writing_style': {'conversational', 'explanatory', 'casual', 'expert'},
        'language': {'ko', 'en', 'ja'},
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


# ── 생성 헬퍼 (분리된 모듈에서 import) ──────────────────────────
from routes.generation_helpers import (
    _fetch_youtube_content, _build_combined_content,
    _handle_short_content_bypass, _handle_cache_hit,
    _call_ai_with_comments, _save_and_respond,
    _process_single_url,
    _get_style_prompt, _handle_direct_text, _handle_audio_upload,
    _handle_document_upload, _handle_web_source,
)
from routes import generation_helpers as _generation_helpers


# ── 핵심 생성 엔드포인트 ──────────────────────────────────────


@blog_bp.route('/generate', methods=['POST'])
@limiter.limit("15/minute")
@require_auth
@require_usage
def generate():
    """단일 URL에서 콘텐츠를 생성합니다 (YouTube, 웹페이지, RSS, arXiv 지원).
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    로그인 필수, 하루 5회 제한 적용 (관리자는 무제한).
    """
    from services.content.multi_source_collector import detect_source_type, SOURCE_YOUTUBE

    try:
        start_time = time.time()
        params = _get_request_data(request)
        url = params['url']
        direct_content = params.get('content')

        # ── 직접 텍스트 입력 모드 ──
        if not url and direct_content and len(direct_content.strip()) >= 50:
            return _generation_helpers._handle_direct_text(params, start_time)

        # ── 파일 업로드 모드 (오디오 / 문서) ──
        uploaded_file = request.files.get('file')
        if uploaded_file and not url:
            filename = (uploaded_file.filename or '').lower()
            _audio_extensions = ('.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac', '.webm', '.weba')

            if filename.endswith(_audio_extensions) or (uploaded_file.content_type or '').startswith('audio/'):
                return _handle_audio_upload(params, uploaded_file, start_time)

            try:
                return _handle_document_upload(params, uploaded_file, start_time)
            except ValueError as e:
                return handle_error(str(e))

        if not url:
            return jsonify({'error': 'URL이 필요합니다.'}), 400

        # ── 비YouTube 소스 (웹페이지 / RSS / arXiv) ──
        source_type = params.get('source_type') or detect_source_type(url)
        if source_type != SOURCE_YOUTUBE:
            try:
                return _generation_helpers._handle_web_source(params, url, source_type, start_time)
            except ValueError as e:
                return handle_error(str(e))

        # ── YouTube 흐름 ──
        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': '유효하지 않은 YouTube URL입니다.'}), 400

        # 제목 조회와 자막/댓글 추출을 병렬 실행 (700-1500ms 절감)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            title_future = executor.submit(content_service.get_content_title, url)
            content_future = executor.submit(_fetch_youtube_content, video_id)
            youtube_title = title_future.result() or 'YouTube 영상'
            transcript_text, comments, error, raw_transcript, transcript_source, transcript_segments = content_future.result()
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
        from services.core.cache_service import AICacheService
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

        # 에이전트 모드 여부 확인
        request_data_all = request.get_json(silent=True) or {}
        agent_mode = bool(request_data_all.get('agent_mode', False))

        style_prompt = _get_style_prompt(params['style'], params['custom_prompt'])
        agent_meta = None

        if agent_mode:
            # 멀티에이전트 파이프라인 실행
            try:
                from services.agents import Orchestrator
                user_id = getattr(g, 'user_id', None)
                orchestrator = Orchestrator(model=params['model'])
                agent_output = orchestrator.run(
                    transcript=transcript_text,
                    style=params['style'],
                    style_prompt=style_prompt,
                    url=url,
                    modifiers=params['modifiers'] or {},
                    user_id=user_id,
                )
                result = {
                    'title': agent_output['title'],
                    'content': agent_output['content'],
                    'html': agent_output['html'],
                    'usage': agent_output['usage'],
                }
                used_prompt = f'[에이전트 모드] {params["style"]}'
                comment_result = None
                agent_meta = {
                    'agent_mode': True,
                    'quality': agent_output.get('quality'),
                    'seo': agent_output.get('seo'),
                    'elapsed_time': agent_output.get('elapsed_time', 0),
                }
            except Exception as ae:
                current_app.logger.error(f'에이전트 모드 실패, 일반 모드로 폴백: {ae}')
                web_search = bool(request_data_all.get('web_search', False))
                result, used_prompt, comment_result = _call_ai_with_comments(
                    truncated_content, params['model'], style_prompt, params,
                    comments, transcript_text, max_tokens, web_search=web_search
                )
        else:
            web_search = bool(request_data_all.get('web_search', False))
            result, used_prompt, comment_result = _call_ai_with_comments(
                truncated_content, params['model'], style_prompt, params,
                comments, transcript_text, max_tokens, web_search=web_search
            )

        # 인용 타임스탬프 처리 (enable_citations: true 요청 시)
        if params.get('enable_citations') and video_id:
            try:
                from services.content.citation_service import (
                    parse_citations, validate_citations,
                    enrich_content_with_links, enrich_html_with_links,
                )
                # 마크다운 내 [MM:SS] 링크 변환
                result['content'] = enrich_content_with_links(
                    result.get('content', ''), video_id
                )
                # HTML 내 [MM:SS] 링크 변환
                if result.get('html'):
                    result['html'] = enrich_html_with_links(
                        result['html'], video_id
                    )
                # 인용 목록 파싱 + 검증
                citations = parse_citations(result.get('content', ''))
                citations = validate_citations(citations, transcript_segments or [])
                result['citations'] = citations
            except Exception as cite_err:
                current_app.logger.warning(f"인용 처리 실패 (무시): {cite_err}")

        # 품질 평가 (quality_check: true 요청 시만)
        quality_score = None
        request_data = request_data_all
        if request_data.get('quality_check'):
            try:
                from services.quality.quality_service import evaluate_quality
                quality_score = evaluate_quality(
                    content=result.get('content', ''),
                    source_summary=transcript_text[:500],
                )
                current_app.logger.info(
                    f"품질 평가 완료: grade={quality_score.get('grade')}, "
                    f"overall={quality_score.get('overall')}"
                )
            except Exception as qe:
                current_app.logger.warning(f"품질 평가 실패 (무시): {qe}")

        # 캐시 저장 + 히스토리 + 응답
        return _save_and_respond(
            result, used_prompt, comment_result, cache_key,
            video_id, params, url, youtube_title,
            raw_transcript, transcript_source, comments, start_time,
            quality_score=quality_score,
            agent_meta=agent_meta,
            transcript_segments=transcript_segments,
        )

    except ValueError as e:
        return handle_error(str(e))
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

        return jsonify({**result, "prompt": used_prompt, "quota": get_usage_for_response()})

    except ValueError as e:
        return handle_error(str(e))
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

            # 배치 INSERT — Content/Library BC에 위임 (sanitize + batch INSERT 통합 처리)
            if histories_to_save:
                from src.contexts.content_library import save_many_history_entries
                save_many_history_entries(g.user_id, histories_to_save)

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
        return handle_error(str(e))
    except Exception as e:
        current_app.logger.error(f"Batch generate failed: {e}", exc_info=True)
        return api_error_from_exception(e, '배치 처리 중 오류가 발생했습니다.')


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
                try:
                    vid = content_service.get_video_id(url)
                    if not vid:
                        return {'url': url, 'error': '유효하지 않은 YouTube URL'}
                    title = content_service.get_content_title(url) or 'YouTube 영상'
                    transcript_text, comments, error, _, source, _ = _fetch_youtube_content(vid)
                    if error:
                        return {'url': url, 'error': error, 'title': title}
                    return {
                        'url': url, 'video_id': vid, 'title': title,
                        'transcript': transcript_text, 'comments': comments,
                        'transcript_source': source,
                    }
                except Exception as e:
                    current_app.logger.error('Merged fetch failed for %s: %s', url, e, exc_info=True)
                    return {
                        'url': url,
                        'title': '알 수 없는 영상',
                        'error': _sanitize_error_for_client(str(e))
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
            style_id=params['style'],
            detail_level=params.get('detail_level'),
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
            'quota': get_usage_for_response(),
        })

    except ValueError as e:
        return handle_error(str(e))
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
        transcript_text, comments, error, raw_transcript, transcript_source, transcript_segments = _fetch_youtube_content(video_id)
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
                        modifiers=params['modifiers'], style_id=params['style'],
                        detail_level=params.get('detail_level'),
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
                        'transcript_segments': transcript_segments or [],
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

@blog_bp.route('/api/video-qa', methods=['POST'])
@require_auth
def video_qa():
    """YouTube 영상 자막 기반 Q&A 챗봇 엔드포인트.

    요청 형식:
        {"video_url": str, "question": str, "history": [{"role": str, "content": str}], "model": str}

    응답 형식:
        {"answer": str, "sources": [{"text": str, "relevance": float}]}
    """
    from services.media.video_qa_service import (
        is_video_indexed,
        index_video_transcript,
        answer_question,
    )

    data = request.get_json(silent=True) or {}
    video_url = data.get('video_url', '').strip()
    question = data.get('question', '').strip()
    history = data.get('history', [])
    model = data.get('model') or None

    # 입력값 검증
    if not video_url:
        return jsonify({'error': 'video_url이 필요합니다.'}), 400
    if not content_service.is_youtube_url(video_url):
        return jsonify({'error': '유효한 YouTube URL을 입력해주세요.'}), 400
    if not question:
        return jsonify({'error': '질문을 입력해주세요.'}), 400
    if len(question) > 500:
        return jsonify({'error': '질문은 500자 이내로 입력해주세요.'}), 400

    video_id = content_service.get_video_id(video_url)
    if not video_id:
        return jsonify({'error': '영상 ID를 추출할 수 없습니다.'}), 400

    try:
        # 아직 인덱싱이 안 됐으면 자막을 가져와 인덱싱
        if not is_video_indexed(video_id):
            transcript_result = content_service.get_transcript(video_id)

            # get_transcript 반환값은 str 또는 dict
            if isinstance(transcript_result, dict):
                if transcript_result.get('error'):
                    return jsonify({'error': sanitize_error_for_client(transcript_result['error'])}), 400
                transcript_text = transcript_result.get('text') or transcript_result.get('transcript', '')
            elif isinstance(transcript_result, str):
                transcript_text = transcript_result
            else:
                transcript_text = ''

            if not transcript_text:
                return jsonify({'error': '영상 자막을 가져올 수 없습니다.'}), 400

            ok = index_video_transcript(video_id, transcript_text)
            if not ok:
                return jsonify({'error': '[서버 오류] 영상 자막 인덱싱에 실패했습니다.'}), 500

        # Q&A 답변 생성
        result = answer_question(
            video_id=video_id,
            question=question,
            history=history if isinstance(history, list) else [],
            model=model,
        )

        return jsonify(result)
    except Exception as exc:
        current_app.logger.error('Video QA failed: %s', exc, exc_info=True)
        return api_error_from_exception(exc, '[서버 오류] 영상 Q&A 처리 중 문제가 발생했습니다.')


@blog_bp.route('/api/tts', methods=['POST'])
@limiter.limit("20/minute")
@require_auth
def text_to_speech():
    """텍스트를 TTS(Text-to-Speech)로 변환해 MP3 오디오 파일을 반환합니다.

    요청 형식:
        {"text": str, "voice": str (optional), "speed": float (optional)}

    응답:
        audio/mpeg 파일 스트림
    """
    from config import TTS_DEFAULT_VOICE, TTS_MAX_CHARS
    from services.media.tts_service import TTSService

    data = request.get_json(silent=True) or {}

    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': '변환할 텍스트를 입력하세요.'}), 400

    if len(text) > TTS_MAX_CHARS:
        return jsonify({
            'error': f'텍스트가 너무 깁니다. 최대 {TTS_MAX_CHARS}자까지 지원합니다.'
        }), 400

    voice = data.get('voice') or TTS_DEFAULT_VOICE
    if not isinstance(voice, str):
        voice = TTS_DEFAULT_VOICE

    speed = data.get('speed', 1.0)
    try:
        speed = float(speed)
        speed = max(0.5, min(2.0, speed))
    except (TypeError, ValueError):
        speed = 1.0

    try:
        audio_bytes = TTSService.synthesize(text, voice=voice, speed=speed, preprocess=True)
    except ValueError as exc:
        return handle_error(str(exc))
    except RuntimeError as exc:
        return api_error_from_exception(exc, '오디오 생성에 실패했습니다.')

    return Response(
        audio_bytes,
        mimetype='audio/mpeg',
        headers={
            'Content-Disposition': 'inline; filename="podcast.mp3"',
            'Content-Length': str(len(audio_bytes)),
            'Cache-Control': 'no-cache',
        },
    )


# =============================================
# 이벤트 추출
# =============================================

@blog_bp.route('/api/extract-events', methods=['POST'])
def extract_events_endpoint():
    """YouTube 영상 자막에서 구조화된 이벤트를 추출합니다.

    요청 형식:
        {"url": "https://youtube.com/..."} — URL 제공 시 자막 자동 추출
        {"transcript": "자막 텍스트"} — 자막 직접 제공
        {"model": "zhipuai/GLM-4.5-Air"} — 선택적 모델 지정

    응답 형식:
        {"events": [...], "summary": {...}, "categorized": {...}}
    """
    data = request.get_json(silent=True) or {}

    url = (data.get('url') or '').strip()
    transcript_text = (data.get('transcript') or '').strip()
    model = (data.get('model') or '').strip() or None

    # 자막 획득: transcript 직접 제공 또는 URL에서 추출
    if not transcript_text:
        if not url:
            return jsonify({'error': 'url 또는 transcript 중 하나를 제공해야 합니다.'}), 400

        if not content_service.is_youtube_url(url):
            return jsonify({'error': '유효한 YouTube URL이 아닙니다.'}), 400

        video_id = content_service.get_video_id(url)
        if not video_id:
            return jsonify({'error': 'YouTube 비디오 ID를 추출할 수 없습니다.'}), 400

        try:
            transcript_data = content_service.get_transcript(video_id)
            if not transcript_data or not transcript_data.get('transcript'):
                return jsonify({'error': '영상 자막을 추출할 수 없습니다. 자막이 없는 영상이거나 접근 불가합니다.'}), 422

            # 자막 세그먼트 → 타임스탬프 포함 텍스트 변환 (이벤트 추출 품질 향상)
            segments = transcript_data.get('segments', [])
            if segments:
                from services.core.ai_service import format_transcript_with_timestamps
                transcript_text = format_transcript_with_timestamps(segments)
            else:
                transcript_text = transcript_data.get('transcript', '')

        except Exception as exc:
            return api_error_from_exception(exc, '자막 추출에 실패했습니다.')

    # 이벤트 추출
    try:
        from services.content.event_extraction_service import (
            extract_events, categorize_events, get_event_summary
        )
        events = extract_events(transcript_text, model=model)
        categorized = categorize_events(events)
        summary = get_event_summary(events)

        return jsonify({
            'events': events,
            'categorized': categorized,
            'summary': summary,
        })

    except ValueError as exc:
        return handle_error(str(exc))
    except RuntimeError as exc:
        return api_error_from_exception(exc, '이벤트 추출에 실패했습니다.')
    except Exception as exc:
        return api_error_from_exception(exc, '이벤트 추출 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.')

# ============================================================
# 분리된 라우트 패키지 — 부수효과 import로 자동 등록
# - routes/blog/templates.py: 프롬프트 템플릿 5개
# - routes/blog/transcript_workspace.py: F13 자막 워크스페이스
# - routes/blog/voice_capture.py: 핸즈프리 음성 캡처
# ============================================================
from routes import blog as _blog_subroutes  # noqa: E402,F401
