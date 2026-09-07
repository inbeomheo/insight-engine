"""LiteLLM 콘텐츠 스트리밍 구현.

ai_service.py의 공개 API(create_content_stream)는 유지하되, 파일 크기 제한을
넘기지 않도록 스트리밍 전용 세부 구현을 이 모듈로 분리합니다.
"""
import logging
from typing import Any, Callable, Dict, Generator, List, Optional

from services.core import ai_service
from services.core.ai_prompt_context import build_optional_prompt_contexts
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)


def _usage_to_dict(usage: Any) -> Dict[str, int]:
    """LiteLLM usage 객체/dict를 기존 응답 형태로 정규화합니다."""
    if not usage:
        return {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0}
    if isinstance(usage, dict):
        prompt_tokens = int(usage.get('prompt_tokens') or usage.get('input_tokens') or 0)
        completion_tokens = int(usage.get('completion_tokens') or usage.get('output_tokens') or 0)
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': int(usage.get('total_tokens') or (prompt_tokens + completion_tokens)),
        }
    prompt_tokens = int(getattr(usage, 'prompt_tokens', 0) or getattr(usage, 'input_tokens', 0) or 0)
    completion_tokens = int(getattr(usage, 'completion_tokens', 0) or getattr(usage, 'output_tokens', 0) or 0)
    return {
        'prompt_tokens': prompt_tokens,
        'completion_tokens': completion_tokens,
        'total_tokens': int(getattr(usage, 'total_tokens', 0) or (prompt_tokens + completion_tokens)),
    }


def _get_chunk_value(obj: Any, key: str, default: Any = None) -> Any:
    """LiteLLM chunk가 dict/객체 어느 형태여도 값을 읽습니다."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_stream_delta(chunk: Any) -> str:
    """LiteLLM 스트림 chunk에서 텍스트 delta만 추출합니다."""
    choices = _get_chunk_value(chunk, 'choices', []) or []
    if not choices:
        return ''
    choice = choices[0]
    delta = _get_chunk_value(choice, 'delta')
    content = _get_chunk_value(delta, 'content')
    if content is None:
        # 일부 provider는 message/content 형태를 섞어 보낼 수 있어 방어적으로 처리
        message = _get_chunk_value(choice, 'message')
        content = _get_chunk_value(message, 'content')
    return content or ''


def _extract_stream_usage(chunk: Any) -> Optional[Dict[str, int]]:
    """가능한 경우 스트림 chunk의 usage를 추출합니다."""
    usage = _get_chunk_value(chunk, 'usage')
    if not usage:
        return None
    return _usage_to_dict(usage)


def create_content_stream(content: str, model: str, style_prompt: Optional[str] = None,
                          modifiers: Optional[Dict[str, Any]] = None, style_id: Optional[str] = None,
                          detail_level: Optional[str] = None,
                          user_id: Optional[str] = None,
                          segments: Optional[List[Dict[str, Any]]] = None,
                          web_search: bool = False,
                          on_cost_start: Optional[Callable[[], None]] = None) -> Generator[str, None, Dict[str, Any]]:
    """
    LiteLLM 스트리밍으로 AI 콘텐츠를 생성합니다.
    각 조각은 텍스트 delta만 yield하고, generator return 값으로 prompt/usage를 돌려줍니다.

    CLIProxyAPI(OpenAI 호환) 단일 경로를 사용하므로 프로바이더별 스트리밍 폴백은 두지 않습니다.
    """
    default_meta = {
        'prompt': '',
        'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
        'web_sources': None,
        'fallback_non_streaming': False,
    }

    try:
        ai_service.require_gateway_connection()
        rag_context, web_context, web_sources, style_memory_context, memory_context = (
            build_optional_prompt_contexts(
                content,
                user_id=user_id,
                web_search=web_search,
                on_cost_start=on_cost_start,
            )
        )
        prompt = ai_service._build_prompt(
            content, style_prompt, modifiers,
            rag_context=rag_context,
            segments=segments,
            web_context=web_context,
            style_memory_context=style_memory_context,
            detail_level=detail_level,
            memory_context=memory_context,
        )
        completion_kwargs = ai_service._build_completion_kwargs(
            model, prompt, style_id, modifiers, stream=True, detail_level=detail_level
        )
        completion = ai_service._get_completion()
        if callable(on_cost_start):
            on_cost_start()
        else:
            from services.usage.usage_decorator import mark_usage_charge_committed
            mark_usage_charge_committed()
        response = completion(**completion_kwargs)

        usage = default_meta['usage']
        for chunk in response:
            chunk_usage = _extract_stream_usage(chunk)
            if chunk_usage:
                usage = chunk_usage
            delta = _extract_stream_delta(chunk)
            if delta:
                yield delta

        return {
            **default_meta,
            'prompt': prompt,
            'usage': usage,
            'web_sources': web_sources or None,
        }

    except UsageLockUnavailable:
        raise
    except Exception as e:
        logger.error(f"Streaming failed: model={model}, error={e}")
        raise Exception(ai_service._convert_error_message(str(e), model)) from e
