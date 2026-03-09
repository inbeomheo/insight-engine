"""영향원 레이더 서비스 — 오디언스 데이터에서 숨겨진 영향원을 발굴한다.

규칙 기반으로 커뮤니티, 매체, 인플루언서, 플랫폼, 트렌드 등
잠재적 영향원을 최소 5개 이상 발굴하여 관련도 순으로 정렬한다.
"""

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# 데이터 모델
# ---------------------------------------------------------------------------

@dataclass
class InfluenceSource:
    """발굴된 영향원 정보"""
    name: str                   # 영향원 이름
    source_type: str            # "community"|"publication"|"influencer"|"platform"|"trend"
    relevance: float            # 관련도 0~1
    reach_estimate: int         # 추정 도달 규모
    description: str            # 설명


# ---------------------------------------------------------------------------
# 상수 / 규칙 사전
# ---------------------------------------------------------------------------

# 토픽 → 커뮤니티 매핑
_TOPIC_COMMUNITIES: dict[str, list[dict]] = {
    "tech": [
        {"name": "Hacker News", "reach": 500_000, "desc": "기술 뉴스/토론 커뮤니티"},
        {"name": "Reddit r/programming", "reach": 5_000_000, "desc": "프로그래밍 서브레딧"},
        {"name": "GeekNews", "reach": 100_000, "desc": "한국어 기술 뉴스 큐레이션"},
    ],
    "ai": [
        {"name": "Reddit r/MachineLearning", "reach": 3_000_000, "desc": "ML/AI 연구 커뮤니티"},
        {"name": "Hugging Face Community", "reach": 1_000_000, "desc": "오픈소스 AI 모델 커뮤니티"},
        {"name": "AI Twitter/X", "reach": 10_000_000, "desc": "AI 연구자/실무자 네트워크"},
    ],
    "marketing": [
        {"name": "GrowthHackers", "reach": 200_000, "desc": "그로스 마케팅 커뮤니티"},
        {"name": "Indiehackers", "reach": 300_000, "desc": "인디 메이커/마케터 커뮤니티"},
        {"name": "마케터 모여라 (카페)", "reach": 150_000, "desc": "한국 마케터 네이버 카페"},
    ],
    "design": [
        {"name": "Dribbble", "reach": 5_000_000, "desc": "디자인 포트폴리오 플랫폼"},
        {"name": "Behance", "reach": 10_000_000, "desc": "크리에이티브 작품 쇼케이스"},
        {"name": "디자인 스펙트럼", "reach": 50_000, "desc": "한국 디자인 미디엄 퍼블리케이션"},
    ],
    "business": [
        {"name": "LinkedIn Groups", "reach": 2_000_000, "desc": "비즈니스 전문가 네트워크"},
        {"name": "EO/YPO 네트워크", "reach": 30_000, "desc": "기업가 피어 그룹"},
        {"name": "스타트업 얼라이언스", "reach": 80_000, "desc": "한국 스타트업 생태계 허브"},
    ],
    "education": [
        {"name": "Coursera Community", "reach": 1_000_000, "desc": "온라인 교육 학습자 커뮤니티"},
        {"name": "클래스101 커뮤니티", "reach": 200_000, "desc": "한국 온라인 클래스 플랫폼"},
        {"name": "에듀테크 포럼", "reach": 50_000, "desc": "교육 기술 전문가 네트워크"},
    ],
    "finance": [
        {"name": "Reddit r/investing", "reach": 2_000_000, "desc": "투자 토론 커뮤니티"},
        {"name": "한경 투자클럽", "reach": 300_000, "desc": "한국 투자자 커뮤니티"},
        {"name": "FinTwit", "reach": 5_000_000, "desc": "금융 트위터 네트워크"},
    ],
    "health": [
        {"name": "Reddit r/fitness", "reach": 10_000_000, "desc": "피트니스/건강 커뮤니티"},
        {"name": "건강in", "reach": 100_000, "desc": "한국 건강 정보 커뮤니티"},
        {"name": "WebMD Community", "reach": 3_000_000, "desc": "건강 정보 공유 포럼"},
    ],
    "gaming": [
        {"name": "Reddit r/gaming", "reach": 35_000_000, "desc": "게이밍 메가 커뮤니티"},
        {"name": "디시인사이드 게임 갤러리", "reach": 500_000, "desc": "한국 게임 커뮤니티"},
        {"name": "Discord Gaming Servers", "reach": 20_000_000, "desc": "게이머 디스코드 서버 네트워크"},
    ],
}

# 토픽 → 매체(publication) 매핑
_TOPIC_PUBLICATIONS: dict[str, list[dict]] = {
    "tech": [
        {"name": "TechCrunch", "reach": 15_000_000, "desc": "글로벌 테크 미디어"},
        {"name": "요즘IT", "reach": 300_000, "desc": "한국 IT 인사이트 미디어"},
    ],
    "ai": [
        {"name": "MIT Technology Review", "reach": 3_000_000, "desc": "AI/기술 심층 분석 매체"},
        {"name": "AI타임스", "reach": 100_000, "desc": "한국 AI 전문 매체"},
    ],
    "marketing": [
        {"name": "Content Marketing Institute", "reach": 500_000, "desc": "콘텐츠 마케팅 리서치 매체"},
        {"name": "브런치", "reach": 1_000_000, "desc": "한국 마케팅/에세이 퍼블리싱 플랫폼"},
    ],
    "business": [
        {"name": "Harvard Business Review", "reach": 10_000_000, "desc": "경영 전문 매체"},
        {"name": "플래텀", "reach": 200_000, "desc": "한국 스타트업 미디어"},
    ],
    "design": [
        {"name": "Smashing Magazine", "reach": 2_000_000, "desc": "웹 디자인/개발 매체"},
        {"name": "디스이즈게임", "reach": 300_000, "desc": "게임 디자인 미디어"},
    ],
}

# 플랫폼 도달 규모 참조
_PLATFORM_REACH: dict[str, int] = {
    "youtube": 2_000_000_000,
    "instagram": 1_500_000_000,
    "tiktok": 1_200_000_000,
    "twitter": 500_000_000,
    "linkedin": 900_000_000,
    "facebook": 3_000_000_000,
    "pinterest": 400_000_000,
    "reddit": 500_000_000,
    "naver_blog": 30_000_000,
    "brunch": 1_000_000,
    "threads": 200_000_000,
}

# 인구통계 → 트렌드 키워드
_DEMOGRAPHIC_TRENDS: dict[str, list[dict]] = {
    "gen_z": [
        {"name": "숏폼 콘텐츠 트렌드", "reach": 50_000_000, "desc": "15-60초 숏폼 영상 소비 확대"},
        {"name": "크리에이터 이코노미", "reach": 10_000_000, "desc": "개인 브랜딩 기반 수익화 트렌드"},
    ],
    "millennial": [
        {"name": "구독 경제", "reach": 20_000_000, "desc": "구독 기반 콘텐츠/서비스 소비 트렌드"},
        {"name": "사이드 프로젝트 문화", "reach": 5_000_000, "desc": "부업/창업 관심 증가 트렌드"},
    ],
    "gen_x": [
        {"name": "재테크/자산 관리", "reach": 15_000_000, "desc": "중장년 자산 관리 관심 트렌드"},
        {"name": "라이프스타일 콘텐츠", "reach": 8_000_000, "desc": "건강/여행/취미 콘텐츠 소비"},
    ],
}

# 토픽 정규화 사전 (유사 토픽 → 표준 키)
_TOPIC_ALIASES: dict[str, str] = {
    "technology": "tech", "programming": "tech", "coding": "tech",
    "software": "tech", "development": "tech", "web": "tech",
    "개발": "tech", "프로그래밍": "tech", "기술": "tech", "코딩": "tech",
    "artificial intelligence": "ai", "machine learning": "ai", "deep learning": "ai",
    "인공지능": "ai", "머신러닝": "ai", "딥러닝": "ai",
    "마케팅": "marketing", "광고": "marketing", "브랜딩": "marketing",
    "seo": "marketing", "content marketing": "marketing",
    "디자인": "design", "ux": "design", "ui": "design", "그래픽": "design",
    "경영": "business", "비즈니스": "business", "스타트업": "business",
    "창업": "business", "startup": "business", "entrepreneurship": "business",
    "교육": "education", "학습": "education", "온라인 강의": "education",
    "투자": "finance", "금융": "finance", "재테크": "finance", "주식": "finance",
    "건강": "health", "피트니스": "health", "운동": "health", "fitness": "health",
    "게임": "gaming", "gaming": "gaming", "esports": "gaming",
}


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _normalize_topic(topic: str) -> str:
    """토픽 문자열을 표준 키로 정규화한다."""
    lower = topic.strip().lower()
    return _TOPIC_ALIASES.get(lower, lower)


def _extract_normalized_topics(topics: list) -> list[str]:
    """토픽 리스트를 정규화하고 중복을 제거한다."""
    seen: set[str] = set()
    result: list[str] = []
    for t in topics:
        if not isinstance(t, str) or not t.strip():
            continue
        normalized = _normalize_topic(t)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def _detect_demographic_key(demographics: dict) -> str:
    """인구통계 데이터에서 세대 키를 추출한다."""
    if not demographics:
        return ""

    age = demographics.get("age", "")
    age_range = demographics.get("age_range", "")
    generation = demographics.get("generation", "")

    # 직접 세대 명시
    gen_lower = str(generation).lower()
    if gen_lower in ("gen_z", "z세대", "genz"):
        return "gen_z"
    if gen_lower in ("millennial", "밀레니얼", "millennials"):
        return "millennial"
    if gen_lower in ("gen_x", "x세대", "genx"):
        return "gen_x"

    # 나이로 추론
    age_str = str(age or age_range)
    try:
        # "25" 또는 "25-34" 형태 처리
        nums = [int(x) for x in age_str.replace("~", "-").split("-") if x.strip().isdigit()]
        if nums:
            avg_age = sum(nums) / len(nums)
            if avg_age < 28:
                return "gen_z"
            elif avg_age < 44:
                return "millennial"
            else:
                return "gen_x"
    except (ValueError, TypeError):
        pass

    return ""


def _compute_relevance(topic: str, topics: list[str], position_bonus: float = 0.0) -> float:
    """토픽의 관련도를 계산한다.

    첫 번째 토픽일수록 높은 관련도. 매칭된 토픽 수에 비례한 보너스.

    Args:
        topic: 매칭된 토픽 키
        topics: 전체 정규화된 토픽 리스트
        position_bonus: 추가 보너스 (0~0.2)

    Returns:
        관련도 0~1
    """
    if topic not in topics:
        return max(0.1, position_bonus)

    idx = topics.index(topic)
    # 첫 토픽 0.9, 두 번째 0.8, ... 최소 0.3
    base = max(0.3, 0.9 - idx * 0.1)
    return min(1.0, base + position_bonus)


def _scan_communities(topics: list[str]) -> list[InfluenceSource]:
    """토픽 기반 커뮤니티 영향원을 발굴한다."""
    sources: list[InfluenceSource] = []
    seen_names: set[str] = set()

    for topic in topics:
        entries = _TOPIC_COMMUNITIES.get(topic, [])
        for entry in entries:
            if entry["name"] in seen_names:
                continue
            seen_names.add(entry["name"])
            relevance = _compute_relevance(topic, topics)
            sources.append(InfluenceSource(
                name=entry["name"],
                source_type="community",
                relevance=round(relevance, 2),
                reach_estimate=entry["reach"],
                description=entry["desc"],
            ))

    return sources


def _scan_publications(topics: list[str]) -> list[InfluenceSource]:
    """토픽 기반 매체 영향원을 발굴한다."""
    sources: list[InfluenceSource] = []
    seen_names: set[str] = set()

    for topic in topics:
        entries = _TOPIC_PUBLICATIONS.get(topic, [])
        for entry in entries:
            if entry["name"] in seen_names:
                continue
            seen_names.add(entry["name"])
            relevance = _compute_relevance(topic, topics, position_bonus=0.05)
            sources.append(InfluenceSource(
                name=entry["name"],
                source_type="publication",
                relevance=round(relevance, 2),
                reach_estimate=entry["reach"],
                description=entry["desc"],
            ))

    return sources


def _scan_platforms(platforms: list) -> list[InfluenceSource]:
    """활성 플랫폼에서 영향원을 발굴한다."""
    sources: list[InfluenceSource] = []

    for i, platform in enumerate(platforms):
        if not isinstance(platform, str) or not platform.strip():
            continue
        key = platform.strip().lower().replace(" ", "_")
        reach = _PLATFORM_REACH.get(key, 100_000)

        # 순서가 앞일수록 주력 플랫폼으로 간주
        relevance = max(0.3, 0.85 - i * 0.1)

        sources.append(InfluenceSource(
            name=f"{platform.strip()} 네트워크",
            source_type="platform",
            relevance=round(relevance, 2),
            reach_estimate=reach,
            description=f"{platform.strip()} 플랫폼 오디언스 네트워크",
        ))

    return sources


def _scan_trends(demographics: dict) -> list[InfluenceSource]:
    """인구통계 기반 트렌드 영향원을 발굴한다."""
    demo_key = _detect_demographic_key(demographics)
    if not demo_key:
        return []

    entries = _DEMOGRAPHIC_TRENDS.get(demo_key, [])
    sources: list[InfluenceSource] = []

    for entry in entries:
        sources.append(InfluenceSource(
            name=entry["name"],
            source_type="trend",
            relevance=0.65,
            reach_estimate=entry["reach"],
            description=entry["desc"],
        ))

    return sources


def _scan_influencer_niches(topics: list[str], demographics: dict) -> list[InfluenceSource]:
    """토픽+인구통계 조합으로 인플루언서 니치를 추론한다."""
    sources: list[InfluenceSource] = []
    demo_key = _detect_demographic_key(demographics)

    # 토픽별 인플루언서 니치 매핑
    niche_map: dict[str, list[dict]] = {
        "tech": [
            {"name": "테크 유튜버/블로거", "reach": 2_000_000, "desc": "기술 리뷰/튜토리얼 크리에이터"},
        ],
        "ai": [
            {"name": "AI 연구자/교육자", "reach": 500_000, "desc": "AI 분야 KOL (Key Opinion Leader)"},
        ],
        "marketing": [
            {"name": "마케팅 인플루언서", "reach": 1_000_000, "desc": "디지털 마케팅 전문 크리에이터"},
        ],
        "design": [
            {"name": "디자인 크리에이터", "reach": 800_000, "desc": "디자인 프로세스 공유 크리에이터"},
        ],
        "business": [
            {"name": "비즈니스/창업 멘토", "reach": 1_500_000, "desc": "창업/경영 노하우 공유 인플루언서"},
        ],
        "education": [
            {"name": "에듀 크리에이터", "reach": 1_200_000, "desc": "교육/학습 콘텐츠 전문 크리에이터"},
        ],
        "finance": [
            {"name": "재테크 인플루언서", "reach": 3_000_000, "desc": "투자/재테크 정보 크리에이터"},
        ],
        "health": [
            {"name": "헬스/웰니스 크리에이터", "reach": 5_000_000, "desc": "건강/운동 콘텐츠 인플루언서"},
        ],
        "gaming": [
            {"name": "게임 스트리머/유튜버", "reach": 10_000_000, "desc": "게임 플레이/리뷰 크리에이터"},
        ],
    }

    seen_names: set[str] = set()
    for topic in topics:
        entries = niche_map.get(topic, [])
        for entry in entries:
            if entry["name"] in seen_names:
                continue
            seen_names.add(entry["name"])

            relevance = _compute_relevance(topic, topics, position_bonus=0.1)
            # 세대 매칭 시 보너스
            if demo_key:
                relevance = min(1.0, relevance + 0.05)

            sources.append(InfluenceSource(
                name=entry["name"],
                source_type="influencer",
                relevance=round(relevance, 2),
                reach_estimate=entry["reach"],
                description=entry["desc"],
            ))

    return sources


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

def scan_hidden_sources(audience_data: dict) -> list[InfluenceSource]:
    """오디언스 데이터에서 숨겨진 영향원을 발굴한다.

    최소 5개 이상의 영향원을 관련도 순으로 정렬하여 반환한다.

    Args:
        audience_data: 오디언스 데이터
            {
                "topics": ["tech", "ai", ...],
                "demographics": {"age": "25-34", "generation": "millennial"},
                "platforms": ["youtube", "twitter", ...]
            }

    Returns:
        InfluenceSource 리스트 (관련도 내림차순, 5개 이상)

    Raises:
        ValueError: audience_data가 None인 경우
    """
    if audience_data is None:
        raise ValueError("audience_data는 None일 수 없습니다")

    topics_raw = audience_data.get("topics", [])
    demographics = audience_data.get("demographics", {})
    platforms_raw = audience_data.get("platforms", [])

    # 토픽 정규화
    topics = _extract_normalized_topics(
        topics_raw if isinstance(topics_raw, list) else []
    )

    demographics = demographics if isinstance(demographics, dict) else {}
    platforms = platforms_raw if isinstance(platforms_raw, list) else []

    # 각 소스 유형별 스캔
    all_sources: list[InfluenceSource] = []
    all_sources.extend(_scan_communities(topics))
    all_sources.extend(_scan_publications(topics))
    all_sources.extend(_scan_platforms(platforms))
    all_sources.extend(_scan_trends(demographics))
    all_sources.extend(_scan_influencer_niches(topics, demographics))

    # 데이터가 부족해도 최소 5개 보장 — 범용 영향원 추가
    _FALLBACK_SOURCES = [
        InfluenceSource(
            name="YouTube 추천 알고리즘",
            source_type="platform",
            relevance=0.5,
            reach_estimate=2_000_000_000,
            description="YouTube 추천 시스템을 통한 자연 노출",
        ),
        InfluenceSource(
            name="Google 검색 (SEO)",
            source_type="platform",
            relevance=0.45,
            reach_estimate=5_000_000_000,
            description="검색엔진 최적화를 통한 오가닉 트래픽",
        ),
        InfluenceSource(
            name="소셜 미디어 공유 (바이럴)",
            source_type="trend",
            relevance=0.4,
            reach_estimate=1_000_000_000,
            description="소셜 미디어 자연 공유를 통한 바이럴 확산",
        ),
        InfluenceSource(
            name="뉴스레터/이메일 네트워크",
            source_type="publication",
            relevance=0.35,
            reach_estimate=500_000_000,
            description="이메일 기반 구독자 직접 도달",
        ),
        InfluenceSource(
            name="커뮤니티 WOM (입소문)",
            source_type="community",
            relevance=0.3,
            reach_estimate=100_000_000,
            description="커뮤니티 내 자발적 입소문 확산",
        ),
    ]

    # 이름 중복 방지
    existing_names = {s.name for s in all_sources}
    for fallback in _FALLBACK_SOURCES:
        if len(all_sources) >= 5:
            break
        if fallback.name not in existing_names:
            all_sources.append(fallback)
            existing_names.add(fallback.name)

    # 관련도 내림차순 정렬
    all_sources.sort(key=lambda s: s.relevance, reverse=True)

    return all_sources
