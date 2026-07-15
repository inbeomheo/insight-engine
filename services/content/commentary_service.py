"""
AI 코멘터리 서비스

원본 콘텐츠에 [해설] 주석을 추가합니다.
전문 용어 설명, 배경 정보, 관련 사례를 주석으로 삽입합니다.
"""
import functools
import logging
import re
from typing import Dict, Optional


logger = logging.getLogger(__name__)

_COMMENTARY_PROMPT = """당신은 전문 해설자입니다. 아래 콘텐츠를 읽고, 독자 이해를 돕기 위해 핵심 부분에 [해설] 주석을 추가하세요.

[규칙]
1. 전문 용어가 나오면 간단한 설명 추가
2. 주요 주장에는 배경 정보 또는 관련 사례 추가
3. [해설] 주석은 해당 문단 바로 아래에 삽입
4. 형식: > **[해설]** 설명 내용
5. 원본 내용을 수정하지 말고, 주석만 추가
6. 주석은 최대 8개까지만 추가 (과도한 주석 금지)
7. 원본 마크다운 서식을 유지

[콘텐츠]
{content}

위 콘텐츠에 [해설] 주석을 추가한 전체 텍스트를 출력하세요.
"""


def add_commentary(content: str, model: Optional[str] = None) -> Dict:
    """콘텐츠에 AI 해설 주석을 추가합니다.

    Args:
        content: 원본 콘텐츠 (마크다운)
        model: 사용할 모델 ID (None이면 자동 선택)

    Returns:
        dict: {
            "commented_content": str,  # 해설이 추가된 콘텐츠
            "comment_count": int,      # 추가된 해설 수
        }

    Raises:
        ValueError: 콘텐츠가 비어있을 때
        Exception: AI 호출 실패 시
    """
    try:
        if not content or not content.strip():
            raise ValueError("해설을 추가할 콘텐츠가 필요합니다.")

        use_model = model or _get_model()

        # 콘텐츠 길이 제한 (비용 절감)
        truncated = content[:5000] if len(content) > 5000 else content

        prompt = _COMMENTARY_PROMPT.format(content=truncated)

        from services.core import ai_service
        result = ai_service.create_content(prompt, use_model, "")

        commented = result.get('content', '')
        if not commented:
            commented = content

        # 해설 주석 개수 카운트
        comment_count = len(re.findall(r'\*\*\[해설\]\*\*', commented))

        return {
            "commented_content": commented,
            "comment_count": comment_count,
        }
    except Exception as e:
        logger.error(f"AI 해설 추가 처리 실패: {e}")
        raise
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
