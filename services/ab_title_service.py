"""
A/B 테스트 제목 생성 서비스

AI를 활용하여 원본 제목의 변형 후보를 3~5개 생성합니다.
클릭베이트, 질문형, 리스트형, 직설형 등 다양한 형식 제공.
"""
import json
import logging
import os
from typing import List, Optional

from litellm import completion

logger = logging.getLogger(__name__)

# 제목 생성에 사용할 경량 모델 폴백 체인
_MODEL_CHAIN = [
    'gemini/gemini-2.5-flash-lite-preview-09-2025',
    'gemini/gemini-3-flash-preview',
    'deepseek/deepseek-chat',
]

_TITLE_PROMPT = """다음 콘텐츠와 원본 제목을 분석하여, A/B 테스트용 제목 변형을 5개 생성하세요.

원본 제목: {title}

콘텐츠 요약 (앞부분):
{content_preview}

규칙:
1. 각 변형은 서로 다른 전략을 사용 (질문형, 숫자/리스트형, 호기심 유발, 핵심 가치 강조, 직설형)
2. 클릭베이트 수준이 아닌, 정직하면서도 매력적인 제목
3. 원본 제목의 핵심 주제를 유지
4. 30자 이내 권장

JSON 배열만 반환하세요. 설명 없이:
["변형1", "변형2", "변형3", "변형4", "변형5"]
"""


def _get_available_model() -> Optional[str]:
    """사용 가능한 AI 모델을 반환합니다."""
    key_map = {
        'gemini/': 'GEMINI_API_KEY',
        'deepseek/': 'DEEPSEEK_API_KEY',
        'zhipuai/': 'ZHIPUAI_API_KEY',
    }
    for model in _MODEL_CHAIN:
        for prefix, env_key in key_map.items():
            if model.startswith(prefix) and os.environ.get(env_key):
                return model
    return None


def generate_title_variants(
    content: str,
    original_title: str,
    count: int = 5,
) -> List[str]:
    """AI로 A/B 테스트용 제목 변형을 생성합니다.

    Args:
        content: 콘텐츠 본문 텍스트
        original_title: 원본 제목
        count: 생성할 변형 수 (기본 5)

    Returns:
        제목 변형 문자열 리스트 (최대 count개)

    Raises:
        RuntimeError: AI 모델 사용 불가 시
    """
    if not content or not original_title:
        return []

    model = _get_available_model()
    if not model:
        raise RuntimeError('사용 가능한 AI 모델이 없습니다. API 키를 확인하세요.')

    # 콘텐츠 미리보기 (토큰 절약)
    preview = content[:500]

    prompt = _TITLE_PROMPT.format(
        title=original_title,
        content_preview=preview,
    )

    try:
        response = completion(
            model=model,
            messages=[{'role': 'user', 'content': prompt}],
            temperature=0.9,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()

        # JSON 파싱 (코드 블록 제거)
        if raw.startswith('```'):
            raw = raw.split('\n', 1)[-1].rsplit('```', 1)[0].strip()

        titles = json.loads(raw)
        if isinstance(titles, list):
            return [str(t).strip() for t in titles if t][:count]

        return []

    except Exception as e:
        logger.error(f"A/B 제목 생성 실패: {e}")
        raise RuntimeError(f'제목 생성 실패: {e}')
