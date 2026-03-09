"""크리에이터 매처 서비스 — 의미 유사도 기반 크리에이터 매칭.

채널 프로필과 후보 크리에이터 리스트를 비교하여
토픽 오버랩, 오디언스 유사도, 협업 아이디어를 포함한
매칭 점수(0~100)를 산출한다. 순수 규칙 기반 (AI 호출 없음).
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

@dataclass
class MatchResult:
    """크리에이터 매칭 결과"""
    creator_name: str               # 크리에이터 이름
    match_score: float              # 종합 매칭 점수 0~100
    shared_topics: list[str] = field(default_factory=list)    # 공통 토픽
    audience_overlap: float = 0.0   # 오디언스 오버랩 추정치 0~1
    collaboration_ideas: list[str] = field(default_factory=list)  # 협업 아이디어


# ---------------------------------------------------------------------------
# 상수
# ---------------------------------------------------------------------------

# 토픽 유사도 매트릭스 (간접 관련 토픽 간 유사도)
_TOPIC_SIMILARITY: dict[tuple[str, str], float] = {
    ("tech", "ai"): 0.7,
    ("tech", "design"): 0.4,
    ("tech", "gaming"): 0.3,
    ("tech", "business"): 0.3,
    ("ai", "education"): 0.4,
    ("ai", "business"): 0.3,
    ("marketing", "business"): 0.6,
    ("marketing", "design"): 0.4,
    ("marketing", "sns"): 0.5,
    ("business", "finance"): 0.5,
    ("business", "education"): 0.3,
    ("design", "gaming"): 0.3,
    ("health", "education"): 0.2,
    ("health", "lifestyle"): 0.5,
    ("gaming", "entertainment"): 0.6,
    ("education", "tech"): 0.3,
    ("finance", "education"): 0.3,
}

# 토픽별 협업 아이디어 템플릿
_COLLAB_IDEAS: dict[str, list[str]] = {
    "tech": [
        "기술 리뷰 크로스 콘텐츠 제작",
        "공동 튜토리얼/워크숍 시리즈",
        "테크 트렌드 토론 라이브 방송",
    ],
    "ai": [
        "AI 도구 활용 공동 실험 콘텐츠",
        "AI 트렌드 분석 콜라보 영상",
        "프롬프트 엔지니어링 챌린지",
    ],
    "marketing": [
        "마케팅 성공 사례 공동 분석",
        "브랜드 전략 크로스 인터뷰",
        "공동 캠페인 집행 후기",
    ],
    "design": [
        "디자인 챌린지 콜라보",
        "포트폴리오 리뷰 크로스 콘텐츠",
        "UI/UX 트렌드 공동 분석",
    ],
    "business": [
        "비즈니스 인사이트 공동 뉴스레터",
        "창업 경험 크로스 인터뷰",
        "업계 분석 콜라보 리포트",
    ],
    "education": [
        "공동 강의/커리큘럼 제작",
        "학습 팁 공유 콜라보 시리즈",
        "교육 콘텐츠 크로스 프로모션",
    ],
    "finance": [
        "재테크/투자 전략 공동 분석",
        "경제 이슈 토론 콜라보",
        "포트폴리오 구성 크로스 콘텐츠",
    ],
    "health": [
        "건강/운동 루틴 공유 콜라보",
        "영양/식단 크로스 콘텐츠",
        "웰니스 챌린지 공동 진행",
    ],
    "gaming": [
        "게임 플레이 크로스 스트리밍",
        "게임 리뷰 콜라보 영상",
        "e스포츠 이벤트 공동 중계",
    ],
}

# 범용 협업 아이디어 (토픽 무관)
_GENERIC_COLLAB_IDEAS = [
    "게스트 출연 교차 인터뷰",
    "공동 라이브 Q&A 세션",
    "크로스 프로모션 쇼츠/릴스",
    "공동 뉴스레터 기고",
]

# 토픽 정규화 (중복 방지)
_TOPIC_NORMALIZE: dict[str, str] = {
    "technology": "tech", "programming": "tech", "coding": "tech",
    "소프트웨어": "tech", "개발": "tech", "프로그래밍": "tech", "기술": "tech",
    "artificial intelligence": "ai", "machine learning": "ai",
    "인공지능": "ai", "머신러닝": "ai", "딥러닝": "ai",
    "마케팅": "marketing", "광고": "marketing", "브랜딩": "marketing",
    "디자인": "design", "ui": "design", "ux": "design",
    "경영": "business", "비즈니스": "business", "스타트업": "business", "창업": "business",
    "교육": "education", "학습": "education",
    "투자": "finance", "금융": "finance", "재테크": "finance",
    "건강": "health", "피트니스": "health", "운동": "health",
    "게임": "gaming", "esports": "gaming",
    "엔터테인먼트": "entertainment", "여행": "lifestyle",
}


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _normalize_topic(topic: str) -> str:
    """토픽을 표준 키로 정규화한다."""
    lower = topic.strip().lower()
    return _TOPIC_NORMALIZE.get(lower, lower)


def _normalize_topics(topics: list) -> list[str]:
    """토픽 리스트를 정규화하고 중복 제거한다."""
    seen: set[str] = set()
    result: list[str] = []
    for t in topics:
        if not isinstance(t, str) or not t.strip():
            continue
        norm = _normalize_topic(t)
        if norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def _compute_direct_overlap(topics_a: list[str], topics_b: list[str]) -> tuple[float, list[str]]:
    """직접 토픽 오버랩을 계산한다 (Jaccard 유사도).

    Args:
        topics_a: 정규화된 토픽 리스트 A
        topics_b: 정규화된 토픽 리스트 B

    Returns:
        (오버랩 점수 0~1, 공통 토픽 리스트)
    """
    set_a = set(topics_a)
    set_b = set(topics_b)

    if not set_a and not set_b:
        return 0.0, []

    shared = set_a & set_b
    union = set_a | set_b

    if not union:
        return 0.0, []

    score = len(shared) / len(union)
    return score, sorted(shared)


def _compute_indirect_similarity(topics_a: list[str], topics_b: list[str]) -> float:
    """간접 토픽 유사도를 계산한다.

    직접 오버랩이 아닌, 유사 매트릭스 기반 관련도.

    Args:
        topics_a: 정규화된 토픽 리스트 A
        topics_b: 정규화된 토픽 리스트 B

    Returns:
        간접 유사도 점수 0~1
    """
    if not topics_a or not topics_b:
        return 0.0

    total_sim = 0.0
    pair_count = 0

    for ta in topics_a:
        for tb in topics_b:
            if ta == tb:
                continue  # 직접 오버랩은 제외
            pair = (ta, tb)
            pair_rev = (tb, ta)

            sim = _TOPIC_SIMILARITY.get(pair, 0.0)
            if sim == 0.0:
                sim = _TOPIC_SIMILARITY.get(pair_rev, 0.0)

            if sim > 0:
                total_sim += sim
                pair_count += 1

    if pair_count == 0:
        return 0.0

    # 평균 간접 유사도 (최대 0.5로 캡 — 직접 오버랩보다 약해야 함)
    avg = total_sim / pair_count
    return min(avg, 0.5)


def _compute_audience_overlap(
    channel_audience: int,
    candidate_audience: int,
) -> float:
    """오디언스 규모 기반 오버랩 추정치를 계산한다.

    규모가 비슷할수록 높은 오버랩. 극단적 차이 시 낮은 값.

    Args:
        channel_audience: 채널 오디언스 규모
        candidate_audience: 후보 오디언스 규모

    Returns:
        오버랩 추정치 0~1
    """
    if channel_audience <= 0 or candidate_audience <= 0:
        return 0.2  # 정보 부족

    smaller = min(channel_audience, candidate_audience)
    larger = max(channel_audience, candidate_audience)
    ratio = smaller / larger

    # ratio 1.0 → 0.9, ratio 0.5 → 0.65, ratio 0.1 → 0.25, ratio 0.01 → 0.1
    if ratio >= 0.8:
        return 0.9
    elif ratio >= 0.5:
        return 0.7
    elif ratio >= 0.2:
        return 0.5
    elif ratio >= 0.05:
        return 0.3
    else:
        return 0.1


def _generate_collaboration_ideas(
    shared_topics: list[str],
    all_channel_topics: list[str],
    all_candidate_topics: list[str],
) -> list[str]:
    """공통 토픽 기반 협업 아이디어를 생성한다.

    Args:
        shared_topics: 공통 토픽 리스트
        all_channel_topics: 채널의 전체 토픽
        all_candidate_topics: 후보의 전체 토픽

    Returns:
        협업 아이디어 문자열 리스트 (1~5개)
    """
    ideas: list[str] = []
    seen: set[str] = set()

    # 1순위: 공통 토픽 기반 아이디어
    for topic in shared_topics:
        topic_ideas = _COLLAB_IDEAS.get(topic, [])
        for idea in topic_ideas:
            if idea not in seen and len(ideas) < 5:
                ideas.append(idea)
                seen.add(idea)

    # 2순위: 채널/후보 토픽 조합 아이디어
    combined = set(all_channel_topics) | set(all_candidate_topics)
    for topic in combined:
        if len(ideas) >= 4:
            break
        topic_ideas = _COLLAB_IDEAS.get(topic, [])
        for idea in topic_ideas:
            if idea not in seen and len(ideas) < 5:
                ideas.append(idea)
                seen.add(idea)

    # 3순위: 범용 아이디어로 최소 1개 보장
    if not ideas:
        for idea in _GENERIC_COLLAB_IDEAS:
            if idea not in seen and len(ideas) < 3:
                ideas.append(idea)
                seen.add(idea)

    return ideas


def _compute_match_score(
    direct_overlap: float,
    indirect_similarity: float,
    audience_overlap: float,
) -> float:
    """종합 매칭 점수를 계산한다.

    직접 토픽 오버랩(50%) + 간접 유사도(20%) + 오디언스 오버랩(30%)

    Args:
        direct_overlap: 직접 토픽 오버랩 0~1
        indirect_similarity: 간접 토픽 유사도 0~1
        audience_overlap: 오디언스 오버랩 0~1

    Returns:
        종합 점수 0~100
    """
    raw = (direct_overlap * 50) + (indirect_similarity * 20) + (audience_overlap * 30)
    return round(min(100.0, max(0.0, raw)), 1)


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def match_creators(
    channel_profile: dict,
    candidates: list[dict],
) -> list[MatchResult]:
    """채널 프로필과 후보 크리에이터를 매칭한다.

    의미 유사도 기반으로 각 후보의 매칭 점수(0~100)를 산출하고
    점수 내림차순으로 정렬하여 반환한다.

    Args:
        channel_profile: 채널 프로필
            {"name": "...", "topics": [...], "audience_size": N, "tone": "..."}
        candidates: 후보 크리에이터 리스트
            [{"name": "...", "topics": [...], "audience_size": N}]

    Returns:
        MatchResult 리스트 (점수 내림차순)

    Raises:
        ValueError: channel_profile이 None이거나 name이 없는 경우
        ValueError: candidates가 None인 경우
    """
    if channel_profile is None:
        raise ValueError("channel_profile은 None일 수 없습니다")
    if candidates is None:
        raise ValueError("candidates는 None일 수 없습니다")

    channel_name = channel_profile.get("name", "").strip()
    if not channel_name:
        raise ValueError("channel_profile에 name이 필요합니다")

    channel_topics = _normalize_topics(channel_profile.get("topics", []))
    channel_audience = channel_profile.get("audience_size", 0)
    if not isinstance(channel_audience, (int, float)):
        channel_audience = 0

    results: list[MatchResult] = []

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        cand_name = candidate.get("name", "").strip()
        if not cand_name:
            continue  # 이름 없는 후보 건너뜀

        cand_topics = _normalize_topics(candidate.get("topics", []))
        cand_audience = candidate.get("audience_size", 0)
        if not isinstance(cand_audience, (int, float)):
            cand_audience = 0

        # 점수 계산
        direct_overlap, shared = _compute_direct_overlap(channel_topics, cand_topics)
        indirect_sim = _compute_indirect_similarity(channel_topics, cand_topics)
        aud_overlap = _compute_audience_overlap(int(channel_audience), int(cand_audience))

        score = _compute_match_score(direct_overlap, indirect_sim, aud_overlap)

        # 협업 아이디어
        ideas = _generate_collaboration_ideas(shared, channel_topics, cand_topics)

        results.append(MatchResult(
            creator_name=cand_name,
            match_score=score,
            shared_topics=shared,
            audience_overlap=round(aud_overlap, 2),
            collaboration_ideas=ideas,
        ))

    # 점수 내림차순 정렬
    results.sort(key=lambda r: r.match_score, reverse=True)

    return results
