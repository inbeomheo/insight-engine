"""Narrative Explorer — 주제 주변 내러티브 탐색 서비스 (규칙 기반).

주어진 토픽과 소스 텍스트를 분석하여 AI API 호출 없이
주변 내러티브(관점, 감성, 근거)를 3개 이상 식별한다.
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 내러티브 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass
class Narrative:
    """탐색된 하나의 내러티브."""

    topic: str  # 내러티브가 다루는 세부 주제
    angle: str  # 관점/프레이밍 (예: "비용 절감", "기술 혁신")
    sentiment: str  # "positive" | "negative" | "neutral"
    strength: float  # 0~1, 해당 내러티브의 강도
    supporting_evidence: list[str] = field(default_factory=list)  # 근거 문장


# ---------------------------------------------------------------------------
# 내러티브 탐색용 사전 / 패턴
# ---------------------------------------------------------------------------

# 긍정 감성 키워드
_POSITIVE_KEYWORDS = [
    "좋은", "좋다", "훌륭", "장점", "이점", "성공", "효과적", "효율",
    "유용", "편리", "혁신", "성장", "발전", "긍정", "추천", "만족",
    "우수", "benefit", "good", "great", "success", "advantage",
    "improve", "growth", "positive", "best",
]

# 부정 감성 키워드
_NEGATIVE_KEYWORDS = [
    "나쁜", "나쁘다", "문제", "단점", "위험", "실패", "비효율", "부족",
    "어려움", "걱정", "우려", "비판", "한계", "리스크", "약점", "불편",
    "과제", "risk", "bad", "problem", "failure", "issue", "concern",
    "weakness", "challenge", "difficult", "danger",
]

# 관점(앵글) 사전 — 키워드 → 앵글 라벨
_ANGLE_PATTERNS: dict[str, list[str]] = {
    "비용/경제성": ["비용", "가격", "경제", "예산", "투자", "수익", "매출", "절감", "cost", "price", "budget", "roi"],
    "기술/혁신": ["기술", "혁신", "자동화", "ai", "ml", "디지털", "플랫폼", "tech", "innovation", "digital"],
    "사용자 경험": ["사용자", "ux", "ui", "편의", "접근성", "인터페이스", "경험", "user", "experience"],
    "보안/안전": ["보안", "안전", "해킹", "암호", "인증", "프라이버시", "개인정보", "security", "privacy", "safety"],
    "생산성/효율": ["생산성", "효율", "자동", "최적화", "시간", "속도", "performance", "productivity", "efficiency"],
    "시장/트렌드": ["시장", "트렌드", "경쟁", "점유율", "소비자", "수요", "market", "trend", "demand"],
    "환경/지속가능": ["환경", "지속가능", "친환경", "탄소", "재생", "그린", "esg", "green", "sustainability"],
    "법/규제": ["법", "규제", "정책", "컴플라이언스", "준수", "제도", "법률", "regulation", "compliance", "policy"],
    "교육/학습": ["교육", "학습", "훈련", "역량", "인재", "커리큘럼", "education", "learning", "training"],
    "사회적 영향": ["사회", "문화", "공동체", "공익", "윤리", "책임", "사회적", "social", "community", "ethics"],
}

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r"[.!?。]\s+|[.!?。]$|\n+")


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    raw = _SENTENCE_SPLIT.split(text)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    """텍스트에서 키워드 등장 횟수를 센다."""
    lower = text.lower()
    count = 0
    for kw in keywords:
        count += len(re.findall(re.escape(kw.lower()), lower))
    return count


def _detect_sentiment(text: str) -> tuple[str, float]:
    """텍스트의 감성(sentiment)과 강도(score)를 반환한다.

    Returns:
        (sentiment, score): sentiment는 "positive"/"negative"/"neutral",
                           score는 0~1 사이 강도
    """
    pos_count = _count_keyword_hits(text, _POSITIVE_KEYWORDS)
    neg_count = _count_keyword_hits(text, _NEGATIVE_KEYWORDS)
    total = pos_count + neg_count

    if total == 0:
        return "neutral", 0.3

    if pos_count > neg_count:
        ratio = pos_count / total
        return "positive", round(min(0.5 + ratio * 0.5, 1.0), 2)
    elif neg_count > pos_count:
        ratio = neg_count / total
        return "negative", round(min(0.5 + ratio * 0.5, 1.0), 2)
    else:
        return "neutral", 0.5


def _detect_angles(text: str) -> list[tuple[str, int]]:
    """텍스트에서 감지된 관점(앵글)과 점수를 반환한다.

    Returns:
        [(앵글_라벨, 히트수), ...] — 히트수 내림차순 정렬
    """
    results: list[tuple[str, int]] = []
    for angle_label, keywords in _ANGLE_PATTERNS.items():
        hits = _count_keyword_hits(text, keywords)
        if hits > 0:
            results.append((angle_label, hits))
    # 히트수 내림차순
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def _find_evidence(sentences: list[str], angle_keywords: list[str], sentiment_keywords: list[str], max_evidence: int = 3) -> list[str]:
    """앵글+감성 키워드가 포함된 근거 문장을 추출한다."""
    scored: list[tuple[str, int]] = []
    for sent in sentences:
        lower = sent.lower()
        score = 0
        for kw in angle_keywords:
            if kw.lower() in lower:
                score += 2
        for kw in sentiment_keywords:
            if kw.lower() in lower:
                score += 1
        if score > 0:
            scored.append((sent, score))
    # 점수 내림차순
    scored.sort(key=lambda x: x[1], reverse=True)
    return [s for s, _ in scored[:max_evidence]]


def _build_narrative_from_angle(
    topic: str,
    angle_label: str,
    angle_keywords: list[str],
    sentences: list[str],
    hit_count: int,
    total_sentences: int,
) -> Narrative:
    """하나의 앵글에 대한 Narrative 객체를 생성한다."""
    # 앵글 관련 문장만 필터링하여 감성 분석
    relevant_text = " ".join(
        s for s in sentences
        if any(kw.lower() in s.lower() for kw in angle_keywords)
    )
    if not relevant_text:
        relevant_text = " ".join(sentences)

    sentiment, _ = _detect_sentiment(relevant_text)

    # 강도: 관련 키워드 히트 비율 기반 (최소 0.2, 최대 1.0)
    strength = round(min(max(hit_count / max(total_sentences, 1), 0.2), 1.0), 2)

    # 감성에 따른 근거 검색 키워드
    if sentiment == "positive":
        sentiment_kws = _POSITIVE_KEYWORDS
    elif sentiment == "negative":
        sentiment_kws = _NEGATIVE_KEYWORDS
    else:
        sentiment_kws = _POSITIVE_KEYWORDS + _NEGATIVE_KEYWORDS

    evidence = _find_evidence(sentences, angle_keywords, sentiment_kws)

    return Narrative(
        topic=f"{topic} — {angle_label}",
        angle=angle_label,
        sentiment=sentiment,
        strength=strength,
        supporting_evidence=evidence,
    )


def _ensure_minimum_narratives(
    narratives: list[Narrative],
    topic: str,
    sentences: list[str],
    min_count: int = 3,
) -> list[Narrative]:
    """내러티브가 min_count 미만이면 보충 내러티브를 추가한다."""
    if len(narratives) >= min_count:
        return narratives

    # 이미 사용된 앵글
    used_angles = {n.angle for n in narratives}

    # 전체 텍스트 감성 기반 보충 내러티브
    full_text = " ".join(sentences)
    sentiment, strength = _detect_sentiment(full_text)

    # 기본 보충 앵글 목록
    filler_angles = ["일반 관점", "종합 평가", "주요 시사점", "핵심 논점", "향후 전망"]

    for filler_angle in filler_angles:
        if len(narratives) >= min_count:
            break
        if filler_angle in used_angles:
            continue

        # 보충 근거: 가장 긴 문장 상위 2개
        sorted_sents = sorted(sentences, key=len, reverse=True)
        evidence = sorted_sents[:2] if sorted_sents else []

        narratives.append(Narrative(
            topic=f"{topic} — {filler_angle}",
            angle=filler_angle,
            sentiment=sentiment,
            strength=round(max(strength * 0.6, 0.2), 2),
            supporting_evidence=evidence,
        ))

    return narratives


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def explore_narratives(
    topic: str,
    sources: list[str] | None = None,
) -> list[Narrative]:
    """주제 주변 내러티브를 탐색한다 (3개 이상 식별, 규칙 기반).

    Args:
        topic: 탐색할 주제 (예: "AI 자동화", "원격 근무")
        sources: 분석할 소스 텍스트 목록. None이면 topic만으로 기본 내러티브 생성.

    Returns:
        3개 이상의 Narrative 리스트 (strength 내림차순 정렬)
    """
    # 소스가 없으면 topic 자체를 분석 대상으로 사용
    if not sources:
        sources = [topic]

    # 전체 텍스트 결합
    combined_text = "\n".join(s for s in sources if s and s.strip())
    if not combined_text.strip():
        combined_text = topic

    sentences = _split_sentences(combined_text)
    if not sentences:
        sentences = [combined_text]

    total_sentences = len(sentences)

    # 앵글 감지
    angles = _detect_angles(combined_text)

    # 각 앵글에 대해 내러티브 생성
    narratives: list[Narrative] = []
    for angle_label, hit_count in angles:
        angle_keywords = _ANGLE_PATTERNS.get(angle_label, [])
        narrative = _build_narrative_from_angle(
            topic=topic,
            angle_label=angle_label,
            angle_keywords=angle_keywords,
            sentences=sentences,
            hit_count=hit_count,
            total_sentences=total_sentences,
        )
        narratives.append(narrative)

    # 최소 3개 보장
    narratives = _ensure_minimum_narratives(narratives, topic, sentences, min_count=3)

    # strength 내림차순 정렬
    narratives.sort(key=lambda n: n.strength, reverse=True)

    return narratives
