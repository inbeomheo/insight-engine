"""
콘텐츠 생성 내부 헬퍼 함수 — blog_routes.py에서 분리
"""
import concurrent.futures
import time
import uuid

from flask import current_app, g, jsonify

from services.core import ai_service, content_service
from services.core.content_service import clear_cache
from services.data.supabase_service import save_history
from services.usage.usage_decorator import get_usage_for_response
from services.platform.webhook_service import WebhookService
from config import get_model_max_tokens, WEBHOOK_URL, WEBHOOK_ENABLED
from utils.responses import sanitize_error_for_client

_webhook = WebhookService(url=WEBHOOK_URL, enabled=WEBHOOK_ENABLED)


def _sanitize_transcript_error(error_msg: str) -> str:
    """자막 조회 오류를 클라이언트 노출용 메시지로 정리합니다."""
    raw_message = str(error_msg or '')
    safe_message = sanitize_error_for_client(raw_message)

    # 서비스가 "사용자 메시지: 내부 상세" 형태로 원문 예외를 덧붙인 경우 차단합니다.
    if safe_message == raw_message and ': ' in raw_message:
        return '[서버 오류] 자막을 가져오는 중 문제가 발생했습니다. 다시 시도해주세요.'
    if safe_message.startswith('[서버 오류]'):
        return '[서버 오류] 자막을 가져오는 중 문제가 발생했습니다. 다시 시도해주세요.'

    return safe_message


def _apply_output_format(result: dict, output_format: str, max_chars: int = None) -> dict:
    """output_format에 따라 결과를 변환합니다."""
    import re
    if output_format == 'plain':
        text = result.get('content', '')
        text = re.sub(r'#{1,6}\s+', '', text)  # headers
        text = re.sub(r'\*{1,3}(.+?)\*{1,3}', r'\1', text)  # bold/italic
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # links
        text = re.sub(r'`(.+?)`', r'\1', text)  # inline code
        text = re.sub(r'\n{3,}', '\n\n', text)  # excessive newlines
        result = {**result, 'content': text, 'html': ''}
    elif output_format == 'markdown':
        result = {**result, 'html': ''}  # HTML 제거, markdown만

    if max_chars and result.get('content'):
        result = {**result, 'content': result['content'][:max_chars]}

    return result


def _fetch_youtube_content(video_id):
    """YouTube 영상의 자막과 댓글을 분리하여 가져옵니다.
    Supadata API 키는 환경변수에서 자동으로 로드됩니다.

    Returns:
        tuple: (transcript_text, comments_list, error, raw_transcript, transcript_source, transcript_segments)
        - comments_list: 댓글 문자열 리스트 (전체) 또는 빈 리스트
        - transcript_source: 'api' | 'watch' | 'supadata' | 'cache'
        - transcript_segments: 타임스탬프 포함 세그먼트 목록 [{'start': float, 'text': str}, ...]
    """
    transcript_result = content_service.get_transcript(video_id)
    if isinstance(transcript_result, dict) and transcript_result.get('error'):
        return None, [], _sanitize_transcript_error(transcript_result['error']), None, None, []

    if isinstance(transcript_result, dict):
        # 새 형식: {'text': '...', 'source': '...', 'segments': [...]}
        transcript_text = transcript_result.get('text', '')
        transcript_source = transcript_result.get('source', 'unknown')
        transcript_segments = transcript_result.get('segments', [])
    elif isinstance(transcript_result, str):
        transcript_text = transcript_result
        transcript_source = 'unknown'
        transcript_segments = []
    else:
        return None, [], '[서버 오류] 자막 정보를 불러오는 중 문제가 발생했습니다.', None, None, []

    try:
        comments = content_service.get_top_comments(video_id) or []
    except Exception as e:
        current_app.logger.warning('Top comments fetch failed for %s: %s', video_id, e)
        comments = []

    return transcript_text, comments, None, transcript_text, transcript_source, transcript_segments


def _build_combined_content(transcript_text, comments):
    """자막과 댓글을 기존 형식으로 합성합니다 (배치 처리 호환용).

    Args:
        transcript_text: 자막 텍스트
        comments: 댓글 리스트

    Returns:
        str: "[영상 자막]\\n...\\n\\n[시청자 댓글]\\n..." 형식 문자열
    """
    comments_text = '\n'.join(comments[:20]) if comments else '(댓글 없음)'
    return f"[영상 자막]\n{transcript_text}\n\n[시청자 댓글]\n{comments_text}"


def _generate_main_content(app, content, model, style_prompt, modifiers, style_id=None):
    """스레드에서 메인 콘텐츠를 생성합니다.

    Returns:
        tuple: (result_dict, used_prompt)
    """
    with app.app_context():
        return ai_service.create_content(
            content, model, style_prompt,
            return_prompt=True, modifiers=modifiers,
            style_id=style_id
        )


def _generate_comment_summary(app, comments, model):
    """스레드에서 댓글 요약을 생성합니다. 실패 시 None 반환.

    Args:
        app: Flask 앱 객체
        comments: 댓글 리스트 (최대 50개 사용)
        model: AI 모델 ID

    Returns:
        dict 또는 None: {'content': '...', 'usage': {...}} 또는 실패 시 None
    """
    from prompts.styles.comment_summary import COMMENT_SUMMARY_PROMPT

    with app.app_context():
        try:
            comments_text = '\n'.join(comments[:50])
            comment_content = f"[시청자 댓글]\n{comments_text}"

            result = ai_service.create_content(
                comment_content, model, COMMENT_SUMMARY_PROMPT,
                style_id='comment_summary'
            )
            return result
        except Exception as e:
            current_app.logger.warning(f"댓글 요약 생성 실패 (무시): {e}")
            return None


def _combine_results(main_result, main_prompt, comment_result):
    """메인 결과와 댓글 요약을 결합합니다.

    Args:
        main_result: 메인 AI 생성 결과 dict
        main_prompt: 메인 생성에 사용된 프롬프트
        comment_result: 댓글 요약 결과 dict 또는 None

    Returns:
        tuple: (combined_result, used_prompt)
    """
    if not comment_result:
        return main_result, main_prompt

    import markdown as md_lib

    # 본문 끝에 댓글 요약 추가
    comment_body = comment_result.get('content', '')
    combined_content = main_result.get('content', '') + '\n\n' + comment_body

    # HTML 재생성
    try:
        combined_html = md_lib.markdown(
            combined_content,
            extensions=['tables', 'fenced_code', 'nl2br']
        )
    except Exception:
        combined_html = main_result.get('html', '') + comment_result.get('html', '')

    # 토큰 사용량 합산
    main_usage = main_result.get('usage', {})
    comment_usage = comment_result.get('usage', {})
    combined_usage = {
        'prompt_tokens': main_usage.get('prompt_tokens', 0) + comment_usage.get('prompt_tokens', 0),
        'completion_tokens': main_usage.get('completion_tokens', 0) + comment_usage.get('completion_tokens', 0),
        'total_tokens': main_usage.get('total_tokens', 0) + comment_usage.get('total_tokens', 0),
    }

    combined_result = {
        'title': main_result.get('title', ''),
        'content': combined_content,
        'html': combined_html,
        'usage': combined_usage,
    }

    return combined_result, main_prompt


def _handle_short_content_bypass(transcript_text, style, youtube_title,
                                  raw_transcript, transcript_source, start_time):
    """짧은 콘텐츠 바이패스 체크. 해당 시 Response 반환, 아니면 None."""
    from config import SHORT_CONTENT_THRESHOLD, SHORT_CONTENT_BYPASS_STYLES
    if len(transcript_text) >= SHORT_CONTENT_THRESHOLD or style not in SHORT_CONTENT_BYPASS_STYLES:
        return None

    import markdown as md_lib
    g.skip_usage_decrement = True
    bypass_html = md_lib.markdown(transcript_text, extensions=['tables', 'fenced_code', 'nl2br'])
    elapsed_time = round(time.time() - start_time, 2)
    return jsonify({
        'title': youtube_title,
        'content': transcript_text,
        'html': bypass_html,
        'id': str(uuid.uuid4()),
        'prompt': '',
        'elapsed_time': elapsed_time,
        'youtube_title': youtube_title,
        'transcript': raw_transcript,
        'transcript_source': transcript_source,
        'comment_summary_included': False,
        'bypassed': True,
        'bypass_reason': 'short_content',
        'quota': get_usage_for_response()
    })


def _handle_cache_hit(cache_key, force, youtube_title,
                       raw_transcript, transcript_source, start_time):
    """캐시 히트 체크. 히트 시 Response 반환, 아니면 None."""
    if force:
        return None

    cached = current_app.ai_cache.get(cache_key)
    if not cached:
        return None

    g.skip_usage_decrement = True
    elapsed_time = round(time.time() - start_time, 2)
    _cached_content = cached.get('content', '')
    return jsonify({
        **cached,
        'id': str(uuid.uuid4()),
        'elapsed_time': elapsed_time,
        'youtube_title': youtube_title,
        'transcript': raw_transcript,
        'transcript_source': transcript_source,
        'cached': True,
        'duplicate_message': '동일 설정으로 이전에 생성된 콘텐츠입니다.',
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
        'char_count': len(_cached_content),
        'word_count': len(_cached_content.split()) if _cached_content else 0,
        'quota': get_usage_for_response()
    })


def _generate_main_content_with_web_search(app, content, model, style_prompt, modifiers, style_id=None, web_search=False, detail_level=None):
    """스레드에서 메인 콘텐츠를 생성합니다 (웹 검색 지원).

    Returns:
        tuple: (result_dict, used_prompt)
    """
    with app.app_context():
        return ai_service.create_content(
            content, model, style_prompt,
            return_prompt=True, modifiers=modifiers,
            style_id=style_id, web_search=web_search,
            detail_level=detail_level,
        )


def _call_ai_with_comments(truncated_content, model, style_prompt, params,
                            comments, transcript_text, max_tokens, web_search=False):
    """AI 호출 + 댓글 병렬 처리. (result, used_prompt, comment_result) 반환."""
    # RAG 컨텍스트를 위한 user_id (없으면 None → RAG 스킵)
    user_id = getattr(g, 'user_id', None)
    detail_level = params.get('detail_level')
    is_auto = model == 'auto'

    if is_auto:
        from config import FALLBACK_CHAIN
        comment_result = None
        if comments:
            combined_content = _build_combined_content(transcript_text, comments)
            truncated_content = content_service.truncate_text(
                f"[영상 자막]\n{combined_content}", max_tokens
            )
        result, used_prompt = ai_service.create_content_with_fallback(
            truncated_content, FALLBACK_CHAIN, style_prompt,
            return_prompt=True, modifiers=params['modifiers'],
            style_id=params['style'], user_id=user_id
        )
        return result, used_prompt, comment_result

    is_glm = model.startswith('zhipuai/')

    if comments:
        app = current_app._get_current_object()

        if is_glm:
            # GLM 모델: 순차 실행 (글로벌 락 충돌 방지)
            result, used_prompt = ai_service.create_content(
                truncated_content, model, style_prompt,
                return_prompt=True, modifiers=params['modifiers'],
                style_id=params['style'], user_id=user_id,
                web_search=web_search,
                detail_level=detail_level,
            )
            comment_result = _generate_comment_summary(app, comments, model)
        else:
            # 병렬 실행
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                main_future = executor.submit(
                    _generate_main_content_with_web_search, app, truncated_content,
                    model, style_prompt, params['modifiers'],
                    style_id=params['style'], web_search=web_search,
                    detail_level=detail_level,
                )
                comment_future = executor.submit(
                    _generate_comment_summary, app, comments, model
                )

                result, used_prompt = main_future.result()
                comment_result = comment_future.result()

        result, used_prompt = _combine_results(result, used_prompt, comment_result)
    else:
        # 댓글 없음: 단일 AI 호출
        comment_result = None
        result, used_prompt = ai_service.create_content(
            truncated_content, model, style_prompt,
            return_prompt=True, modifiers=params['modifiers'],
            style_id=params['style'], user_id=user_id,
            web_search=web_search,
            detail_level=detail_level,
        )

    return result, used_prompt, comment_result


def _save_and_respond(result, used_prompt, comment_result, cache_key,
                       video_id, params, url, youtube_title,
                       raw_transcript, transcript_source, comments, start_time,
                       quality_score=None, agent_meta=None,
                       transcript_segments=None):
    """캐시 저장 + 히스토리 저장 + JSON 응답 반환."""
    model = params['model']
    modifiers = params['modifiers'] or {}

    current_app.ai_cache.put(
        cache_key, video_id, params['style'], model,
        modifiers.get('length', 'medium'),
        modifiers.get('writing_style', 'conversational'),
        {
            'title': result.get('title', ''),
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'comment_summary_included': bool(comments and comment_result),
            'prompt': used_prompt,
        }
    )

    elapsed_time = round(time.time() - start_time, 2)

    report_id = str(uuid.uuid4())
    if g.user_id:
        save_history(g.user_id, {
            'id': report_id,
            'url': url,
            'title': result.get('title', youtube_title),
            'style': params['style'],
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'transcript': raw_transcript,
            'transcript_source': transcript_source,
            'usage': result.get('usage'),
            'elapsed_time': elapsed_time
        })

    # SEO 메타데이터 추출 (blog_seo 스타일만)
    seo = None
    if params['style'] == 'blog_seo':
        seo = ai_service.extract_seo_metadata(result.get('content', ''))

    # GEO 메타데이터 추출 (geo_seo 스타일만)
    geo = None
    if params['style'] == 'geo_seo':
        geo = ai_service.extract_geo_metadata(result.get('content', ''))

    # FAQ JSON-LD 스키마 추출 (blog_seo, geo_seo 스타일)
    faq_schema = None
    if params['style'] in ('blog_seo', 'geo_seo'):
        faq_schema = ai_service.extract_faq_schema(result.get('content', ''))

    # CTA 추출 (geo_seo 스타일만)
    cta = None
    if params['style'] == 'geo_seo':
        cta = ai_service.extract_cta(result.get('content', ''))

    # JSON-LD 구조화 데이터 생성 (geo_seo 스타일만)
    json_ld_schemas = None
    if params['style'] == 'geo_seo':
        try:
            from services.seo.seo_metadata_service import generate_all_schemas
            content_text = result.get('content', '')
            faq_pairs = []
            if faq_schema and faq_schema.get('mainEntity'):
                for entity in faq_schema['mainEntity']:
                    faq_pairs.append({
                        'question': entity.get('name', ''),
                        'answer': entity.get('acceptedAnswer', {}).get('text', ''),
                    })
            keywords = (geo or {}).get('entity_tags', [])
            json_ld_schemas = generate_all_schemas(
                video_url=url,
                title=result.get('title', youtube_title),
                content=content_text,
                faq_pairs=faq_pairs,
                keywords=keywords,
            )
        except Exception as schema_err:
            current_app.logger.warning(f"JSON-LD 스키마 생성 실패 (무시): {schema_err}")

    # NLP 분석 (analyze=true 파라미터가 있을 때만 실행, 비용 절감)
    analysis = None
    if params.get('analyze'):
        try:
            from services.analysis.nlp_analysis_service import analyze_content
            analysis = analyze_content(result.get('content', ''))
        except Exception as analysis_err:
            current_app.logger.warning(f"NLP 분석 실패 (무시): {analysis_err}")

    # 웹훅 전송 (fire-and-forget — 실패해도 응답에 영향 없음)
    try:
        content_text = result.get('content', '')
        _webhook.send('content.generated', {
            'title': result.get('title', ''),
            'url': url,
            'style': params['style'],
            'model': model,
            'word_count': len(content_text.split()) if content_text else 0,
        })
    except Exception:
        pass  # 웹훅 실패가 응답을 블로킹하면 안 됨

    # 스타일 메모리 프로필 업데이트 (fire-and-forget — 응답 블로킹 금지)
    if g.user_id:
        try:
            import threading
            from services.data.style_memory_service import update_profile as _update_style_profile
            threading.Thread(
                target=_update_style_profile,
                args=(g.user_id, {'style': params['style'], 'modifiers': params.get('modifiers')}),
                daemon=True
            ).start()
        except Exception:
            pass  # 스타일 메모리 업데이트 실패는 응답에 영향 없음

    # 챕터 분할 (타임스탬프 세그먼트가 있을 때만)
    chapters = []
    if transcript_segments:
        try:
            from services.transcript.chapter_service import split_chapters
            chapters = split_chapters(raw_transcript, model, transcript_segments)
        except Exception as ch_err:
            current_app.logger.warning(f"챕터 분할 실패 (무시): {ch_err}")

    # 웹 검색 출처 정보 (result에 포함되어 있으면 응답에 포함)
    web_sources = result.pop('web_sources', None)

    # output_format / max_chars 적용
    result = _apply_output_format(
        result,
        params.get('output_format', 'html'),
        params.get('max_chars'),
    )

    # 콘텐츠 통계 (프론트엔드 카드 메타 칩용)
    _content_text = result.get('content', '')
    _char_count = len(_content_text)
    # 한국어 기준 분당 500자, 최소 1분
    _reading_time_min = max(1, round(_char_count / 500)) if _char_count > 0 else 0
    _content_stats = {
        "char_count": _char_count,
        "word_count": len(_content_text.split()) if _content_text else 0,
        "reading_time_min": _reading_time_min,
    }

    return jsonify({
        **result,
        "id": report_id,
        "source_url": url,
        "prompt": used_prompt,
        "elapsed_time": elapsed_time,
        "youtube_title": youtube_title,
        "transcript": raw_transcript,
        "transcript_source": transcript_source,
        "comment_summary_included": bool(comments and comment_result),
        "seo": seo,
        "geo": geo,
        "faq_schema": faq_schema,
        "cta": cta,
        "json_ld_schemas": json_ld_schemas,
        "quality_score": quality_score,
        "web_sources": web_sources,
        "analysis": analysis,
        "transcript_segments": transcript_segments or [],
        "chapters": chapters,
        "quota": get_usage_for_response(),
        **_content_stats,
        **(agent_meta or {}),
    })


def _process_single_url(app, url, model, style, modifiers, custom_prompt):
    """배치 처리에서 단일 URL을 처리하는 헬퍼 함수입니다.
    API 키는 서버 환경변수에서 자동으로 로드됩니다.
    """
    from routes.blog_routes import _get_style_prompt

    with app.app_context():
        try:
            current_app.logger.info(f"Processing URL: {url}")

            if not content_service.is_youtube_url(url):
                return {
                    'success': False,
                    'url': url,
                    'title': 'URL 오류',
                    'error': '유효한 YouTube URL이 아닙니다.'
                }

            video_id = content_service.get_video_id(url)
            if not video_id:
                return {
                    'success': False,
                    'url': url,
                    'title': 'YouTube 영상',
                    'error': '유효하지 않은 YouTube URL입니다'
                }

            title = content_service.get_content_title(url) or 'YouTube 영상'
            current_app.logger.info(f"Content title: {title}")

            transcript_text, comments, error, raw_transcript, transcript_source, _ = _fetch_youtube_content(video_id)
            if error:
                return {
                    'success': False,
                    'url': url,
                    'title': title,
                    'error': error
                }

            # 배치 처리: 기존 방식(자막+댓글 합성)으로 처리
            content = _build_combined_content(transcript_text, comments)
            max_tokens = get_model_max_tokens(model)
            content = content_service.truncate_text(content, max_tokens)
            style_prompt = _get_style_prompt(style, custom_prompt)

            result, used_prompt = ai_service.create_content(
                content, model, style_prompt,
                return_prompt=True, modifiers=modifiers,
                style_id=style
            )

            return {
                'success': True,
                'url': url,
                'title': result.get('title', title),
                'content': result.get('content', ''),
                'html': result.get('html', ''),
                'prompt': used_prompt,
                'transcript_source': transcript_source
            }

        except Exception as e:
            current_app.logger.error(f"Error processing URL {url}: {e}")
            return {
                'success': False,
                'url': url,
                'title': '오류 발생',
                'error': sanitize_error_for_client(f'처리 중 오류 발생: {str(e)}')
            }
