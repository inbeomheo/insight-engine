"""
스마트 요약 서비스 (Progressive Summary)

1줄 / 3줄 / 전체 요약을 단계별로 생성합니다.
"""
import json
import re
from typing import Dict, Optional



_SUMMARY_PROMPT = """다음 콘텐츠를 3단계로 요약하세요. JSON으로만 응답하세요 (마크다운 코드블록 없이).

[콘텐츠]
{content}

응답 형식:
{{
  "one_line": "핵심을 한 문장으로 요약 (50자 이내)",
  "three_lines": "3문장으로 요약. 각 문장은 마침표로 구분.",
  "full_summary": "5-7문장의 전체 요약. 핵심 논점과 결론을 포함."
}}
"""


def _parse_summary_json(raw_text: str) -> Optional[Dict]:
    """LLM 응답에서 JSON을 파싱합니다."""
    text = re.sub(r'```json\s*', '', raw_text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()

    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def generate_progressive_summary(content: str, model: Optional[str] = None) -> Dict:
    """콘텐츠를 3단계 요약으로 변환합니다.

    Args:
        content: 요약할 콘텐츠
        model: 사용할 모델 ID (None이면 자동 선택)

    Returns:
        dict: {
            "one_line": str,      # 1줄 요약
            "three_lines": str,   # 3줄 요약
            "full_summary": str,  # 전체 요약
        }

    Raises:
        ValueError: 콘텐츠가 비어있을 때
        Exception: AI 호출 실패 시
    """
    if not content or not content.strip():
        raise ValueError("요약할 콘텐츠가 필요합니다.")

    use_model = model or _get_model()

    # 콘텐츠 길이 제한
    truncated = content[:5000] if len(content) > 5000 else content

    prompt = _SUMMARY_PROMPT.format(content=truncated)

    from services.core import ai_service
    result = ai_service.create_content(prompt, use_model, "")

    content_text = result.get('content', '')
    parsed = _parse_summary_json(content_text)

    if parsed is None:
        # 파싱 실패 시 전체 텍스트를 full_summary로 사용
        return {
            "one_line": content_text[:50] if content_text else "",
            "three_lines": content_text[:200] if content_text else "",
            "full_summary": content_text[:500] if content_text else "",
        }

    # 필수 키 보장
    return {
        "one_line": parsed.get("one_line", ""),
        "three_lines": parsed.get("three_lines", ""),
        "full_summary": parsed.get("full_summary", ""),
    }


def _get_model() -> str:
    """사용 가능한 모델을 반환합니다."""
    from config import PROVIDER_API_KEYS

    candidates = [
        'gemini/gemini-3-flash-preview',
        'gemini/gemini-2.5-flash-lite-preview-09-2025',
        'deepseek/deepseek-chat',
        'zhipuai/GLM-4.5-Air',
    ]
    for model_id in candidates:
        provider = model_id.split('/')[0]
        if PROVIDER_API_KEYS.get(provider, ''):
            return model_id

    raise Exception("사용 가능한 AI 모델이 없습니다. API 키를 확인해주세요.")
