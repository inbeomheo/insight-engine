"""
모디파이어 시스템 - 콘텐츠 세부 조정을 위한 옵션
7개 카테고리: 길이, 톤, 언어, 이모지, 타겟, 포커스, 깊이
"""

from typing import Dict, Optional

# 모디파이어 정의
MODIFIERS: Dict[str, Dict[str, str]] = {
    # 기존 모디파이어 (개선)
    'length': {
        'short': '''
## 분량 지침: 짧은 글
- 총 분량: 300~500자
- 핵심만 간결하게 전달
- 부가 설명 최소화
- 한 섹션당 2~3문장
''',
        'medium': '''
## 분량 지침: 중간 글
- 총 분량: 800~1200자
- 핵심 + 적절한 부연 설명
- 각 포인트에 예시 1개씩
- 한 섹션당 4~6문장
''',
        'long': '''
## 분량 지침: 긴 글
- 총 분량: 1500자 이상
- 상세하고 풍부한 설명
- 다양한 예시와 맥락 제공
- 한 섹션당 6~10문장
'''
    },

    'tone': {
        'professional': '''
## 톤 지침: 전문적
- 경어체 사용 (~습니다, ~입니다)
- 객관적이고 중립적인 어조
- 감정적 표현 자제
- 데이터와 근거 중심 서술
''',
        'friendly': '''
## 톤 지침: 친근한
- 부드러운 경어체 (~요, ~네요)
- 독자에게 말을 거는 듯한 어조
- 공감 표현 적절히 활용
- "여러분", "우리" 등 포용적 표현 사용
''',
        'humorous': '''
## 톤 지침: 유머러스
- 가벼운 농담과 위트 포함
- 비유와 은유 적극 활용
- 딱딱함을 피하되 정보 정확성 유지
- 과한 농담은 자제 (정보 전달이 우선)
'''
    },

    'language': {
        'ko': '## 언어 지침\n결과는 반드시 **한국어**로 작성하세요.',
        'en': '## Language Directive\nPlease write the entire result in **English**.',
        'ja': '## 言語指示\n結果は必ず**日本語**で作成してください。'
    },

    'emoji': {
        'use': '''
## 이모지 지침: 사용
- 각 섹션 제목에 관련 이모지 1개
- 중요 포인트 강조용으로 적절히 활용
- 과도한 사용 금지 (문장당 최대 1개)
- 이모지만으로 의미 전달하지 않음
''',
        'none': '''
## 이모지 지침: 미사용
- 이모지를 전혀 사용하지 마세요
- 텍스트만으로 모든 내용 전달
- 특수문자도 최소화
'''
    },

    # 신규 모디파이어
    'target': {
        'general': '''
## 타겟 독자: 일반인
- 전문 용어 사용 시 반드시 설명 추가
- 배경 지식 없이도 이해 가능하게
- 일상적인 비유와 예시 활용
- 복잡한 개념은 단계별로 설명
''',
        'expert': '''
## 타겟 독자: 전문가
- 전문 용어 사용 가능 (기본 설명 생략)
- 심층적인 분석과 인사이트 제공
- 업계 맥락과 트렌드 연결
- 실무 적용 관점에서 서술
''',
        'beginner': '''
## 타겟 독자: 입문자
- 가장 기초적인 용어부터 설명
- "~이란?" 형식의 정의 포함
- 단계별 이해를 돕는 구조
- 친절하고 격려하는 톤
'''
    },

    'focus': {
        'actionable': '''
## 콘텐츠 포커스: 실행 가능
- "어떻게" 중심으로 서술
- 구체적인 액션 아이템 제시
- 체크리스트/단계별 가이드 포함
- 바로 적용할 수 있는 팁 강조
''',
        'informative': '''
## 콘텐츠 포커스: 정보 전달
- "무엇"과 "왜" 중심으로 서술
- 개념과 원리 명확히 설명
- 다양한 관점과 맥락 제공
- 지식 전달에 집중
''',
        'persuasive': '''
## 콘텐츠 포커스: 설득
- 논리적 근거와 증거 강조
- 문제-해결 구조 활용
- 독자의 행동 변화 유도
- 강력한 결론과 CTA 포함
'''
    },

    'depth': {
        'overview': '''
## 분석 깊이: 개요
- 핵심 포인트만 빠르게 훑기
- 세부 사항보다 전체 그림 제시
- "한눈에 보기" 형식 선호
- 깊은 분석보다 빠른 파악 우선
''',
        'detailed': '''
## 분석 깊이: 상세
- 각 포인트별 충분한 설명
- 예시와 근거 포함
- 장단점 분석
- 실용적 시사점 도출
''',
        'comprehensive': '''
## 분석 깊이: 종합
- 모든 측면을 빠짐없이 다룸
- 다각도 분석 (장단점, 비교, 시사점)
- 관련 맥락과 배경 포함
- 심층적 인사이트 제공
'''
    }
}

# 모디파이어 기본값
DEFAULT_MODIFIERS = {
    'length': 'medium',
    'tone': 'professional',
    'language': 'ko',
    'emoji': 'none',
    'target': 'general',
    'focus': 'informative',
    'depth': 'detailed'
}

# UI 표시용 옵션 정보
MODIFIER_OPTIONS = {
    'length': {
        'label': '분량',
        'options': [
            ('short', '짧게 (300~500자)'),
            ('medium', '보통 (800~1200자)'),
            ('long', '길게 (1500자+)')
        ]
    },
    'tone': {
        'label': '톤',
        'options': [
            ('professional', '전문적'),
            ('friendly', '친근한'),
            ('humorous', '유머러스')
        ]
    },
    'language': {
        'label': '언어',
        'options': [
            ('ko', '한국어'),
            ('en', 'English'),
            ('ja', '日本語')
        ]
    },
    'emoji': {
        'label': '이모지',
        'options': [
            ('use', '사용'),
            ('none', '미사용')
        ]
    },
    'target': {
        'label': '타겟 독자',
        'options': [
            ('general', '일반인'),
            ('expert', '전문가'),
            ('beginner', '입문자')
        ]
    },
    'focus': {
        'label': '콘텐츠 목적',
        'options': [
            ('actionable', '실행 가능한 팁'),
            ('informative', '정보 전달'),
            ('persuasive', '설득/제안')
        ]
    },
    'depth': {
        'label': '분석 깊이',
        'options': [
            ('overview', '개요'),
            ('detailed', '상세'),
            ('comprehensive', '종합')
        ]
    }
}


def build_modifier_text(modifiers: Dict[str, str]) -> str:
    """
    선택된 모디파이어들을 텍스트로 조합합니다.

    Args:
        modifiers: {'length': 'medium', 'tone': 'friendly', ...}

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
        category: 모디파이어 카테고리 (length, tone, ...)
        value: 모디파이어 값 (short, professional, ...)

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
