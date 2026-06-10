"""
모디파이어 시스템 v4.0
3개 카테고리: 길이(length), 문체(writing_style), 언어(language)

v4 변경점: config.STYLE_MODIFIERS와 이중화돼 있던 텍스트를 이 파일 하나로 통합.
(config.py가 이 MODIFIERS를 그대로 재export한다)
"""

from typing import Dict, Optional

# 모디파이어 정의 — 각 항목은 프롬프트에 그대로 주입되는 지시문
MODIFIERS: Dict[str, Dict[str, str]] = {
    'length': {
        'short': '총 분량은 약 500~800자. 핵심만 간결하게 쓰고, 출력 형식의 선택적 섹션은 과감히 생략하세요.',
        'medium': '총 분량은 약 1000~1500자. 핵심에 적절한 부연 설명을 더해 작성하세요.',
        'long': '총 분량은 약 2000~3000자. 예시와 맥락을 풍부하게 포함해 상세히 작성하세요.'
    },
    'writing_style': {
        'conversational': '대화체(~요, ~해요)로 독자에게 말을 거는 듯 친근하게 작성하세요.',
        'explanatory': '설명체(~입니다, ~합니다)로 객관적이고 중립적으로 작성하세요.',
        'casual': '캐주얼체(~야, ~해)로 친구에게 얘기하듯 편하게 작성하세요.',
        'expert': '전문가 톤으로 업계 용어를 자연스럽게 사용하고, 기초 설명은 생략하며 깊이 있게 작성하세요.'
    },
    'language': {
        'ko': '결과는 반드시 한국어로 작성해주세요.',
        'en': 'You MUST write the entire result in English.',
        'ja': '結果は必ず日本語で書いてください。'
    }
}

# 모디파이어 기본값
DEFAULT_MODIFIERS = {
    'length': 'medium',
    'writing_style': 'conversational',
    'language': 'ko'
}

# UI 표시용 옵션 정보
MODIFIER_OPTIONS = {
    'length': {
        'label': '길이',
        'options': [
            ('short', '짧게'),
            ('medium', '보통'),
            ('long', '길게')
        ]
    },
    'writing_style': {
        'label': '문체',
        'options': [
            ('conversational', '대화체'),
            ('explanatory', '설명체'),
            ('casual', '캐주얼'),
            ('expert', '전문가')
        ]
    },
    'language': {
        'label': '출력 언어',
        'options': [
            ('ko', '한국어'),
            ('en', 'English'),
            ('ja', '日本語')
        ]
    }
}


def build_modifier_text(modifiers: Dict[str, str]) -> str:
    """선택된 모디파이어들을 텍스트로 조합합니다.

    Args:
        modifiers: {'length': 'medium', 'writing_style': 'conversational'}

    Returns:
        조합된 모디파이어 텍스트
    """
    texts = []

    for key, value in modifiers.items():
        if key in MODIFIERS and value in MODIFIERS[key]:
            texts.append(MODIFIERS[key][value])

    return "\n".join(texts)


def get_modifier_text(category: str, value: str) -> Optional[str]:
    """특정 모디파이어의 텍스트를 반환합니다.

    Args:
        category: 모디파이어 카테고리 (length, writing_style, language)
        value: 모디파이어 값 (short, conversational 등)

    Returns:
        모디파이어 텍스트 또는 None
    """
    return MODIFIERS.get(category, {}).get(value)


__all__ = [
    'MODIFIERS',
    'DEFAULT_MODIFIERS',
    'MODIFIER_OPTIONS',
    'build_modifier_text',
    'get_modifier_text'
]
