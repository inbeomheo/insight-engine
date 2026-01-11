"""
AI 콘텐츠 생성 서비스
LiteLLM을 사용한 다중 AI 프로바이더 지원
"""
import markdown
from flask import current_app
from litellm import completion

DEFAULT_LANGUAGE_INSTRUCTION = '결과는 반드시 한국어로 작성해주세요.'


def _build_modifier_instructions(modifiers, style_modifiers):
    """세부 옵션에서 추가 지시사항을 생성합니다."""
    instructions = []

    if not modifiers:
        instructions.append(DEFAULT_LANGUAGE_INSTRUCTION)
        return instructions

    modifier_types = ['length', 'tone', 'emoji']
    for modifier_type in modifier_types:
        value = modifiers.get(modifier_type)
        if value and value in style_modifiers.get(modifier_type, {}):
            instructions.append(style_modifiers[modifier_type][value])

    lang = modifiers.get('language', 'ko')
    language_modifiers = style_modifiers.get('language', {})
    if lang in language_modifiers:
        instructions.append(language_modifiers[lang])
    else:
        instructions.append(language_modifiers.get('ko', DEFAULT_LANGUAGE_INSTRUCTION))

    return instructions


def _build_prompt(content, style_prompt, modifiers):
    """프롬프트를 구성합니다."""
    prompt = f"{content}\n\n{style_prompt}" if style_prompt else content

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


def _convert_error_message(error_msg):
    """API 에러 메시지를 사용자 친화적인 한국어로 변환합니다."""
    error_lower = error_msg.lower()

    if 'invalid_api_key' in error_lower or 'authentication' in error_lower:
        return "API 키가 유효하지 않습니다. 설정에서 API 키를 확인해주세요."

    if 'rate_limit' in error_lower or 'quota' in error_lower:
        return "API 사용량 한도에 도달했습니다. 잠시 후 다시 시도해주세요."

    if 'model' in error_lower and 'not found' in error_lower:
        return "선택한 모델을 찾을 수 없습니다. 다른 모델을 선택해주세요."

    return f"콘텐츠 생성 중 오류 발생: {error_msg}"


def create_content(content, model, api_key, style_prompt=None, return_prompt=False, modifiers=None):
    """
    LiteLLM을 사용하여 AI 콘텐츠를 생성합니다.

    Args:
        content: 분석할 콘텐츠 (자막 + 댓글)
        model: 모델 ID (예: 'gpt-4o', 'claude-sonnet-4-20250514')
        api_key: 사용자 API 키
        style_prompt: 스타일 프롬프트
        return_prompt: 사용된 프롬프트 반환 여부
        modifiers: 세부 옵션 딕셔너리 (length, tone, language, emoji)

    Returns:
        dict 또는 tuple: 생성 결과 (return_prompt=True면 (result, prompt) 튜플)
    """
    try:
        prompt = _build_prompt(content, style_prompt, modifiers)

        response = completion(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            api_key=api_key
        )

        markdown_content = response.choices[0].message.content
        title, body = _extract_title_and_content(markdown_content)

        # 토큰 사용량 정보 추출
        usage = getattr(response, 'usage', None)
        token_usage = None
        if usage:
            token_usage = {
                'prompt_tokens': getattr(usage, 'prompt_tokens', 0),
                'completion_tokens': getattr(usage, 'completion_tokens', 0),
                'total_tokens': getattr(usage, 'total_tokens', 0)
            }

        result = {
            'title': title,
            'content': body,
            'html': markdown.markdown(body, extensions=['tables', 'fenced_code']),
            'usage': token_usage
        }

        if return_prompt:
            return result, prompt
        return result

    except Exception as e:
        current_app.logger.error(f"AI content generation failed: {e}")
        raise Exception(_convert_error_message(str(e))) from e


def create_full_blog_post(content, model_name='gpt-4o', style_prompt=None, return_prompt=False, api_key=None):
    """
    하위 호환성을 위한 래퍼 함수입니다.
    """
    if api_key is None:
        raise Exception("API 키가 필요합니다. 설정에서 API 키를 입력해주세요.")
    return create_content(content, model_name, api_key, style_prompt, return_prompt)
