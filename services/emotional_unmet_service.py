"""
정서적 미충족 분석 서비스 — 콘텐츠의 정서적 공백 탐지
"""

import uuid
from dataclasses import dataclass, field


# 정서적 필요 유형별 키워드
NEED_KEYWORDS = {
    'belonging': ['함께', '커뮤니티', '소속', '동료', '공동체', '팀', '우리', 'together', 'community', 'team'],
    'achievement': ['성취', '달성', '목표', '성공', '완료', '성장', '도전', 'achieve', 'goal', 'success'],
    'security': ['안전', '보호', '안정', '신뢰', '보장', '예방', 'safe', 'secure', 'trust', 'protect'],
    'growth': ['발전', '학습', '배움', '개선', '향상', '진화', 'grow', 'learn', 'improve', 'develop'],
    'recognition': ['인정', '칭찬', '감사', '존경', '평가', '보상', 'recognize', 'praise', 'appreciate', 'reward'],
}


@dataclass
class EmotionalNeed:
    """정서적 필요"""
    need_type: str  # belonging / achievement / security / growth / recognition
    intensity: float
    addressed: bool


@dataclass
class UnmetAnalysis:
    """미충족 분석 결과"""
    content_id: str
    needs: list[EmotionalNeed]
    unmet_count: int
    suggestions: list[str]


def analyze_needs(content: str) -> UnmetAnalysis:
    """키워드 기반 정서적 필요 탐지"""
    content_lower = content.lower()
    needs = []

    for need_type, keywords in NEED_KEYWORDS.items():
        matched = [kw for kw in keywords if kw in content_lower]
        intensity = min(1.0, len(matched) / max(len(keywords) * 0.3, 1))
        addressed = len(matched) > 0

        needs.append(EmotionalNeed(
            need_type=need_type,
            intensity=round(intensity, 3),
            addressed=addressed
        ))

    unmet = identify_gaps(UnmetAnalysis(
        content_id='', needs=needs, unmet_count=0, suggestions=[]
    ))
    unmet_count = len(unmet)
    suggestions = suggest_improvements(UnmetAnalysis(
        content_id='', needs=needs, unmet_count=unmet_count, suggestions=[]
    ))

    return UnmetAnalysis(
        content_id=str(uuid.uuid4())[:8],
        needs=needs,
        unmet_count=unmet_count,
        suggestions=suggestions
    )


def identify_gaps(analysis: UnmetAnalysis) -> list[EmotionalNeed]:
    """미충족 필요 식별"""
    return [n for n in analysis.needs if not n.addressed]


def suggest_improvements(analysis: UnmetAnalysis) -> list[str]:
    """개선 제안"""
    suggestions_map = {
        'belonging': '소속감을 강화하는 표현을 추가하세요 (예: "함께", "커뮤니티").',
        'achievement': '성취 관련 키워드를 포함하세요 (예: "목표 달성", "성공").',
        'security': '안전/신뢰 메시지를 추가하세요 (예: "안전한", "검증된").',
        'growth': '성장/학습 요소를 강조하세요 (예: "배움", "발전").',
        'recognition': '인정/감사 표현을 추가하세요 (예: "감사합니다", "인정").',
    }

    suggestions = []
    for need in analysis.needs:
        if not need.addressed:
            suggestion = suggestions_map.get(need.need_type)
            if suggestion:
                suggestions.append(suggestion)

    return suggestions
