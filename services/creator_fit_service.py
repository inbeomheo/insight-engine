"""크리에이터 적합도 점수 서비스

두 프로필(크리에이터 vs 브랜드/채널)의 교차 추천 적합도를 분석하여
토픽 오버랩, 강점, 리스크, 종합 점수(0~100)를 산출한다.
"""
from dataclasses import dataclass, field


@dataclass
class FitScore:
    """크리에이터-브랜드 적합도 점수"""
    creator_name: str                    # 크리에이터 이름
    score: float                         # 종합 점수 0~100
    overlap_topics: list[str] = field(default_factory=list)   # 공통 토픽
    strengths: list[str] = field(default_factory=list)        # 강점
    risks: list[str] = field(default_factory=list)            # 리스크
    recommendation: str = ""             # 종합 추천 문구


# ── 톤 호환성 매트릭스 ────────────────────────────────────────
# 각 톤 쌍의 호환도 (0~1). 양방향 대칭.
_TONE_COMPATIBILITY: dict[tuple[str, str], float] = {
    ("professional", "professional"): 1.0,
    ("professional", "casual"): 0.4,
    ("professional", "humorous"): 0.3,
    ("professional", "educational"): 0.8,
    ("professional", "inspirational"): 0.7,
    ("casual", "casual"): 1.0,
    ("casual", "humorous"): 0.9,
    ("casual", "educational"): 0.5,
    ("casual", "inspirational"): 0.6,
    ("humorous", "humorous"): 1.0,
    ("humorous", "educational"): 0.4,
    ("humorous", "inspirational"): 0.5,
    ("educational", "educational"): 1.0,
    ("educational", "inspirational"): 0.7,
    ("inspirational", "inspirational"): 1.0,
}


def _normalize_topics(topics: list) -> set[str]:
    """토픽 리스트를 정규화된 소문자 집합으로 변환한다.

    Args:
        topics: 토픽 문자열 리스트

    Returns:
        정규화된 토픽 집합
    """
    result = set()
    for t in topics:
        if isinstance(t, str) and t.strip():
            result.add(t.strip().lower())
    return result


def _compute_topic_overlap(
    creator_topics: set[str],
    our_topics: set[str],
) -> tuple[float, list[str]]:
    """토픽 오버랩 점수를 계산한다.

    Jaccard 유사도 기반 (교집합 / 합집합).

    Args:
        creator_topics: 크리에이터 토픽 집합
        our_topics: 우리 토픽 집합

    Returns:
        (점수 0~1, 공통 토픽 리스트)
    """
    if not creator_topics and not our_topics:
        return 0.0, []

    overlap = creator_topics & our_topics
    union = creator_topics | our_topics

    if not union:
        return 0.0, []

    score = len(overlap) / len(union)
    return score, sorted(overlap)


def _compute_tone_score(creator_tone: str, our_tone: str) -> float:
    """톤 호환성 점수를 계산한다.

    Args:
        creator_tone: 크리에이터의 톤
        our_tone: 우리의 톤

    Returns:
        호환성 점수 (0~1). 알 수 없는 톤은 0.5 반환.
    """
    t1 = creator_tone.strip().lower() if creator_tone else ""
    t2 = our_tone.strip().lower() if our_tone else ""

    if not t1 or not t2:
        return 0.5  # 정보 부족 시 중립

    # 동일 톤
    if t1 == t2:
        return 1.0

    # 매트릭스에서 양방향 조회
    key = (t1, t2)
    if key in _TONE_COMPATIBILITY:
        return _TONE_COMPATIBILITY[key]

    key_rev = (t2, t1)
    if key_rev in _TONE_COMPATIBILITY:
        return _TONE_COMPATIBILITY[key_rev]

    # 매트릭스에 없는 톤 조합
    return 0.5


def _compute_audience_score(
    creator_audience: int,
    our_audience: int,
) -> float:
    """오디언스 규모 균형 점수를 계산한다.

    규모 차이가 작을수록 높은 점수. 10배 이상 차이 시 낮은 점수.

    Args:
        creator_audience: 크리에이터 오디언스 규모
        our_audience: 우리 오디언스 규모

    Returns:
        균형 점수 (0~1)
    """
    if creator_audience <= 0 or our_audience <= 0:
        return 0.3  # 정보 부족

    ratio = max(creator_audience, our_audience) / min(creator_audience, our_audience)

    # 1:1 = 1.0, 2:1 = 0.85, 5:1 = 0.55, 10:1 = 0.3, 20:1+ = 0.1
    if ratio <= 1.5:
        return 1.0
    elif ratio <= 3:
        return 0.8
    elif ratio <= 5:
        return 0.6
    elif ratio <= 10:
        return 0.4
    elif ratio <= 20:
        return 0.2
    else:
        return 0.1


def _identify_strengths(
    topic_score: float,
    tone_score: float,
    audience_score: float,
    overlap_topics: list[str],
    creator_profile: dict,
) -> list[str]:
    """협업 강점을 식별한다.

    Args:
        topic_score: 토픽 오버랩 점수
        tone_score: 톤 호환성 점수
        audience_score: 오디언스 균형 점수
        overlap_topics: 공통 토픽 리스트
        creator_profile: 크리에이터 프로필

    Returns:
        강점 문자열 리스트
    """
    strengths = []

    if topic_score >= 0.5:
        topics_str = ", ".join(overlap_topics[:3])
        strengths.append(f"공통 관심 토픽이 풍부합니다: {topics_str}")
    elif topic_score >= 0.25:
        strengths.append("일부 토픽이 겹쳐 교차 홍보 효과가 기대됩니다.")

    if tone_score >= 0.8:
        strengths.append("콘텐츠 톤이 매우 잘 맞아 자연스러운 협업이 가능합니다.")
    elif tone_score >= 0.6:
        strengths.append("톤 차이가 적어 일관된 메시지 전달이 가능합니다.")

    if audience_score >= 0.8:
        strengths.append("오디언스 규모가 비슷해 상호 이익이 됩니다.")

    audience_size = creator_profile.get("audience_size", 0)
    if audience_size >= 100000:
        strengths.append(f"크리에이터 영향력이 큽니다 (팔로워 {audience_size:,}명).")
    elif audience_size >= 10000:
        strengths.append("중간 규모 오디언스로 집중 타게팅에 적합합니다.")

    return strengths


def _identify_risks(
    topic_score: float,
    tone_score: float,
    audience_score: float,
    creator_profile: dict,
    our_profile: dict,
) -> list[str]:
    """협업 리스크를 식별한다.

    Args:
        topic_score: 토픽 오버랩 점수
        tone_score: 톤 호환성 점수
        audience_score: 오디언스 균형 점수
        creator_profile: 크리에이터 프로필
        our_profile: 우리 프로필

    Returns:
        리스크 문자열 리스트
    """
    risks = []

    if topic_score < 0.1:
        risks.append("토픽 겹침이 거의 없어 오디언스 관심이 분산될 수 있습니다.")

    if tone_score < 0.4:
        creator_tone = creator_profile.get("tone", "알 수 없음")
        our_tone = our_profile.get("tone", "알 수 없음")
        risks.append(f"톤 차이가 큽니다 ({creator_tone} vs {our_tone}). 메시지 불일치 위험.")

    if audience_score < 0.3:
        risks.append("오디언스 규모 차이가 커서 한쪽에 편향된 효과가 우려됩니다.")

    creator_audience = creator_profile.get("audience_size", 0)
    if creator_audience < 1000:
        risks.append("크리에이터 오디언스가 매우 적어 노출 효과가 제한적입니다.")

    our_audience = our_profile.get("audience_size", 0)
    if our_audience > 0 and creator_audience > 0:
        ratio = creator_audience / our_audience
        if ratio > 20:
            risks.append("크리에이터 규모가 압도적으로 커서 협상력이 낮을 수 있습니다.")

    return risks


def _generate_recommendation(
    score: float,
    strengths: list[str],
    risks: list[str],
) -> str:
    """종합 추천 문구를 생성한다.

    Args:
        score: 종합 점수 (0~100)
        strengths: 강점 리스트
        risks: 리스크 리스트

    Returns:
        추천 문구 문자열
    """
    if score >= 80:
        return "매우 적합합니다. 적극적으로 협업을 추진하세요."
    elif score >= 60:
        return "적합한 편입니다. 토픽/톤 조율 후 협업을 검토하세요."
    elif score >= 40:
        return "보통 수준입니다. 특정 캠페인에 한해 시범 협업을 고려하세요."
    elif score >= 20:
        return "적합도가 낮습니다. 다른 크리에이터를 우선 검토하세요."
    else:
        return "부적합합니다. 타겟 오디언스와의 정합성을 재검토하세요."


def score_creator_fit(
    creator_profile: dict,
    our_profile: dict,
) -> FitScore:
    """크리에이터-브랜드 교차 추천 적합도를 점수화한다.

    종합 점수 = 토픽 오버랩(40%) + 톤 호환성(30%) + 오디언스 균형(30%)

    Args:
        creator_profile: 크리에이터 프로필
            {"name": str, "topics": list, "audience_size": int, "tone": str}
        our_profile: 우리(브랜드/채널) 프로필
            {"name": str, "topics": list, "audience_size": int, "tone": str}

    Returns:
        FitScore 데이터클래스

    Raises:
        ValueError: creator_profile 또는 our_profile이 None인 경우
        ValueError: creator_profile에 name이 없는 경우
    """
    if creator_profile is None:
        raise ValueError("creator_profile은 None일 수 없습니다")
    if our_profile is None:
        raise ValueError("our_profile은 None일 수 없습니다")

    creator_name = creator_profile.get("name", "").strip()
    if not creator_name:
        raise ValueError("creator_profile에 name이 필요합니다")

    # 토픽 분석
    creator_topics = _normalize_topics(creator_profile.get("topics", []))
    our_topics = _normalize_topics(our_profile.get("topics", []))
    topic_score, overlap_topics = _compute_topic_overlap(creator_topics, our_topics)

    # 톤 분석
    creator_tone = creator_profile.get("tone", "")
    our_tone = our_profile.get("tone", "")
    tone_score = _compute_tone_score(creator_tone, our_tone)

    # 오디언스 분석
    creator_audience = creator_profile.get("audience_size", 0)
    our_audience = our_profile.get("audience_size", 0)
    audience_score = _compute_audience_score(creator_audience, our_audience)

    # 종합 점수: 토픽 40% + 톤 30% + 오디언스 30%
    raw_score = (topic_score * 40) + (tone_score * 30) + (audience_score * 30)
    final_score = round(min(100.0, max(0.0, raw_score)), 1)

    # 강점/리스크 식별
    strengths = _identify_strengths(
        topic_score, tone_score, audience_score, overlap_topics, creator_profile,
    )
    risks = _identify_risks(
        topic_score, tone_score, audience_score, creator_profile, our_profile,
    )

    # 추천
    recommendation = _generate_recommendation(final_score, strengths, risks)

    return FitScore(
        creator_name=creator_name,
        score=final_score,
        overlap_topics=overlap_topics,
        strengths=strengths,
        risks=risks,
        recommendation=recommendation,
    )


def rank_creators(
    creators: list[dict],
    our_profile: dict,
    top_n: int = 10,
) -> list[FitScore]:
    """여러 크리에이터를 적합도 순으로 랭킹한다.

    Args:
        creators: 크리에이터 프로필 리스트
        our_profile: 우리 프로필
        top_n: 상위 N명 반환

    Returns:
        FitScore 리스트 (점수 내림차순)

    Raises:
        ValueError: creators가 None이거나 our_profile이 None인 경우
    """
    if creators is None:
        raise ValueError("creators는 None일 수 없습니다")
    if our_profile is None:
        raise ValueError("our_profile은 None일 수 없습니다")

    results = []
    for creator in creators:
        try:
            fit = score_creator_fit(creator, our_profile)
            results.append(fit)
        except ValueError:
            # name이 없는 등 유효하지 않은 프로필은 건너뜀
            continue

    results.sort(key=lambda f: f.score, reverse=True)
    return results[:top_n]
