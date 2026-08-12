"""
콘텐츠 생성 내부 헬퍼 함수 — blog_routes.py에서 분리
"""
import concurrent.futures
import time
import uuid

from flask import current_app, g, jsonify

from services.core import ai_service, content_service
from src.contexts.content_library import save_history_entry as save_history
from services.usage.usage_decorator import get_usage_for_response
from services.platform.webhook_service import WebhookService
from config import get_model_max_tokens, WEBHOOK_URL, WEBHOOK_ENABLED
from utils.responses import api_error, sanitize_error_for_client

_webhook = WebhookService(url=WEBHOOK_URL, enabled=WEBHOOK_ENABLED)


# ==================== 소스별 핸들러 ====================

def _get_style_prompt(style, custom_prompt=None):
    """스타일에 맞는 프롬프트(베이스 규칙 포함)를 반환합니다."""
    if custom_prompt and str(custom_prompt).strip():
        return str(custom_prompt).strip()[:2000]
    from flask import current_app
    from prompts import compose_style_prompt
    style_prompts = current_app.config.get('STYLE_PROMPTS', {})
    return compose_style_prompt(style, style_prompts.get(style, ''))


def _get_style_label(style_id: str) -> str:
    """스타일 ID에 대한 한글 표시명을 반환합니다."""
    from config import STYLE_OPTIONS
    for sid, label in STYLE_OPTIONS:
        if sid == style_id:
            return label
    return style_id


def _truncate_for_model(model_id: str, label: str, source_content: str) -> str:
    """소스 콘텐츠에 라벨을 붙이고 모델 토큰 한도에 맞춰 잘라냅니다."""
    max_tokens = get_model_max_tokens(model_id)
    return content_service.truncate_text(f"[{label}]\n{source_content}", max_tokens)


def _generate_from_source(params: dict, truncated_content: str):
    """소스 핸들러 공통 AI 호출: 스타일 프롬프트 결합 + create_content.

    Returns:
        tuple: (result_dict, used_prompt)
    """
    style_prompt = _get_style_prompt(params['style'], params.get('custom_prompt'))
    return ai_service.create_content(
        truncated_content, params['model'], style_prompt,
        return_prompt=True, modifiers=params['modifiers'],
        style_id=params['style'],
        detail_level=params.get('detail_level'),
    )


def _validate_direct_text_content(direct_content: str) -> str | None:
    """직접 텍스트 입력값을 검증하고, 클라이언트용 한국어 오류를 반환합니다."""
    from config import DIRECT_TEXT_MAX_CHARS, DIRECT_TEXT_MIN_CHARS

    if len((direct_content or '').strip()) < DIRECT_TEXT_MIN_CHARS:
        return f'텍스트를 {DIRECT_TEXT_MIN_CHARS}자 이상 입력해주세요.'

    if len(direct_content or '') > DIRECT_TEXT_MAX_CHARS:
        return (
            f'텍스트가 너무 깁니다. 최대 {DIRECT_TEXT_MAX_CHARS:,}자까지 '
            '입력할 수 있습니다.'
        )

    return None


def _base_generation_response(result: dict, params: dict, start_time: float,
                              used_prompt: str) -> dict:
    """소스 핸들러(직접 텍스트/음성/문서) 공통 응답 필드를 구성합니다.

    소스별 고유 필드(source_type, source_title 등)는 호출 측에서 추가합니다.
    """
    return {
        'id': str(uuid.uuid4()),
        **result,
        'elapsed_time': round(time.time() - start_time, 2),
        'prompt': used_prompt,
        'style_label': _get_style_label(params['style']),
        'cached': False,
        'comment_summary_included': False,
        'has_code_blocks': _has_code_blocks(result),
        'quota': get_usage_for_response(),
    }


def _handle_direct_text(params: dict, start_time: float):
    """직접 텍스트/로컬 미디어 전사 모드."""
    direct_content = params.get('content', '')
    validation_error = _validate_direct_text_content(direct_content)
    if validation_error:
        return api_error(validation_error, 400)

    source_type = params.get('direct_source_type') or 'text'
    source_title = params.get('source_title') or {
        'video': '로컬 영상', 'audio': '로컬 오디오', 'text': '직접 입력 텍스트',
    }.get(source_type, '직접 입력 텍스트')
    transcript_source = params.get('transcript_source') or (
        'whisper' if source_type in {'video', 'audio'} else 'direct_input'
    )
    transcript_segments = params.get('transcript_segments') or []
    detected_language = params.get('detected_language')
    content_label = '로컬 미디어 전사' if source_type in {'video', 'audio'} else '사용자 입력 텍스트'

    truncated_content = _truncate_for_model(params['model'], content_label, direct_content)
    result, used_prompt = _generate_from_source(params, truncated_content)

    result = _apply_output_format(result, params.get('output_format', 'html'), params.get('max_chars'))

    elapsed_time = round(time.time() - start_time, 2)
    report_id = str(uuid.uuid4())
    if g.user_id:
        save_history(g.user_id, {
            'id': report_id,
            'url': '',
            'title': result.get('title') or source_title,
            'style': params['style'],
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'transcript': direct_content[:5000],
            'transcript_source': transcript_source,
            'usage': result.get('usage'),
            'elapsed_time': elapsed_time,
        })

    response = _base_generation_response(result, params, start_time, used_prompt)
    response['id'] = report_id
    response['prompt_length'] = len(used_prompt) if used_prompt else 0
    response['transcript'] = direct_content[:5000]
    response['transcript_source'] = transcript_source
    response['transcript_segments'] = transcript_segments
    response['source_type'] = source_type
    response['source_title'] = source_title
    response['source_meta'] = {
        'source_type': source_type,
        'chars': len(direct_content),
        'quality_score': 1.0,
        'is_auto': source_type in {'video', 'audio'},
    }
    if detected_language:
        response['source_meta']['detected_language'] = detected_language
    return jsonify(response)


def _handle_web_source(params: dict, url: str, source_type: str, start_time: float):
    """비YouTube URL (웹페이지/RSS/arXiv) → 콘텐츠 생성."""
    from services.content.multi_source_collector import SOURCE_WEBPAGE

    if source_type in {SOURCE_WEBPAGE, 'article'}:
        return _handle_article_source(params, url, start_time)

    from services.content.multi_source_collector import collect_content
    collected = collect_content(url, source_type=source_type)
    source_title = collected.get('title') or url
    source_content = collected.get('content', '')
    if not source_content.strip():
        return api_error('콘텐츠를 추출할 수 없습니다. URL을 확인해주세요.', 400)

    content_label = {
        'webpage': '웹페이지 본문', 'rss': 'RSS 피드 내용',
        'arxiv': 'arXiv 논문 초록', 'twitter': 'Twitter 게시물',
        'reddit': 'Reddit 포스트', 'github': 'GitHub README',
        'hackernews': 'Hacker News 게시물', 'podcast': '팟캐스트 전사',
    }.get(source_type, '본문')
    truncated_content = _truncate_for_model(params['model'], content_label, source_content)
    result, used_prompt = _generate_from_source(params, truncated_content)

    elapsed_time = round(time.time() - start_time, 2)

    if g.user_id:
        save_history(g.user_id, {
            'id': str(uuid.uuid4()), 'url': url,
            'title': result.get('title') or source_title,
            'style': params['style'],
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'transcript': source_content[:5000],
            'usage': result.get('usage'),
            'elapsed_time': elapsed_time,
        })

    result = _apply_output_format(result, params.get('output_format', 'html'), params.get('max_chars'))

    response_data = {
        **result,
        'id': str(uuid.uuid4()),
        'prompt': used_prompt,
        'prompt_length': len(used_prompt) if used_prompt else 0,
        'elapsed_time': elapsed_time,
        'source_type': source_type,
        'source_title': source_title,
        'style_label': _get_style_label(params['style']),
        'quota': get_usage_for_response(),
    }
    if params.get('include_transcript'):
        response_data['transcript'] = source_content[:5000]

    return jsonify(response_data)


def _handle_article_source(params: dict, url: str, start_time: float):
    """일반 웹 아티클 → YouTube와 같은 메인 생성 경로로 콘텐츠 생성."""
    from flask import request
    from services.content.article_service import fetch_article

    article = fetch_article(url)
    source_title = article.get('title') or url
    source_content = article.get('text', '')
    source_meta = article.get('source_meta') or {}

    if not source_content.strip():
        return api_error('[아티클 추출 실패] 본문을 찾을 수 없습니다.', 400)

    max_tokens = get_model_max_tokens(params['model'])
    truncated_content = content_service.truncate_text(
        f"[아티클 본문]\n{source_content}",
        max_tokens,
    )
    style_prompt = _get_style_prompt(params['style'], params.get('custom_prompt'))
    request_data = request.get_json(silent=True) or {}
    result, used_prompt, comment_result = _call_ai_with_comments(
        truncated_content,
        params['model'],
        style_prompt,
        params,
        [],
        source_content,
        max_tokens,
        web_search=bool(request_data.get('web_search', False)),
    )

    result = _apply_output_format(
        result,
        params.get('output_format', 'html'),
        params.get('max_chars'),
    )

    elapsed_time = round(time.time() - start_time, 2)
    report_id = str(uuid.uuid4())
    if g.user_id:
        save_history(g.user_id, {
            'id': report_id,
            'url': url,
            'title': result.get('title') or source_title,
            'style': params['style'],
            'content': result.get('content', ''),
            'html': result.get('html', ''),
            'transcript': source_content[:5000],
            'transcript_source': 'article',
            'usage': result.get('usage'),
            'elapsed_time': elapsed_time,
        })

    response = _base_generation_response(result, params, start_time, used_prompt)
    response.update({
        'id': report_id,
        'prompt_length': len(used_prompt) if used_prompt else 0,
        'elapsed_time': elapsed_time,
        'source_type': 'article',
        'source_title': source_title,
        'source_meta': {**source_meta, 'source_type': 'article'},
        'transcript_source': 'article',
        'comment_summary_included': bool(comment_result),
    })
    if params.get('include_transcript'):
        response['transcript'] = source_content[:5000]

    return jsonify(response)


def _has_code_blocks(result: dict) -> bool:
    """결과에 코드 블록이 포함되어 있는지 확인."""
    content = result.get('content', '')
    return bool('```' in content or '<code>' in content)


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

    if max_chars and isinstance(max_chars, int) and max_chars > 0 and result.get('content'):
        result = {**result, 'content': result['content'][:max_chars]}

    return result


def _fetch_youtube_content(video_id, transcript_language=None):
    """YouTube 영상의 자막과 댓글을 분리하여 가져옵니다.
    Supadata API 키는 환경변수에서 자동으로 로드됩니다.

    Args:
        video_id: YouTube 비디오 ID
        transcript_language: 사용자가 지정한 자막 언어 코드('ko'/'en'/'ja' 등). None이면 기존 기본 동작.

    Returns:
        tuple: (transcript_text, comments_list, error, raw_transcript, transcript_source, transcript_segments)
        - comments_list: 댓글 문자열 리스트 (전체) 또는 빈 리스트
        - transcript_source: 'api' | 'watch' | 'supadata' | 'cache'
        - transcript_segments: 타임스탬프 포함 세그먼트 목록 [{'start': float, 'text': str}, ...]
    """
    transcript_result = content_service.get_transcript(video_id, transcript_language=transcript_language)
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


def _handle_cache_hit(cache_key, force, video_id, url, start_time, transcript_language=None):
    """캐시 히트 체크. 히트 시 Response 반환, 아니면 None.

    자막/제목 추출 전에 호출된다 — 히트 시 YouTube 왕복(제목 API + 자막
    추출)을 전부 생략한다. 제목은 캐시 페이로드(신규 저장분)에서, 자막은
    video_id 기반 파일 캐시에서 가져오고, 둘 다 없으면 그때만 조회한다.
    단, transcript_language 지정 시 언어 무관 파일 캐시를 신뢰할 수 없어
    자막 페이로드는 매번 언어 지정 재추출로 채운다 (의도된 트레이드오프).
    """
    if force:
        return None

    cached = current_app.ai_cache.get(cache_key)
    if not cached:
        return None

    g.skip_usage_decrement = True
    elapsed_time = round(time.time() - start_time, 2)
    cached.pop('_cached_at', None)

    transcript_cache = {} if transcript_language else (content_service.get_cached_transcript(video_id) or {})
    raw_transcript = transcript_cache.get('text', '')
    transcript_source = transcript_cache.get('source', 'cache')
    if not raw_transcript:
        # 자막 파일 캐시가 AI 캐시(TTL 30일)보다 먼저 정리된 경우 재추출 폴백
        # — 캐시 응답에도 transcript 페이로드는 항상 포함돼야 한다
        try:
            fetched = content_service.get_transcript(
                video_id, transcript_language=transcript_language
            )
            if fetched and not fetched.get('error'):
                raw_transcript = fetched.get('text', '')
                transcript_source = fetched.get('source', 'cache')
        except Exception:
            pass  # 자막 재추출 실패가 캐시 응답 자체를 막지 않도록

    youtube_title = cached.pop('youtube_title', None)
    if not youtube_title:
        # 구버전 캐시 엔트리 폴백 (신규 저장분은 페이로드에 제목 포함)
        youtube_title = content_service.get_content_title(url) or 'YouTube 영상'

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

    if comments:
        app = current_app._get_current_object()

        # 단일 ChatMock 경로: 메인 생성과 댓글 요약을 병렬 실행
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


def _run_chapter_split(app, raw_transcript, model, transcript_segments):
    """스레드에서 챕터 분할 LLM 호출을 실행합니다 (메인 생성과 병렬)."""
    from services.transcript.chapter_service import split_chapters
    with app.app_context():
        return split_chapters(raw_transcript, model, transcript_segments)


def _persist_generation_result(cache_key, video_id, params, url, youtube_title,
                               result, used_prompt, comment_result,
                               raw_transcript, transcript_source, comments,
                               elapsed_time, report_id, user_id=None):
    """AI 결과 캐시 저장 + 히스토리 저장을 /generate와 /generate-stream에서 공유."""
    import threading

    model = params['model']
    modifiers = params['modifiers'] or {}
    _cache = current_app.ai_cache
    _user_id = user_id if user_id is not None else getattr(g, 'user_id', None)
    _cache_data = {
        'title': result.get('title', ''),
        'content': result.get('content', ''),
        'html': result.get('html', ''),
        'comment_summary_included': bool(comments and comment_result),
        'prompt': used_prompt,
        # 캐시 히트 시 YouTube 제목 API 재호출을 피하기 위해 함께 저장
        'youtube_title': youtube_title,
    }
    for key in ('citations', 'source_receipts'):
        if key in result:
            _cache_data[key] = result.get(key)
    _history_data = {
        'id': report_id,
        'url': url,
        'title': result.get('title', youtube_title),
        'style': params['style'],
        'content': result.get('content', ''),
        'html': result.get('html', ''),
        'transcript': raw_transcript,
        'transcript_source': transcript_source,
        'usage': result.get('usage'),
        'elapsed_time': elapsed_time,
    }

    def _background_save():
        _cache.put(
            cache_key, video_id, params['style'], model,
            modifiers.get('length', 'medium'),
            modifiers.get('writing_style', 'conversational'),
            _cache_data,
        )
        if _user_id:
            save_history(_user_id, _history_data)

    threading.Thread(target=_background_save, daemon=True).start()


def _save_and_respond(result, used_prompt, comment_result, cache_key,
                       video_id, params, url, youtube_title,
                       raw_transcript, transcript_source, comments, start_time,
                       quality_score=None, agent_meta=None,
                       transcript_segments=None, chapter_future=None):
    """캐시 저장 + 히스토리 저장 + JSON 응답 반환."""
    import threading

    model = params['model']

    elapsed_time = round(time.time() - start_time, 2)
    report_id = str(uuid.uuid4())

    # 스트리밍 경로와 동일한 캐시/히스토리 저장 헬퍼 사용
    _persist_generation_result(
        cache_key, video_id, params, url, youtube_title,
        result, used_prompt, comment_result,
        raw_transcript, transcript_source, comments,
        elapsed_time, report_id,
    )

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

    # 웹훅 전송 (백그라운드 — 응답 블로킹 방지)
    _webhook_data = {
        'title': result.get('title', ''),
        'url': url,
        'style': params['style'],
        'model': model,
        'word_count': len(result.get('content', '').split()) if result.get('content') else 0,
    }
    def _background_webhook():
        try:
            _webhook.send('content.generated', _webhook_data)
        except Exception:
            pass
    threading.Thread(target=_background_webhook, daemon=True).start()

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
    # chapter_future가 있으면 메인 생성과 병렬로 이미 실행 중 — 결과만 수거
    chapters = []
    total_duration_seconds = 0
    if transcript_segments:
        try:
            from services.transcript.chapter_service import split_chapters, get_total_duration
            total_duration_seconds = get_total_duration(transcript_segments)
            if chapter_future is not None:
                chapters = chapter_future.result(timeout=120)
            else:
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

    return jsonify({
        **result,
        "id": report_id,
        "prompt": used_prompt,
        "prompt_length": len(used_prompt) if used_prompt else 0,
        "elapsed_time": elapsed_time,
        "youtube_title": youtube_title,
        "transcript": raw_transcript,
        "transcript_source": transcript_source,
        "style_label": _get_style_label(params['style']),
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
        "total_duration_seconds": total_duration_seconds,
        "quota": get_usage_for_response(),
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
