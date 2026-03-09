"""
치료 저널 서비스 — 치료 과정 기록 + 감정 추적
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class JournalEntry:
    """저널 항목"""
    entry_id: str
    date: str
    content: str
    mood: str  # happy / sad / anxious / calm / angry / neutral
    energy_level: int  # 1~10
    tags: list[str]


@dataclass
class JournalAnalysis:
    """저널 분석 결과"""
    total_entries: int
    mood_distribution: dict
    avg_energy: float
    common_themes: list[str]
    trend: str


def add_entry(entries: list[JournalEntry], content: str, mood: str,
              energy: int, tags: list[str]) -> list[JournalEntry]:
    """저널 항목 추가"""
    from datetime import datetime
    entry = JournalEntry(
        entry_id=str(uuid.uuid4())[:8],
        date=datetime.now().strftime('%Y-%m-%d'),
        content=content,
        mood=mood,
        energy_level=max(1, min(10, energy)),
        tags=tags
    )
    return entries + [entry]


def analyze_journal(entries: list[JournalEntry]) -> JournalAnalysis:
    """저널 분석"""
    if not entries:
        return JournalAnalysis(
            total_entries=0,
            mood_distribution={},
            avg_energy=0.0,
            common_themes=[],
            trend='stable'
        )

    # 기분 분포
    mood_dist: dict[str, int] = {}
    for e in entries:
        mood_dist[e.mood] = mood_dist.get(e.mood, 0) + 1

    # 평균 에너지
    avg_energy = round(sum(e.energy_level for e in entries) / len(entries), 2)

    # 공통 테마 (태그 빈도)
    tag_counts: dict[str, int] = {}
    for e in entries:
        for tag in e.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    common_themes = sorted(tag_counts, key=tag_counts.get, reverse=True)[:5]

    trend = detect_mood_trend(entries)

    return JournalAnalysis(
        total_entries=len(entries),
        mood_distribution=mood_dist,
        avg_energy=avg_energy,
        common_themes=common_themes,
        trend=trend
    )


def detect_mood_trend(entries: list[JournalEntry]) -> str:
    """기분 추세 판단 (improving / declining / stable)"""
    if len(entries) < 2:
        return 'stable'

    # 에너지 레벨 기반 추세 판단
    half = len(entries) // 2
    first_half_avg = sum(e.energy_level for e in entries[:half]) / half
    second_half_avg = sum(e.energy_level for e in entries[half:]) / (len(entries) - half)

    diff = second_half_avg - first_half_avg
    if diff > 1.0:
        return 'improving'
    elif diff < -1.0:
        return 'declining'
    return 'stable'


def suggest_prompts(analysis: JournalAnalysis) -> list[str]:
    """저널 프롬프트 제안"""
    prompts = []

    if analysis.trend == 'declining':
        prompts.append('오늘 감사했던 일 세 가지를 적어보세요.')
        prompts.append('최근 스트레스 요인은 무엇인가요?')
    elif analysis.trend == 'improving':
        prompts.append('긍정적 변화의 원인은 무엇일까요?')
        prompts.append('이 기분을 유지하기 위해 할 수 있는 일은?')
    else:
        prompts.append('오늘 하루를 한 단어로 표현한다면?')
        prompts.append('이번 주 가장 의미 있었던 순간은?')

    if analysis.avg_energy < 4:
        prompts.append('에너지가 낮은 날, 자신을 위해 무엇을 할 수 있을까요?')
    elif analysis.avg_energy > 7:
        prompts.append('높은 에너지를 활용해 도전해보고 싶은 것은?')

    return prompts
