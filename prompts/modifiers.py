"""
모디파이어 시스템 v3.1
3개 카테고리: 길이(length), 문체(writing_style), 언어(language)
"""

from typing import Dict, Optional

# 모디파이어 정의
MODIFIERS: Dict[str, Dict[str, str]] = {
    'length': {
        'short': '''
## 분량: 짧게
- 총 분량: 500~800자
- 핵심만 간결하게
- 부가 설명 최소화
''',
        'medium': '''
## 분량: 보통
- 총 분량: 1000~1500자
- 핵심 + 적절한 부연 설명
- 각 포인트에 예시 포함
''',
        'long': '''
## 분량: 길게
- 총 분량: 2000~3000자
- 상세하고 풍부한 설명
- 다양한 예시와 맥락 제공
'''
    },

    'writing_style': {
        'conversational': '''
## 문체: 대화체
- ~요, ~해요 체 사용
- 독자에게 말을 거는 듯한 톤
- "여러분", "우리" 같은 포용적 표현 OK
- 친근하면서도 정보 전달은 명확하게
''',
        'explanatory': '''
## 문체: 설명체
- ~입니다, ~합니다 체 사용
- 객관적이고 중립적인 어조
- 감정적 표현 자제
- 정보 전달에 집중
''',
        'casual': '''
## 문체: 캐주얼
- ~야, ~해 체 사용 (반말)
- 친구에게 얘기하듯 편하게
- 가벼운 표현과 비유 활용
- 너무 격식 차리지 않기
''',
        'expert': '''
## 문체: 전문가
- 업계 용어 자연스럽게 사용
- 깊이 있는 분석과 인사이트 제공
- 전문가 동료에게 설명하는 톤
- 기초 설명은 생략해도 OK
'''
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
    """
    선택된 모디파이어들을 텍스트로 조합합니다.

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
    """
    특정 모디파이어의 텍스트를 반환합니다.

    Args:
        category: 모디파이어 카테고리 (length, writing_style)
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
