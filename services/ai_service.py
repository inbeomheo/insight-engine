"""
AI 콘텐츠 생성 서비스
LiteLLM을 사용한 다중 AI 프로바이더 지원
"""
import os
import time
import markdown
import threading
from datetime import datetime
from zoneinfo import ZoneInfo
from flask import current_app
from litellm import completion

# Zhipu AI (GLM) OpenAI 호환 API 설정
ZHIPUAI_API_BASE = 'https://open.bigmodel.cn/api/paas/v4/'

# GLM 모델 동시성 제한 - 한 번에 하나의 요청만 처리
_glm_lock = threading.Lock()

# GLM-4.7 재시도 설정
GLM_RETRY_COUNT = 3
GLM_RETRY_DELAY = 15  # 초

DEFAULT_LANGUAGE_INSTRUCTION = '결과는 반드시 한국어로 작성해주세요.'


def _build_modifier_instructions(modifiers, style_modifiers):
    """세부 옵션에서 추가 지시사항을 생성합니다.

    v3.0: 2개 모디파이어만 지원 (length, writing_style)
    한국어 고정 (다국어 지원 제거)
    """
    instructions = []

    # 한국어 고정
    instructions.append(DEFAULT_LANGUAGE_INSTRUCTION)

    if not modifiers:
        return instructions

    # v3.0: length, writing_style 2개만 지원
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


def _build_prompt(content, style_prompt, modifiers):
    """프롬프트를 구성합니다."""
    # 현재 한국 시간 추가
    current_time = _get_korean_datetime()
    time_context = f"[현재 시간: {current_time} (한국 표준시)]"

    prompt = f"{time_context}\n\n{content}\n\n{style_prompt}" if style_prompt else f"{time_context}\n\n{content}"

    style_modifiers = current_app.config.get('STYLE_MODIFIERS', {})
    modifier_instructions = _build_modifier_instructions(modifiers, style_modifiers)

    if modifier_instructions:
        prompt += "\n\n[추가 지시사항]\n" + "\n".join(modifier_instructions)

    return prompt


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
    if 'service' in error_lower and 'unavailable' in error_lower or '503' in error_lower:
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


def create_content(content, model, style_prompt=None, return_prompt=False, modifiers=None):
    """
    LiteLLM을 사용하여 AI 콘텐츠를 생성합니다.
    API 키는 환경변수에서 자동으로 로드됩니다 (OPENAI_API_KEY, ANTHROPIC_API_KEY 등).

    Args:
        content: 분석할 콘텐츠 (자막 + 댓글)
        model: 모델 ID (예: 'gpt-4o', 'claude-sonnet-4-20250514')
        style_prompt: 스타일 프롬프트
        return_prompt: 사용된 프롬프트 반환 여부
        modifiers: 세부 옵션 딕셔너리 (length, tone, language, emoji)

    Returns:
        dict 또는 tuple: 생성 결과 (return_prompt=True면 (result, prompt) 튜플)
    """
    try:
        prompt = _build_prompt(content, style_prompt, modifiers)

        # LiteLLM이 환경변수에서 자동으로 API 키 로드
        completion_kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}]
        }

        # Gemini 모델 (Flash Lite 제외) - reasoning_effort 사용
        if model.startswith("gemini/") and "lite" not in model.lower():
            completion_kwargs["reasoning_effort"] = "minimal"

        # Zhipu AI (GLM) 모델은 OpenAI 호환 API 사용
        is_glm = model.startswith("zhipuai/")
        if is_glm:
            zhipuai_key = os.getenv("ZHIPUAI_API_KEY")
            if not zhipuai_key:
                raise ValueError("ZHIPUAI_API_KEY 환경변수가 설정되지 않았습니다.")
            actual_model = model.replace("zhipuai/", "")  # zhipuai/ 접두사 제거
            completion_kwargs["model"] = f"openai/{actual_model}"
            completion_kwargs["api_base"] = ZHIPUAI_API_BASE
            completion_kwargs["api_key"] = zhipuai_key

        # GLM 모델은 동시성 제한으로 순차 처리 (락 + 재시도)
        if is_glm:
            with _glm_lock:
                current_app.logger.info(f"GLM 락 획득: {model}")
                last_error = None
                for attempt in range(GLM_RETRY_COUNT):
                    try:
                        response = completion(**completion_kwargs)
                        current_app.logger.info(f"GLM 성공 (시도 {attempt + 1}): {model}")
                        break
                    except Exception as e:
                        last_error = e
                        error_str = str(e)
                        # 1302 동시성 에러만 재시도
                        if '1302' in error_str and attempt < GLM_RETRY_COUNT - 1:
                            current_app.logger.warning(
                                f"GLM 동시성 에러, {GLM_RETRY_DELAY}초 후 재시도 "
                                f"({attempt + 1}/{GLM_RETRY_COUNT}): {model}"
                            )
                            time.sleep(GLM_RETRY_DELAY)
                        else:
                            raise
                else:
                    # 모든 재시도 실패
                    raise last_error
                current_app.logger.info(f"GLM 락 해제: {model}")
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
            html = f"<pre>{body}</pre>"

        result = {
            'title': title,
            'content': body,
            'html': html,
            'usage': token_usage
        }

        if return_prompt:
            return result, prompt
        return result

    except Exception as e:
        current_app.logger.error(f"AI content generation failed: model={model}, error={e}")
        raise Exception(_convert_error_message(str(e), model)) from e


def create_full_blog_post(content, model_name='gpt-4o', style_prompt=None, return_prompt=False):
    """
    하위 호환성을 위한 래퍼 함수입니다.
    API 키는 환경변수에서 자동으로 로드됩니다.
    """
    return create_content(content, model_name, style_prompt, return_prompt)
