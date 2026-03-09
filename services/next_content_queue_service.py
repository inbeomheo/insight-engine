"""
다음 콘텐츠 추천 큐 서비스

콘텐츠 DNA 프로파일과 갭(gap) 정보를 기반으로
다음에 생성할 콘텐츠를 추천합니다.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ContentRecommendation:
    """콘텐츠 추천 항목"""
    topic: str                   # 추천 주제
    content_type: str            # 추천 콘텐츠 유형
    priority: str                # 우선순위 (high/medium/low)
    reason: str                  # 추천 이유
    estimated_impact: float      # 예상 영향도 (0.0 ~ 1.0)


# ── 콘텐츠 유형별 기본 가중치 ──

_TYPE_WEIGHTS: Dict[str, float] = {
    'blog': 0.8,
    'tutorial': 0.9,
    'newsletter': 0.7,
    'sns_post': 0.5,
    'summary': 0.6,
    'qna': 0.75,
    'review': 0.65,
    'case_study': 0.85,
    'video_script': 0.7,
    'podcast': 0.6,
}

# ── 다각화 추천 유형 ──

_DIVERSIFICATION_TYPES = ['tutorial', 'case_study', 'qna', 'newsletter', 'video_script']


def _calculate_impact(
    topic: str,
    content_type: str,
    is_gap: bool,
    dna: Dict,
) -> float:
    """추천 항목의 예상 영향도를 계산합니다.

    Args:
        topic: 추천 주제
        content_type: 콘텐츠 유형
        is_gap: 갭 기반 추천인지 여부
        dna: DNA 프로파일 dict

    Returns:
        0.0 ~ 1.0 사이의 영향도 점수
    """
    base_weight = _TYPE_WEIGHTS.get(content_type, 0.5)

    # 갭 기반 추천은 기본 영향도 가산
    if is_gap:
        base_weight = min(1.0, base_weight + 0.15)

    # DNA에서 기존 주제와 겹치지 않으면 새로운 영역 → 높은 영향도
    dominant_topics = dna.get('dominant_topics', [])
    topic_lower = topic.lower()
    is_new_topic = not any(topic_lower in t.lower() or t.lower() in topic_lower for t in dominant_topics)

    if is_new_topic:
        base_weight = min(1.0, base_weight + 0.1)

    # 유형 분포에서 부족한 유형이면 가산
    type_dist = dna.get('content_type_distribution', {})
    if content_type not in type_dist or type_dist.get(content_type, 0) < 0.1:
        base_weight = min(1.0, base_weight + 0.05)

    return round(base_weight, 2)


def _determine_priority(impact: float) -> str:
    """영향도 기반 우선순위를 결정합니다."""
    if impact >= 0.8:
        return 'high'
    elif impact >= 0.6:
        return 'medium'
    return 'low'


def _recommend_from_gaps(
    dna: Dict,
    gaps: List[str],
) -> List[ContentRecommendation]:
    """갭 목록에서 추천을 생성합니다.

    갭에 명시된 주제를 우선 추천합니다.
    """
    recommendations = []

    # 기존 유형 분포 확인
    type_dist = dna.get('content_type_distribution', {})

    # 가장 부족한 유형 찾기
    underrepresented_types = [
        t for t in _DIVERSIFICATION_TYPES
        if type_dist.get(t, 0) < 0.15
    ]

    for gap_topic in gaps:
        if not gap_topic or not gap_topic.strip():
            continue

        gap_topic = gap_topic.strip()

        # 부족한 유형이 있으면 해당 유형으로 추천, 없으면 blog
        if underrepresented_types:
            content_type = underrepresented_types[
                len(gap_topic) % len(underrepresented_types)
            ]
        else:
            content_type = 'blog'

        impact = _calculate_impact(gap_topic, content_type, is_gap=True, dna=dna)
        priority = _determine_priority(impact)

        recommendations.append(ContentRecommendation(
            topic=gap_topic,
            content_type=content_type,
            priority=priority,
            reason=f"콘텐츠 갭 영역: '{gap_topic}'에 대한 콘텐츠가 부족합니다",
            estimated_impact=impact,
        ))

    return recommendations


def _recommend_from_dna(
    dna: Dict,
    existing_topics: set,
) -> List[ContentRecommendation]:
    """DNA 프로파일에서 추천을 생성합니다.

    기존 강점 영역의 심화/확장 + 유형 다각화를 추천합니다.
    """
    recommendations = []
    dominant_topics = dna.get('dominant_topics', [])
    type_dist = dna.get('content_type_distribution', {})
    tone = dna.get('tone_profile', {})

    # 1) 강점 주제 심화 추천
    for topic in dominant_topics[:3]:
        if topic.lower() in existing_topics:
            continue

        # 기술 톤이 높으면 tutorial, 캐주얼이면 sns_post, 기본은 blog
        if tone.get('technical', 0) > 0.4:
            content_type = 'tutorial'
            reason = f"기술 콘텐츠 강점 영역 '{topic}'의 튜토리얼 확장을 추천합니다"
        elif tone.get('casual', 0) > 0.4:
            content_type = 'sns_post'
            reason = f"캐주얼 톤의 강점 주제 '{topic}'을 SNS 콘텐츠로 확장할 수 있습니다"
        else:
            content_type = 'blog'
            reason = f"핵심 주제 '{topic}'에 대한 심화 블로그 포스트를 추천합니다"

        impact = _calculate_impact(topic, content_type, is_gap=False, dna=dna)
        priority = _determine_priority(impact)

        recommendations.append(ContentRecommendation(
            topic=topic,
            content_type=content_type,
            priority=priority,
            reason=reason,
            estimated_impact=impact,
        ))
        existing_topics.add(topic.lower())

    # 2) 유형 다각화 추천
    for diversify_type in _DIVERSIFICATION_TYPES:
        if type_dist.get(diversify_type, 0) >= 0.15:
            continue

        # 기존 주제 중 하나를 다른 유형으로 추천
        available_topic = None
        for topic in dominant_topics:
            topic_type_key = f"{topic.lower()}_{diversify_type}"
            if topic_type_key not in existing_topics:
                available_topic = topic
                existing_topics.add(topic_type_key)
                break

        if not available_topic:
            continue

        impact = _calculate_impact(available_topic, diversify_type, is_gap=False, dna=dna)
        priority = _determine_priority(impact)

        recommendations.append(ContentRecommendation(
            topic=available_topic,
            content_type=diversify_type,
            priority=priority,
            reason=f"'{diversify_type}' 유형의 콘텐츠가 부족합니다. '{available_topic}' 주제로 다각화를 추천합니다",
            estimated_impact=impact,
        ))

    return recommendations


def recommend_next(
    dna: Dict,
    gaps: Optional[List[str]] = None,
) -> List[ContentRecommendation]:
    """다음 생성할 콘텐츠를 추천합니다.

    Args:
        dna: ContentDNA를 dict로 변환한 프로파일
            - dominant_topics: list[str]
            - tone_profile: dict
            - content_type_distribution: dict
        gaps: 부족한 주제 목록 (우선 추천)

    Returns:
        추천 목록 (priority 내림차순 → impact 내림차순)
    """
    if not dna or not isinstance(dna, dict):
        return []

    existing_topics: set = set()
    recommendations: List[ContentRecommendation] = []

    # 1) 갭 기반 추천 (우선)
    if gaps:
        gap_recs = _recommend_from_gaps(dna, gaps)
        recommendations.extend(gap_recs)
        existing_topics.update(r.topic.lower() for r in gap_recs)

    # 2) DNA 기반 추천
    dna_recs = _recommend_from_dna(dna, existing_topics)
    recommendations.extend(dna_recs)

    # (topic, content_type) 중복 제거 — 먼저 추가된 항목 유지
    seen_keys: set = set()
    unique_recs: List[ContentRecommendation] = []
    for rec in recommendations:
        key = (rec.topic.lower(), rec.content_type)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_recs.append(rec)

    # 우선순위 정렬: high > medium > low → 같은 우선순위 내에서 impact 내림차순
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    unique_recs.sort(
        key=lambda r: (priority_order.get(r.priority, 3), -r.estimated_impact)
    )

    return unique_recs
