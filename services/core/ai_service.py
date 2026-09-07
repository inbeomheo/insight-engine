"""
AI 콘텐츠 생성 서비스
LiteLLM을 사용한 CLIProxyAPI(OpenAI 호환) 호출 지원
"""
import functools
import html as html_lib
import os
markdown = None  # 지연 로딩 (cold start 최적화)
from datetime import datetime
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo
from flask import current_app

from services.usage.usage_lock import UsageLockUnavailable
from services.core.gateway_service import (
    DEFAULT_GATEWAY_MODEL, apply_gateway_kwargs, canonical_gateway_model,
    require_gateway_connection,
)

# SEO/GEO/FAQ/CTA 메타데이터 추출은 별도 모듈로 분리됨.
# 외부 호환을 위해 동일 이름으로 re-export.
from services.core.ai_metadata import (  # noqa: E402,F401
    extract_cta,
    extract_faq_schema,
    extract_geo_metadata,
    extract_seo_metadata,
)


@functools.lru_cache(maxsize=1)
def _get_completion():
    """litellm.completion을 지연 로딩합니다 (cold start 최적화: ~4초 절감)."""
    from litellm import completion
    return completion

DEFAULT_LANGUAGE_INSTRUCTION = '결과는 반드시 한국어로 작성해주세요.'
CLIPROXYAPI_CONNECTION_HINT = (
    "[CLIProxyAPI 연결 실패] CLIProxyAPI 서버에 연결할 수 없습니다. "
    "CLIProxyAPI의 로그인과 서버 실행 상태를 확인하고 "
    "CLIPROXYAPI_BASE_URL=http://127.0.0.1:8317/v1 및 CLIPROXYAPI_API_KEY 설정을 확인해주세요."
)


def get_public_model_allowlist() -> frozenset[str]:
    """Return the centrally configured model IDs accepted from API clients."""
    from config import SUPPORTED_PROVIDERS

    return frozenset(
        model['id']
        for provider in SUPPORTED_PROVIDERS.values()
        for model in provider.get('models', [])
        if isinstance(model, dict) and isinstance(model.get('id'), str)
    )


def resolve_public_model(
    model: Optional[str],
    default: str = DEFAULT_GATEWAY_MODEL,
    *,
    allow_auto: bool = False,
) -> str:
    """Resolve a client-selected model against the central allow-list.

    This check belongs at paid public AI boundaries.  Internal adapters may
    still use provider-specific IDs while untrusted requests cannot route
    LiteLLM to an arbitrary provider or URL-like model identifier.
    """
    candidate = model.strip() if isinstance(model, str) else ''
    candidate = candidate or default
    if candidate == 'auto':
        if allow_auto:
            return candidate
        candidate = default
    if candidate.startswith('chatmock/'):
        candidate = canonical_gateway_model(candidate)
    allowed = get_public_model_allowlist()
    if candidate not in allowed:
        raise ValueError('지원하지 않는 AI 모델입니다.')
    return candidate

def _build_modifier_instructions(modifiers, style_modifiers):
    """세부 옵션에서 추가 지시사항을 생성합니다.

    v3.1: 3개 모디파이어 지원 (length, writing_style, language)
    language 미지정 시 기본 한국어
    """
    instructions = []

    if not modifiers:
        instructions.append(DEFAULT_LANGUAGE_INSTRUCTION)
        return instructions

    # language 모디파이어 처리 (미지정 시 기본 한국어)
    lang = modifiers.get('language', 'ko')
    lang_options = style_modifiers.get('language', {})
    if lang in lang_options:
        instructions.append(lang_options[lang])
    else:
        instructions.append(DEFAULT_LANGUAGE_INSTRUCTION)

    # length, writing_style 모디파이어
    modifier_types = ['length', 'writing_style']
    for modifier_type in modifier_types:
        value = modifiers.get(modifier_type)
        if value and value in style_modifiers.get(modifier_type, {}):
            instructions.append(style_modifiers[modifier_type][value])

    return instructions


def _get_korean_datetime():
    """현재 한국 시간(KST)을 반환합니다."""
    kst = ZoneInfo("Asia/Seoul")
    now = datetime.now(kst)
    return now.strftime("%Y년 %m월 %d일 %H시 %M분")


def format_transcript_with_timestamps(segments: list) -> str:
    """자막 세그먼트 배열을 '[HH:MM:SS] 텍스트' 형식으로 변환하여 반환합니다.

    AI 프롬프트에 타임스탬프 컨텍스트를 주입하기 위해 사용됩니다.

    Args:
        segments: 자막 세그먼트 목록 [{'start': float, 'text': str}, ...]

    Returns:
        '[HH:MM:SS] 텍스트\\n...' 형식 문자열, 세그먼트가 없으면 빈 문자열
    """
    if not segments:
        return ""
    try:
        from utils.timestamp_utils import format_segments_for_prompt
        return format_segments_for_prompt(segments)
    except Exception:
        return ""


def _build_prompt(content, style_prompt, modifiers, rag_context=None, segments=None, web_context=None, style_memory_context=None, detail_level=None, memory_context=None):
    """프롬프트를 구성합니다.

    배치 순서: 지시(스타일) → 입력(자막/컨텍스트) → 가변 지시(모디파이어/시간).
    정적인 스타일 프롬프트를 맨 앞에 두면 OpenAI 호환 프록시의 프롬프트 처리 안정성이 좋아진다.
    """
    # 타임스탬프 세그먼트가 있으면 타임코드 자막 섹션 추가
    if segments:
        timestamp_text = format_transcript_with_timestamps(segments)
        if timestamp_text:
            content = content + f"\n\n[타임스탬프 자막]\n{timestamp_text}"

    prompt = f"{style_prompt}\n\n{content}" if style_prompt else content

    # 개인 스타일 메모리 컨텍스트 주입 (RAG/웹 앞에 삽입)
    if style_memory_context:
        prompt += f"\n\n{style_memory_context}"

    # AI 메모리 레이어 컨텍스트 주입
    if memory_context:
        prompt += f"\n\n{memory_context}"

    # RAG 참고자료 삽입
    if rag_context:
        prompt += f"\n\n[참고자료]\n다음은 사용자가 제공한 참고 문서에서 검색된 관련 내용입니다. 콘텐츠 작성 시 참고하되, 자막 내용이 우선입니다.\n\n{rag_context}"

    # 웹 검색 보강 컨텍스트 삽입
    if web_context:
        prompt += f"\n\n[웹 참고 자료]\n다음은 자막 주제와 관련된 최신 웹 검색 결과입니다. 콘텐츠 작성 시 사실 보강에 활용하되, 자막 내용이 우선이며 무비판적 수용 금지.\n\n{web_context}"

    style_modifiers = current_app.config.get('STYLE_MODIFIERS', {})
    modifier_instructions = _build_modifier_instructions(modifiers, style_modifiers)

    # 가변 컨텍스트(시간)는 캐싱을 깨지 않도록 프롬프트 끝에 배치
    modifier_instructions.append(f"[현재 시간: {_get_korean_datetime()} (한국 표준시)]")
    prompt += "\n\n[추가 지시사항]\n" + "\n".join(modifier_instructions)

    # 상세도 프리셋 suffix 추가
    if detail_level:
        from config import DETAIL_PRESETS
        detail = DETAIL_PRESETS.get(detail_level, DETAIL_PRESETS['standard'])
        suffix = detail.get('prompt_suffix', '')
        if suffix:
            prompt += f"\n\n[상세도 지시]\n{suffix}"

    return prompt


def _build_completion_kwargs(model, prompt, style_id=None, modifiers=None, stream=False, detail_level=None):
    """LiteLLM completion 호출용 kwargs 빌드 (DRY)"""
    from config import STYLE_TEMPERATURE, LENGTH_MAX_TOKENS, DETAIL_PRESETS

    request_timeout = int(os.getenv('AI_REQUEST_TIMEOUT', '300'))
    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": request_timeout,
    }
    if stream:
        kwargs["stream"] = True
        kwargs["stream_options"] = {"include_usage": True}

    detail = DETAIL_PRESETS.get(detail_level, DETAIL_PRESETS['standard'])
    base_temp = STYLE_TEMPERATURE.get(style_id, 0.7)
    kwargs["temperature"] = max(0.0, min(1.0, base_temp + detail['temperature_offset']))

    length = (modifiers or {}).get('length', 'medium')
    base_tokens = LENGTH_MAX_TOKENS.get(length, 4000)
    kwargs["max_tokens"] = int(base_tokens * detail['max_tokens_multiplier'])

    apply_gateway_kwargs(kwargs, model)

    return kwargs


def call_litellm(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Any:
    """Call the shared CLIProxyAPI/LiteLLM boundary for legacy AI services.

    Repurposing and realtime translation historically imported this helper.
    Keeping them on the same boundary preserves proxy configuration and usage
    lease validation instead of letting each service call LiteLLM directly.
    """
    target_model = model or DEFAULT_GATEWAY_MODEL
    completion_kwargs = _build_completion_kwargs(
        target_model,
        "",
        style_id="summary",
        modifiers={"length": "medium"},
    )
    completion_kwargs["messages"] = messages
    completion_kwargs["max_tokens"] = max_tokens
    if "temperature" in completion_kwargs:
        completion_kwargs["temperature"] = temperature
    return _call_completion_with_model_retry(
        target_model,
        completion_kwargs,
        on_cost_start=on_cost_start,
    )


def _call_completion_with_model_retry(
    model: str,
    completion_kwargs: Dict[str, Any],
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Any:
    """LiteLLM completion을 호출합니다. 단일 CLIProxyAPI 경로를 사용합니다."""
    completion = _get_completion()

    # 함수 로딩·인자 구성 실패는 무비용으로 남기고, 실제 외부 AI
    # 호출을 시작하는 순간부터는 응답 성공 여부와 관계없이 예약을 차감한다.
    from services.usage.usage_decorator import mark_usage_charge_committed

    if callable(on_cost_start):
        on_cost_start()
    else:
        mark_usage_charge_committed()
    return completion(**completion_kwargs)


def _extract_title_and_content(markdown_content):
    """마크다운에서 제목과 본문을 분리합니다."""
    title = "AI 생성 결과"
    lines = markdown_content.split('\n')

    if lines and lines[0].startswith('#'):
        title = lines[0].lstrip('#').strip()
        markdown_content = '\n'.join(lines[1:]).strip()

    return title, markdown_content


def _convert_error_message(error_msg, model=None):
    """API 에러 메시지를 사용자 친화적인 한국어로 변환합니다."""
    error_lower = error_msg.lower()
    model_info = f" (모델: {model})" if model else ""

    if model and any(
        marker in error_lower
        for marker in (
            "connection", "connect", "refused", "winerror 10061",
            "failed to establish", "httpconnectionpool", "server disconnected",
        )
    ):
        return CLIPROXYAPI_CONNECTION_HINT

    # 인증 관련
    if 'invalid_api_key' in error_lower or 'authentication' in error_lower or 'unauthorized' in error_lower:
        return f"[인증 실패] API 키가 유효하지 않습니다{model_info}. 환경변수를 확인해주세요."

    # 사용량 제한
    if 'rate_limit' in error_lower or 'quota' in error_lower or 'too many requests' in error_lower or '429' in error_lower:
        return f"[사용량 초과] API 요청 한도에 도달했습니다{model_info}. 잠시 후 다시 시도해주세요."

    # 모델 관련
    if 'model' in error_lower and ('not found' in error_lower or 'does not exist' in error_lower):
        return f"[모델 오류] 선택한 모델을 찾을 수 없습니다{model_info}. 다른 모델을 선택해주세요."

    # 연결/타임아웃
    if 'timeout' in error_lower or 'timed out' in error_lower:
        return f"[타임아웃] AI 서버 응답 시간 초과{model_info}. 다시 시도해주세요."

    if 'connection' in error_lower or 'connect' in error_lower:
        return f"[연결 실패] AI 서버에 연결할 수 없습니다{model_info}. 네트워크 상태를 확인하거나 다시 시도해주세요."

    # 서비스 불가
    if ('service' in error_lower and 'unavailable' in error_lower) or '503' in error_lower:
        return f"[서비스 불가] AI 서비스가 일시적으로 불가합니다{model_info}. 잠시 후 다시 시도해주세요."

    if '500' in error_lower or 'internal' in error_lower:
        return f"[서버 오류] AI 서버 내부 오류{model_info}. 잠시 후 다시 시도해주세요."

    # 잔액 부족
    if 'insufficient' in error_lower or 'balance' in error_lower or 'credit' in error_lower:
        return f"[잔액 부족] API 크레딧이 부족합니다{model_info}. 충전이 필요합니다."

    # 컨텐츠 정책
    if 'content' in error_lower and ('policy' in error_lower or 'filter' in error_lower or 'blocked' in error_lower):
        return f"[컨텐츠 차단] 요청이 컨텐츠 정책에 의해 차단되었습니다{model_info}."

    # 기타 - 원본 메시지 포함
    return f"[AI 오류] 콘텐츠 생성 실패{model_info}: {error_msg}"


def create_content(content: str, model: str, style_prompt: Optional[str] = None, return_prompt: bool = False,
                   modifiers: Optional[Dict[str, Any]] = None, style_id: Optional[str] = None,
                   user_id: Optional[str] = None, segments: Optional[List[Dict[str, Any]]] = None,
                   web_search: bool = False, detail_level: Optional[str] = None,
                   on_cost_start: Optional[Callable[[], None]] = None) -> Union[Dict[str, Any], Tuple[Dict[str, Any], str]]:
    """
    LiteLLM을 사용하여 CLIProxyAPI(OpenAI 호환)로 AI 콘텐츠를 생성합니다.
    CLIProxyAPI 서버 기본 URL은 CLIPROXYAPI_BASE_URL 환경변수로 조정할 수 있습니다.

    Args:
        content: 분석할 콘텐츠 (자막 + 댓글)
        model: 모델 ID (예: 'cliproxyapi/gpt-5.5')
        style_prompt: 스타일 프롬프트
        return_prompt: 사용된 프롬프트 반환 여부
        modifiers: 세부 옵션 딕셔너리 (length, writing_style)
        style_id: 스타일 ID (temperature 매핑용)
        user_id: 사용자 ID (RAG 컨텍스트 검색용)
        segments: 자막 세그먼트 목록 [{'start': float, 'text': str}, ...] (타임스탬프 주입용)
        web_search: 웹 검색 보강 활성화 여부

    Returns:
        dict 또는 tuple: 생성 결과 (return_prompt=True면 (result, prompt) 튜플)
        결과에 'web_sources'가 포함될 수 있음 (웹 검색 활성화 시)
    """
    try:
        # 독립적인 컨텍스트 빌드들을 병렬 실행 (150-600ms 절감)
        require_gateway_connection()
        from services.core.ai_prompt_context import build_optional_prompt_contexts
        rag_context, web_context, web_sources, style_memory_context, memory_context = (
            build_optional_prompt_contexts(
                content,
                user_id=user_id,
                web_search=web_search,
                on_cost_start=on_cost_start,
            )
        )

        prompt = _build_prompt(content, style_prompt, modifiers, rag_context=rag_context,
                               segments=segments, web_context=web_context,
                               style_memory_context=style_memory_context,
                               detail_level=detail_level,
                               memory_context=memory_context)
        completion_kwargs = _build_completion_kwargs(model, prompt, style_id, modifiers,
                                                     detail_level=detail_level)
        response = _call_completion_with_model_retry(
            model,
            completion_kwargs,
            on_cost_start=on_cost_start,
        )

        markdown_content = response.choices[0].message.content
        title, body = _extract_title_and_content(markdown_content)

        # 토큰 사용량 정보 추출 (기본값 설정으로 None 방지)
        token_usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
        usage = getattr(response, 'usage', None)
        if usage:
            token_usage = {
                'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(usage, 'completion_tokens', 0),
                'total_tokens': getattr(usage, 'total_tokens', 0)
            }

        # P3 버그 #11: 마크다운 렌더링 폴백
        try:
            global markdown
            if markdown is None:
                import markdown as _md
                markdown = _md
            html = markdown.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])
        except Exception as md_err:
            current_app.logger.warning(f"마크다운 변환 실패: {md_err}")
            html = f"<pre>{html_lib.escape(body)}</pre>"

        result = {
            'title': title,
            'content': body,
            'html': html,
            'usage': token_usage
        }

        # 웹 검색 출처 정보 포함
        if web_sources:
            result['web_sources'] = web_sources

        if return_prompt:
            return result, prompt
        return result

    except UsageLockUnavailable:
        raise
    except Exception as e:
        current_app.logger.error(f"AI content generation failed: model={model}, error={e}")
        raise Exception(_convert_error_message(str(e), model)) from e


def create_content_stream(content: str, model: str, style_prompt: Optional[str] = None,
                          modifiers: Optional[Dict[str, Any]] = None, style_id: Optional[str] = None,
                          detail_level: Optional[str] = None,
                          user_id: Optional[str] = None,
                          segments: Optional[List[Dict[str, Any]]] = None,
                          web_search: bool = False,
                          on_cost_start: Optional[Callable[[], None]] = None) -> Generator[str, None, Dict[str, Any]]:
    """LiteLLM 스트리밍 콘텐츠 생성 래퍼. 실제 구현은 ai_streaming 모듈에 위임합니다."""
    from services.core.ai_streaming import create_content_stream as _create_content_stream

    return _create_content_stream(
        content, model, style_prompt,
        modifiers=modifiers, style_id=style_id, detail_level=detail_level,
        user_id=user_id, segments=segments, web_search=web_search,
        on_cost_start=on_cost_start,
    )

def create_chat_response(
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 1200,
    temperature: float = 0.2,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> Dict[str, Any]:
    """LiteLLM chat completion thin wrapper."""
    try:
        completion_kwargs = _build_completion_kwargs(
            model,
            "",
            style_id="summary",
            modifiers={"length": "short", "language": "ko"},
        )
        completion_kwargs["messages"] = messages
        completion_kwargs["max_tokens"] = max_tokens
        completion_kwargs["temperature"] = temperature

        response = _call_completion_with_model_retry(
            model,
            completion_kwargs,
            on_cost_start=on_cost_start,
        )
        answer = response.choices[0].message.content or ""

        usage_data = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        usage = getattr(response, "usage", None)
        if usage:
            usage_data = {
                "prompt_tokens": getattr(usage, "prompt_tokens", 0),
                "completion_tokens": getattr(usage, "completion_tokens", 0),
                "total_tokens": getattr(usage, "total_tokens", 0),
            }

        return {"answer": answer.strip(), "usage": usage_data}
    except UsageLockUnavailable:
        raise
    except Exception as e:
        current_app.logger.error(f"AI chat failed: model={model}, error={e}")
        raise Exception(_convert_error_message(str(e), model)) from e


def create_content_with_fallback(content: str, models: List[str], style_prompt: Optional[str] = None,
                                 return_prompt: bool = False, modifiers: Optional[Dict[str, Any]] = None,
                                 style_id: Optional[str] = None, user_id: Optional[str] = None,
                                 on_cost_start: Optional[Callable[[], None]] = None) -> Union[Dict[str, Any], Tuple[Dict[str, Any], str]]:
    """
    모델 리스트를 순차 시도하여 첫 성공 결과를 반환합니다.
    API 키가 없는 모델은 자동 스킵합니다.

    Args:
        content: 분석할 콘텐츠
        models: 시도할 모델 ID 리스트 (폴백 순서)
        style_prompt: 스타일 프롬프트
        return_prompt: 사용된 프롬프트 반환 여부
        modifiers: 세부 옵션
        style_id: 스타일 ID

    Returns:
        dict 또는 tuple: 생성 결과 (return_prompt=True면 (result, prompt) 튜플)
        결과에 'used_model' 키가 추가됨
    """
    from config import PROVIDER_API_KEYS, MAX_FALLBACK_ATTEMPTS, get_provider_from_model

    # API 키가 있는 모델만 필터링
    available_models = []
    for model_id in models:
        # 모델 ID 접두사와 PROVIDER_API_KEYS 키가 다를 수 있어 헬퍼로 프로바이더를 추출한다.
        provider = get_provider_from_model(model_id)
        api_key = PROVIDER_API_KEYS.get(provider, '')
        if api_key:
            available_models.append(model_id)

    if not available_models:
        raise Exception("[AI 오류] 사용 가능한 모델이 없습니다. API 키를 확인해주세요.")

    # 최대 시도 횟수 제한
    attempts = min(len(available_models), MAX_FALLBACK_ATTEMPTS)
    errors = []

    for model_id in available_models[:attempts]:
        try:
            current_app.logger.info(f"폴백 체인 시도: {model_id}")
            result = create_content(
                content, model_id, style_prompt,
                return_prompt=return_prompt, modifiers=modifiers,
                style_id=style_id, user_id=user_id,
                on_cost_start=on_cost_start,
            )

            # 결과에 사용된 모델 정보 추가
            if return_prompt:
                result_dict, prompt = result
                result_dict['used_model'] = model_id
                return result_dict, prompt
            else:
                result['used_model'] = model_id
                return result

        except UsageLockUnavailable:
            raise
        except Exception as e:
            errors.append(f"{model_id}: {str(e)}")
            current_app.logger.warning(f"폴백 체인 실패 ({model_id}): {e}")
            continue

    # 모든 모델 실패
    error_detail = '; '.join(errors)
    raise Exception(f"[AI 오류] 모든 모델이 실패했습니다. ({error_detail})")


def create_full_blog_post(content: str, model_name: str = DEFAULT_GATEWAY_MODEL, style_prompt: Optional[str] = None, return_prompt: bool = False) -> Dict[str, Any]:
    """
    하위 호환성을 위한 래퍼 함수입니다.
    API 키는 환경변수에서 자동으로 로드됩니다.
    """
    return create_content(content, model_name, style_prompt, return_prompt)
