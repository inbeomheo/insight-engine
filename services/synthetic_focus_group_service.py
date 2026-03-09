"""
합성 포커스그룹 서비스 — 가상 페르소나 기반 포커스그룹 시뮬레이션
"""

import uuid
import hashlib
from dataclasses import dataclass, field


@dataclass
class Persona:
    """가상 페르소나"""
    persona_id: str
    name: str
    age: int
    occupation: str
    interests: list[str]
    communication_style: str  # formal / casual / technical


@dataclass
class FocusGroupResponse:
    """포커스그룹 응답"""
    persona_id: str
    question: str
    response: str
    sentiment: str  # positive / neutral / negative
    key_concerns: list[str]


@dataclass
class FocusGroupReport:
    """포커스그룹 보고서"""
    question: str
    responses: list[FocusGroupResponse]
    consensus: str
    key_themes: list[str]


def create_personas(profiles: list[dict]) -> list[Persona]:
    """프로필 딕셔너리 목록으로 페르소나 생성"""
    personas = []
    for p in profiles:
        persona = Persona(
            persona_id=str(uuid.uuid4())[:8],
            name=p.get('name', 'Unknown'),
            age=p.get('age', 30),
            occupation=p.get('occupation', ''),
            interests=p.get('interests', []),
            communication_style=p.get('communication_style', 'casual')
        )
        personas.append(persona)
    return personas


def simulate_response(persona: Persona, question: str, content: str) -> FocusGroupResponse:
    """페르소나 기반 응답 시뮬레이션"""
    # 해시 기반 결정론적 감정 결정
    seed = hashlib.md5(f"{persona.persona_id}{question}".encode()).hexdigest()
    seed_val = int(seed[:4], 16)

    if seed_val % 3 == 0:
        sentiment = 'positive'
    elif seed_val % 3 == 1:
        sentiment = 'neutral'
    else:
        sentiment = 'negative'

    # 스타일에 따른 응답 템플릿
    style_templates = {
        'formal': f"{persona.name}의 전문적 견해: {question}에 대해 {content[:50]}... 관련 분석 결과를 제시합니다.",
        'casual': f"{persona.name}: {question}에 대해서... {content[:50]}... 좀 흥미로운데요!",
        'technical': f"{persona.name} (기술 분석): {question} — {content[:50]}... 기술적 관점에서 검토 필요."
    }

    response_text = style_templates.get(persona.communication_style, style_templates['casual'])

    # 관심사 기반 관심 사항 추출
    concerns = [interest for interest in persona.interests if interest.lower() in content.lower()]
    if not concerns:
        concerns = persona.interests[:1] if persona.interests else []

    return FocusGroupResponse(
        persona_id=persona.persona_id,
        question=question,
        response=response_text,
        sentiment=sentiment,
        key_concerns=concerns
    )


def run_focus_group(personas: list[Persona], question: str, content: str) -> FocusGroupReport:
    """전체 포커스그룹 실행"""
    responses = [simulate_response(p, question, content) for p in personas]

    # 합의 결정 (다수 감정)
    sentiment_counts = {}
    for r in responses:
        sentiment_counts[r.sentiment] = sentiment_counts.get(r.sentiment, 0) + 1

    majority = max(sentiment_counts, key=sentiment_counts.get) if sentiment_counts else 'neutral'
    consensus_map = {
        'positive': '긍정적 합의',
        'neutral': '중립적 의견',
        'negative': '부정적 합의'
    }
    consensus = consensus_map.get(majority, '의견 분산')

    key_themes = extract_themes(
        FocusGroupReport(question=question, responses=responses, consensus='', key_themes=[])
    )

    return FocusGroupReport(
        question=question,
        responses=responses,
        consensus=consensus,
        key_themes=key_themes
    )


def extract_themes(report: FocusGroupReport) -> list[str]:
    """응답에서 주제 추출 — 모든 concern을 빈도순 정렬"""
    theme_counts: dict[str, int] = {}
    for r in report.responses:
        for concern in r.key_concerns:
            theme_counts[concern] = theme_counts.get(concern, 0) + 1

    sorted_themes = sorted(theme_counts.keys(), key=lambda t: theme_counts[t], reverse=True)
    return sorted_themes
