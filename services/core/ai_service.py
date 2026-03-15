"""
AI 콘텐츠 생성 서비스
LiteLLM을 사용한 다중 AI 프로바이더 지원
"""
import html as html_lib
import os
import re
import time
import markdown
import threading
from datetime import datetime
from typing import Any, Dict, Generator, List, Optional, Tuple, Union
from zoneinfo import ZoneInfo
from flask import current_app
from litellm import completion

# Zhipu AI (GLM) OpenAI 호환 API 설정
ZHIPUAI_API_BASE = 'https://open.bigmodel.cn/api/paas/v4/'

# GLM 모델 동시성 제한 - 한 번에 하나의 요청만 처리
_glm_lock = threading.Lock()

# GLM 재시도 설정
GLM_RETRY_COUNT = 5
GLM_RETRY_DELAY = 10  # 초

DEFAULT_LANGUAGE_INSTRUCTION = '결과는 반드시 한국어로 작성해주세요.'


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
    """프롬프트를 구성합니다."""
    # 현재 한국 시간 추가
    current_time = _get_korean_datetime()
    time_context = f"[현재 시간: {current_time} (한국 표준시)]"

    # 타임스탬프 세그먼트가 있으면 타임코드 형식으로 자막 교체
    if segments:
        timestamp_text = format_transcript_with_timestamps(segments)
        if timestamp_text:
            # 기존 content에서 자막 부분을 타임코드 버전으로 대체
            content = content + f"\n\n[타임스탬프 자막]\n{timestamp_text}"

    prompt = f"{time_context}\n\n{content}\n\n{style_prompt}" if style_prompt else f"{time_context}\n\n{content}"

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

    if modifier_instructions:
        prompt += "\n\n[추가 지시사항]\n" + "\n".join(modifier_instructions)

    # 상세도 프리셋 suffix 추가
    if detail_level:
        from config import DETAIL_PRESETS
        detail = DETAIL_PRESETS.get(detail_level, DETAIL_PRESETS['standard'])
        suffix = detail.get('prompt_suffix', '')
        if suffix:
            prompt += f"\n\n[상세도 지시]\n{suffix}"

    return prompt


def _extract_keywords(content):
    """마크다운에서 <!-- KEYWORDS: ... --> 주석을 파싱하여 키워드 추출 후 본문에서 제거합니다.

    Returns:
        tuple: (cleaned_content, keywords_list)
    """
    pattern = r'<!--\s*KEYWORDS:\s*(.+?)\s*-->'
    match = re.search(pattern, content)
    if not match:
        return content, []

    raw = match.group(1)
    keywords = [kw.strip()[:20] for kw in raw.split(',') if kw.strip()][:10]
    cleaned = re.sub(pattern, '', content).strip()
    return cleaned, keywords


def _build_completion_kwargs(model, prompt, style_id=None, modifiers=None, stream=False, detail_level=None):
    """LiteLLM completion 호출용 kwargs 빌드 (DRY)"""
    from config import STYLE_TEMPERATURE, LENGTH_MAX_TOKENS, DETAIL_PRESETS

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "timeout": 300,  # 5분 타임아웃 (GLM 느린 응답 대비)
    }
    if stream:
        kwargs["stream"] = True

    detail = DETAIL_PRESETS.get(detail_level, DETAIL_PRESETS['standard'])
    base_temp = STYLE_TEMPERATURE.get(style_id, 0.7)
    kwargs["temperature"] = max(0.0, min(1.0, base_temp + detail['temperature_offset']))

    length = (modifiers or {}).get('length', 'medium')
    base_tokens = LENGTH_MAX_TOKENS.get(length, 4000)
    kwargs["max_tokens"] = int(base_tokens * detail['max_tokens_multiplier'])

    if model.startswith("gemini/") and "lite" not in model.lower():
        kwargs["reasoning_effort"] = "minimal"

    # GLM → OpenAI 호환 API 변환
    if model.startswith("zhipuai/"):
        zhipuai_key = os.getenv("ZHIPUAI_API_KEY")
        if not zhipuai_key:
            raise ValueError("ZHIPUAI_API_KEY 환경변수가 설정되지 않았습니다.")
        kwargs["model"] = f"openai/{model.replace('zhipuai/', '')}"
        kwargs["api_base"] = ZHIPUAI_API_BASE
        kwargs["api_key"] = zhipuai_key

    # Ollama → api_base 설정 (API 키 불필요)
    if model.startswith("ollama_chat/") or model.startswith("ollama/"):
        kwargs["api_base"] = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

    # ChatMock → OpenAI 호환 프록시 (ChatGPT 구독 기반)
    if model.startswith("chatmock/"):
        actual_model = model.replace("chatmock/", "")
        kwargs["model"] = actual_model
        kwargs["api_base"] = os.getenv("CHATMOCK_BASE_URL", "http://127.0.0.1:8000/v1")
        kwargs["api_key"] = "dummy"
        kwargs["reasoning_effort"] = "medium"
        kwargs.pop("temperature", None)
        kwargs["drop_params"] = True

    # OpenRouter → api_base + API 키 설정
    if model.startswith("openrouter/"):
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            raise ValueError("OPENROUTER_API_KEY 환경변수가 설정되지 않았습니다.")
        kwargs["api_base"] = "https://openrouter.ai/api/v1"
        kwargs["api_key"] = openrouter_key

    return kwargs


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

    # Zhipu AI 관련 에러
    if '1113' in error_msg:
        return f"[권한 없음] 해당 모델에 대한 접근 권한이 없습니다{model_info}. API 키 권한을 확인해주세요."
    if '1211' in error_msg:
        return f"[모델 없음] 요청한 모델이 존재하지 않습니다{model_info}. 모델명을 확인해주세요."
    if '1302' in error_msg:
        return f"[동시성 초과] 동시 요청 수가 초과되었습니다{model_info}. 잠시 후 다시 시도해주세요."

    # 기타 - 원본 메시지 포함
    return f"[AI 오류] 콘텐츠 생성 실패{model_info}: {error_msg}"


def create_content(content: str, model: str, style_prompt: Optional[str] = None, return_prompt: bool = False,
                   modifiers: Optional[Dict[str, Any]] = None, style_id: Optional[str] = None,
                   user_id: Optional[str] = None, segments: Optional[List[Dict[str, Any]]] = None,
                   web_search: bool = False, detail_level: Optional[str] = None) -> Union[Dict[str, Any], Tuple[Dict[str, Any], str]]:
    """
    LiteLLM을 사용하여 AI 콘텐츠를 생성합니다.
    API 키는 환경변수에서 자동으로 로드됩니다 (OPENAI_API_KEY, ANTHROPIC_API_KEY 등).

    Args:
        content: 분석할 콘텐츠 (자막 + 댓글)
        model: 모델 ID (예: 'gpt-4o', 'claude-sonnet-4-20250514')
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
        # RAG 컨텍스트 빌드 (RAG_ENABLED=True이고 user_id가 있을 때)
        rag_context = None
        from config import RAG_ENABLED, RAG_TOP_K, WEB_SEARCH_ENABLED
        if RAG_ENABLED and user_id:
            try:
                from services.rag import context_builder
                rag_context = context_builder.build_context(user_id, content[:500], top_k=RAG_TOP_K)
            except Exception as rag_err:
                current_app.logger.warning(f"RAG 컨텍스트 빌드 실패 (무시): {rag_err}")

        # 웹 검색 보강 컨텍스트 빌드
        web_context = None
        web_sources = []
        if web_search or WEB_SEARCH_ENABLED:
            try:
                from services.data.web_search_service import extract_grounding_context
                grounding = extract_grounding_context(content[:300])
                if grounding['enabled']:
                    web_context = grounding['context_text']
                    web_sources = grounding['results']
                    current_app.logger.info(f"웹 검색 보강: {len(web_sources)}개 결과 주입")
            except Exception as ws_err:
                current_app.logger.warning(f"웹 검색 보강 실패 (무시): {ws_err}")

        # 개인 스타일 메모리 컨텍스트 빌드 (user_id가 있을 때)
        style_memory_context = None
        if user_id:
            try:
                from services.data.style_memory_service import get_profile, build_style_context
                profile = get_profile(user_id)
                style_memory_context = build_style_context(profile) or None
            except Exception as sm_err:
                current_app.logger.warning(f"스타일 메모리 컨텍스트 빌드 실패 (무시): {sm_err}")

        # AI 메모리 레이어 컨텍스트 주입 (user_id가 있을 때)
        memory_context = None
        if user_id:
            try:
                from services.data.memory_service import memory_service
                memory_context = memory_service.build_prompt_context(user_id) or None
            except Exception as mem_err:
                current_app.logger.warning(f"메모리 컨텍스트 빌드 실패 (무시): {mem_err}")

        prompt = _build_prompt(content, style_prompt, modifiers, rag_context=rag_context,
                               segments=segments, web_context=web_context,
                               style_memory_context=style_memory_context,
                               detail_level=detail_level,
                               memory_context=memory_context)
        completion_kwargs = _build_completion_kwargs(model, prompt, style_id, modifiers,
                                                     detail_level=detail_level)
        is_glm = model.startswith("zhipuai/")

        # GLM 모델은 동시성 제한으로 순차 처리 (락은 호출 시만, sleep은 밖에서)
        if is_glm:
            last_error = None
            for attempt in range(GLM_RETRY_COUNT):
                with _glm_lock:
                    try:
                        response = completion(**completion_kwargs)
                        current_app.logger.info(f"GLM 성공 (시도 {attempt + 1}): {model}")
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e)
                        if '1302' not in error_str or attempt >= GLM_RETRY_COUNT - 1:
                            raise
                        current_app.logger.warning(
                            f"GLM 동시성 에러, {GLM_RETRY_DELAY}초 후 재시도 "
                            f"({attempt + 1}/{GLM_RETRY_COUNT}): {model}"
                        )
                # sleep은 락 밖에서 (다른 요청 블로킹 방지)
                time.sleep(GLM_RETRY_DELAY)
            else:
                raise last_error
        else:
            response = completion(**completion_kwargs)

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

    except Exception as e:
        current_app.logger.error(f"AI content generation failed: model={model}, error={e}")
        raise Exception(_convert_error_message(str(e), model)) from e


def create_content_stream(content: str, model: str, style_prompt: Optional[str] = None,
                          modifiers: Optional[Dict[str, Any]] = None, style_id: Optional[str] = None,
                          detail_level: Optional[str] = None) -> Generator[Optional[str], None, None]:
    """
    LiteLLM 스트리밍으로 AI 콘텐츠를 생성합니다.
    각 토큰을 yield하고, 마지막에 None을 yield합니다.
    GLM 모델은 스트리밍 미지원 → 일반 호출 후 전체 텍스트 한 번에 yield.

    Yields:
        str: 토큰 텍스트 또는 None(종료)
    """
    prompt = _build_prompt(content, style_prompt, modifiers, detail_level=detail_level)
    is_glm = model.startswith("zhipuai/")

    # GLM 모델: 스트리밍 미지원, 일반 호출 후 전체 yield
    if is_glm:
        result = create_content(content, model, style_prompt, modifiers=modifiers, style_id=style_id, detail_level=detail_level)
        full_text = f"# {result.get('title', '')}\n\n{result.get('content', '')}"
        yield full_text
        yield None
        return

    try:
        completion_kwargs = _build_completion_kwargs(model, prompt, style_id, modifiers, stream=True, detail_level=detail_level)
        response = completion(**completion_kwargs)

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield delta.content

        yield None  # 스트림 종료 신호

    except Exception as e:
        current_app.logger.error(f"Streaming failed: model={model}, error={e}")
        raise Exception(_convert_error_message(str(e), model)) from e


def create_content_with_fallback(content: str, models: List[str], style_prompt: Optional[str] = None,
                                 return_prompt: bool = False, modifiers: Optional[Dict[str, Any]] = None,
                                 style_id: Optional[str] = None, user_id: Optional[str] = None) -> Union[Dict[str, Any], Tuple[Dict[str, Any], str]]:
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
    from config import PROVIDER_API_KEYS, MAX_FALLBACK_ATTEMPTS

    # API 키가 있는 모델만 필터링
    available_models = []
    for model_id in models:
        provider = model_id.split('/')[0] if '/' in model_id else ''
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
                style_id=style_id, user_id=user_id
            )

            # 결과에 사용된 모델 정보 추가
            if return_prompt:
                result_dict, prompt = result
                result_dict['used_model'] = model_id
                return result_dict, prompt
            else:
                result['used_model'] = model_id
                return result

        except Exception as e:
            errors.append(f"{model_id}: {str(e)}")
            current_app.logger.warning(f"폴백 체인 실패 ({model_id}): {e}")
            continue

    # 모든 모델 실패
    error_detail = '; '.join(errors)
    raise Exception(f"[AI 오류] 모든 모델이 실패했습니다. ({error_detail})")


def extract_seo_metadata(content: str) -> Optional[Dict[str, Any]]:
    """blog_seo 스타일 콘텐츠에서 SEO 메타데이터를 정규식으로 추출합니다.

    Args:
        content: 마크다운 본문

    Returns:
        dict 또는 None: {meta_description, keywords, slug, tags}
    """
    import re

    if not content:
        return None

    seo = {}

    # 메타 설명
    meta_match = re.search(r'\*\*메타 설명\*\*\s*\|?\s*(.+?)(?:\s*\||\n)', content)
    if meta_match:
        seo['meta_description'] = meta_match.group(1).strip()

    # 타겟 키워드
    kw_match = re.search(r'\*\*타겟 키워드\*\*\s*\|?\s*(.+?)(?:\s*\||\n)', content)
    if kw_match:
        raw = kw_match.group(1).strip()
        # "메인: X, 연관: Y, Z" 또는 "X, Y, Z" 형식 파싱
        raw = re.sub(r'메인\s*[:：]\s*', '', raw)
        raw = re.sub(r'연관\s*[:：]\s*', '', raw)
        keywords = [k.strip().strip('[]') for k in raw.split(',') if k.strip()]
        seo['keywords'] = keywords

    # 추천 URL 슬러그
    slug_match = re.search(r'\*\*추천 URL\*\*\s*\|?\s*(/?.+?)(?:\s*\||\n)', content)
    if slug_match:
        seo['slug'] = slug_match.group(1).strip().strip('/')

    # 태그 (#태그 형식)
    tag_match = re.search(r'(?:\*\*태그\*\*|#태그|태그\s*[:：])\s*(.+?)(?:\n|$)', content)
    if tag_match:
        raw_tags = tag_match.group(1).strip()
        tags = re.findall(r'#([\w가-힣]+)', raw_tags)
        if tags:
            seo['tags'] = tags

    # 최소 1개 필드 파싱 성공 시 반환
    return seo if seo else None


def extract_geo_metadata(content: str) -> Optional[Dict[str, Any]]:
    """geo_seo 스타일 콘텐츠에서 GEO 메타데이터를 정규식으로 추출합니다.

    Args:
        content: 마크다운 본문

    Returns:
        dict 또는 None: {citations, structured_data, entity_tags, key_facts}
    """
    import re

    if not content:
        return None

    geo = {}

    # 주요 팩트 (✓ 로 시작하는 줄)
    facts = re.findall(r'[-•✓]\s*✓?\s*(.+?)(?:\n|$)', content)
    if facts:
        geo['key_facts'] = [f.strip() for f in facts if f.strip()]

    # 구조화 데이터 (마크다운 테이블에서 추출 — "구조화 데이터" 섹션)
    table_section = re.search(
        r'###\s*구조화\s*데이터\s*\n((?:\|.+\|\n?)+)',
        content
    )
    if table_section:
        rows = table_section.group(1).strip().split('\n')
        structured = {}
        for row in rows:
            cells = [c.strip().strip('*') for c in row.split('|') if c.strip()]
            if len(cells) >= 2 and '---' not in cells[0]:
                key = cells[0].strip()
                val = cells[1].strip()
                if key and val and key != '항목' and key != '내용':
                    structured[key] = val
        if structured:
            geo['structured_data'] = structured

    # 엔티티 태그 (백틱으로 감싼 태그들 — "엔티티 태그" 섹션)
    tag_section = re.search(r'###\s*엔티티\s*태그\s*\n(.+?)(?:\n\n|\n---|\n###|$)', content, re.DOTALL)
    if tag_section:
        raw_tags = tag_section.group(1).strip()
        tags = re.findall(r'`([^`]+)`', raw_tags)
        if tags:
            geo['entity_tags'] = [t.strip() for t in tags]

    # 인용문 (핵심 요약 + Q&A 답변에서 추출 — 첫 문장들)
    citations = []

    # 한 줄 정의
    definition = re.search(r'###\s*한 줄 정의\s*\n>\s*(.+?)(?:\n|$)', content)
    if definition:
        citations.append(definition.group(1).strip())

    # Q&A 답변의 첫 문장
    qa_answers = re.findall(r'A\.\s*(.+?)(?:\n|$)', content)
    for ans in qa_answers:
        text = ans.strip()
        if text and len(text) > 10:
            citations.append(text)

    if citations:
        geo['citations'] = citations

    # 최소 1개 필드 파싱 성공 시 반환
    return geo if geo else None


def extract_faq_schema(content: str) -> Optional[Dict[str, Any]]:
    """마크다운 본문에서 FAQ Q&A를 파싱하여 JSON-LD FAQPage 스키마를 반환합니다.

    "### 자주 묻는 질문" 섹션의 **Q. ...?** / A. ... 패턴을 인식합니다.

    Args:
        content: 마크다운 본문 문자열

    Returns:
        dict 또는 None: JSON-LD FAQPage 스키마 dict, Q&A가 없으면 None
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": "질문", "acceptedAnswer": {"@type": "Answer", "text": "답변"}},
                ...
            ]
        }
    """
    if not content:
        return None

    # Q&A 패턴 추출: **Q. 질문?** 다음 줄에 A. 답변
    qa_pattern = re.compile(
        r'\*\*Q\.\s*(.+?)\*\*\s*\n\s*A\.\s*(.+?)(?=\n\s*\*\*Q\.|\n---|\n##|\Z)',
        re.DOTALL
    )
    matches = qa_pattern.findall(content)

    if not matches:
        return None

    entities = []
    for question, answer in matches:
        q_text = question.strip()
        a_text = ' '.join(answer.strip().split())  # 줄바꿈 정규화
        if q_text and a_text:
            entities.append({
                "@type": "Question",
                "name": q_text,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a_text
                }
            })

    if not entities:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities
    }


def extract_cta(content: str) -> Optional[Dict[str, str]]:
    """geo_seo 스타일 콘텐츠에서 CTA 문구를 추출합니다.

    **CTA_PRIMARY**: ... / **CTA_SECONDARY**: ... 패턴을 인식합니다.

    Args:
        content: 마크다운 본문 문자열

    Returns:
        dict 또는 None: {"primary": "...", "secondary": "..."} 또는 None
    """
    if not content:
        return None

    cta = {}

    primary_match = re.search(r'\*\*CTA_PRIMARY\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
    if primary_match:
        cta['primary'] = primary_match.group(1).strip()

    secondary_match = re.search(r'\*\*CTA_SECONDARY\*\*\s*[:：]\s*(.+?)(?:\n|$)', content)
    if secondary_match:
        cta['secondary'] = secondary_match.group(1).strip()

    return cta if cta else None


def inline_edit(content: str, selection: str, instruction: str, model: str, context: str = '') -> dict:
    """선택 영역을 AI로 부분 편집합니다.

    Args:
        content: 전체 콘텐츠
        selection: 선택된 텍스트
        instruction: 편집 지시 (축약/확장/톤변경/번역)
        model: AI 모델 ID
        context: 주변 맥락 (선택)

    Returns:
        {'original': str, 'edited': str, 'full_content': str}
    """
    prompt = f"""다음 텍스트의 선택된 부분만 수정해주세요.

## 전체 텍스트 (맥락 참고용)
{content[:2000]}

## 선택된 부분
{selection}

## 수정 지시
{instruction}

## 규칙
- 선택된 부분만 수정하고 나머지는 그대로 유지
- 수정된 텍스트만 출력 (다른 설명 없이)
"""
    result = create_content(prompt, model, style_prompt='', style_id='summary')
    edited = result.get('content', '').strip()
    full_content = content.replace(selection, edited, 1)

    return {
        'original': selection,
        'edited': edited,
        'full_content': full_content,
    }


def create_full_blog_post(content: str, model_name: str = 'gemini/gemini-3-flash-preview', style_prompt: Optional[str] = None, return_prompt: bool = False) -> Dict[str, Any]:
    """
    하위 호환성을 위한 래퍼 함수입니다.
    API 키는 환경변수에서 자동으로 로드됩니다.
    """
    return create_content(content, model_name, style_prompt, return_prompt)
