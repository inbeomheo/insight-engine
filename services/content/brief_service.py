"""
콘텐츠 브리프 생성 서비스

AI를 활용하여 주제에 대한 콘텐츠 브리프를 생성합니다.
"""
import functools
import logging
import json
import re
from typing import Dict, List, Optional



logger = logging.getLogger(__name__)

_BRIEF_PROMPT = """당신은 콘텐츠 전략가입니다. 주어진 주제에 대해 콘텐츠 브리프를 JSON으로 작성하세요.

[주제]
{topic}

{keywords_section}

다음 JSON 형식으로만 응답하세요 (마크다운 코드블록 없이):
{{
  "title_suggestions": ["제목 후보 1", "제목 후보 2", "제목 후보 3"],
  "overview": "콘텐츠 개요 (2-3문장)",
  "target_audience": "타겟 독자 설명",
  "key_points": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3", "핵심 포인트 4"],
  "recommended_structure": ["서론: ...", "본론1: ...", "본론2: ...", "결론: ..."],
  "keywords": ["추천 키워드 1", "추천 키워드 2", "추천 키워드 3"],
  "tone": "추천 문체 (예: 전문적이면서 친근한)"
}}
"""


def _parse_brief_json(raw_text: str) -> Optional[Dict]:
    """LLM 응답에서 JSON을 파싱합니다."""
    # 코드 블록 제거
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


def generate_brief(topic: str, keywords: Optional[List[str]] = None) -> Dict:
    """주제에 대한 콘텐츠 브리프를 생성합니다.

    Args:
        topic: 콘텐츠 주제
        keywords: 포함할 키워드 목록 (선택)

    Returns:
        dict: {
            title_suggestions, overview, target_audience,
            key_points, recommended_structure, keywords, tone
        }

    Raises:
        ValueError: 주제가 비어있을 때
        Exception: AI 호출 실패 시
    """
    try:
        if not topic or not topic.strip():
            raise ValueError("주제를 입력해주세요.")

        keywords_section = ""
        if keywords:
            keywords_section = f"[참고 키워드]\n{', '.join(keywords)}"

        prompt = _BRIEF_PROMPT.format(
            topic=topic.strip(),
            keywords_section=keywords_section,
        )

        from services.core import ai_service
        result = ai_service.create_content(
            prompt,
            _get_model(),
            "",  # 스타일 프롬프트 없음
        )

        content_text = result.get('content', '')
        parsed = _parse_brief_json(content_text)

        if parsed is None:
            return _fallback_brief(topic, content_text, keywords)

        return _ensure_brief_defaults(parsed, topic, keywords)
    except Exception as e:
        logger.error(f"브리프 생성 처리 실패: {e}")
        raise
def _fallback_brief(
    topic: str, content_text: str, keywords: Optional[List[str]],
) -> Dict:
    """JSON 파싱 실패 시 기본 브리프 구조를 반환합니다."""
    return {
        "title_suggestions": [topic],
        "overview": content_text[:200],
        "target_audience": "일반 독자",
        "key_points": [],
        "recommended_structure": [],
        "keywords": keywords or [],
        "tone": "전문적",
    }


def _ensure_brief_defaults(
    parsed: Dict, topic: str, keywords: Optional[List[str]],
) -> Dict:
    """파싱된 브리프에 누락된 필수 키를 기본값으로 채웁니다."""
    defaults = {
        "title_suggestions": [topic],
        "overview": "",
        "target_audience": "일반 독자",
        "key_points": [],
        "recommended_structure": [],
        "keywords": keywords or [],
        "tone": "전문적",
    }
    for key, default in defaults.items():
        if key not in parsed or not parsed[key]:
            parsed[key] = default
    return parsed


@functools.lru_cache(maxsize=1)
def _get_model() -> str:
    """사용 가능한 모델을 반환합니다."""
    from config import PROVIDER_API_KEYS

    candidates = ['chatmock/gpt-5.3-codex-spark']
    for model_id in candidates:
        provider = model_id.split('/')[0]
        if PROVIDER_API_KEYS.get(provider, ''):
            return model_id

    raise Exception("사용 가능한 AI 모델이 없습니다. API 키를 확인해주세요.")
