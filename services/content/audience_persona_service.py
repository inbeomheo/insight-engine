"""Audience Persona Builder — 규칙 기반 타겟 독자 페르소나 추론 서비스.

콘텐츠 텍스트를 분석하여 AI API 호출 없이
전문성, 관심사, 독서 스타일, 연령대, 직업군 등을 추론한다.
"""

import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 상수 / 사전
# ---------------------------------------------------------------------------

# 전문용어 사전
JARGON_TERMS = {
    "api", "sdk", "ai", "ml", "roi", "kpi", "saas", "b2b", "mvp", "seo",
    "cta", "ux", "devops", "ci/cd", "rest", "graphql", "docker",
    "kubernetes", "microservices", "agile",
}

# 기초 설명 패턴 (beginner 감지)
BEGINNER_PATTERNS = [
    r"이란\s", r"이란$", r"란\s무엇", r"의\s뜻", r"기초", r"입문", r"처음",
]

# 타겟 명시 패턴 (confidence 보너스)
TARGET_EXPLICIT_PATTERNS = [
    r"초보자를?\s*위한", r"입문자", r"전문가용", r"전문가를?\s*위한",
    r"시니어", r"중급자",
]

# 카테고리별 키워드
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "기술/개발": ["코딩", "프로그래밍", "개발", "소프트웨어", "앱", "웹", "서버", "데이터"],
    "마케팅": ["마케팅", "광고", "브랜드", "캠페인", "타겟", "콘텐츠", "seo"],
    "비즈니스": ["매출", "수익", "투자", "성장", "전략", "경영", "스타트업"],
    "디자인": ["디자인", "ui", "ux", "레이아웃", "색상", "폰트", "그래픽"],
    "교육": ["학습", "교육", "강의", "수업", "커리큘럼", "훈련"],
}

# 카테고리 → 직업군
CATEGORY_TO_FIELD: dict[str, str] = {
    "기술/개발": "개발자/엔지니어",
    "마케팅": "마케터",
    "비즈니스": "경영/기획자",
    "디자인": "디자이너",
    "교육": "교육자/학생",
}

# 비격식체 / 줄임말 패턴 (young 감지)
INFORMAL_PATTERNS = [
    r"ㅋ{2,}", r"ㅎ{2,}", r"ㅠ{2,}", r"ㅜ{2,}",
    r"[ㄱ-ㅎ]{2,}",
    r"[😀-🙏🤣🤔🔥💯👍🎉❤️✨]",
    r"\b(ㄹㅇ|ㅇㅇ|ㄴㄴ|ㄱㄱ|ㅇㅋ|ㅈㄱ)\b",
    r"~{2,}", r"!{3,}", r"\?{3,}",
]

# 한자어 패턴 (senior 감지) — 격식적 한자어 표현
FORMAL_HANJA_TERMS = [
    "함에", "바이며", "것이며", "하였다", "되었다", "바이다",
    "함으로써", "에 의하여", "에 관하여", "에 대하여",
    "소이", "유의", "차이", "제반", "당해", "상기",
]

# 이미지 참조 패턴 (visual_learner 감지)
VISUAL_PATTERNS = [r"!\[", r"그림", r"사진", r"스크린샷", r"캡처", r"이미지", r"도표"]

# 스캐너 패턴 (scanner 감지)
SCANNER_PATTERNS = [r"^#{1,6}\s", r"^[-*]\s", r"^\d+\.\s", r"\*\*[^*]+\*\*"]


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _count_jargon(content: str) -> int:
    """전문용어 등장 횟수를 센다."""
    lower = content.lower()
    count = 0
    for term in JARGON_TERMS:
        # 단어 경계 매칭 (ci/cd 같은 특수 패턴도 처리)
        escaped = re.escape(term)
        count += len(re.findall(rf"(?<!\w){escaped}(?!\w)", lower))
    return count


def _jargon_density(content: str) -> float:
    """전문용어 밀도 (%)를 계산한다."""
    words = re.findall(r"[a-zA-Z가-힣]+(?:/[a-zA-Z가-힣]+)*", content)
    if not words:
        return 0.0
    jargon_count = _count_jargon(content)
    return (jargon_count / len(words)) * 100


def _has_beginner_patterns(content: str) -> bool:
    """기초/입문 설명 패턴이 있는지 확인한다."""
    for pat in BEGINNER_PATTERNS:
        if re.search(pat, content):
            return True
    return False


def _detect_expertise_level(content: str) -> tuple[str, list[str]]:
    """전문성 수준과 근거를 반환한다."""
    indicators: list[str] = []
    jargon_count = _count_jargon(content)
    density = _jargon_density(content)
    has_beginner = _has_beginner_patterns(content)

    if has_beginner:
        indicators.append("기초/입문 설명 패턴 감지 → beginner 수준")

    if jargon_count > 0:
        indicators.append(f"전문용어 {jargon_count}개 감지 (밀도 {density:.1f}%)")

    # 전문용어 밀도 5%+ & 입문 패턴 없으면 expert
    if density >= 5.0 and not has_beginner:
        indicators.append("높은 전문용어 밀도 + 설명 없이 사용 → expert 수준")
        return "expert", indicators

    if has_beginner:
        return "beginner", indicators

    return "intermediate", indicators


def _extract_interests(content: str) -> list[str]:
    """2회 이상 등장하는 토픽을 추출하고 상위 5개를 반환한다."""
    # 한국어 명사 (2-8자) — 조사 분리 후 어근 추출
    raw_korean = re.findall(r"[가-힣]{2,8}", content)
    # 흔한 한국어 조사/어미 접미사를 제거하여 어근을 추출
    _suffixes = re.compile(
        r"(은|는|이|가|을|를|의|에|와|과|로|으로|도|만|까지|부터|에서|처럼|보다)$"
    )
    korean_words: list[str] = []
    for w in raw_korean:
        stem = _suffixes.sub("", w)
        # 어근이 2자 이상이면 어근 사용, 아니면 원본 사용
        korean_words.append(stem if len(stem) >= 2 else w)
    # 영어 단어 (3자+)
    english_words = [w.lower() for w in re.findall(r"[a-zA-Z]{3,}", content)]

    counter: Counter[str] = Counter()
    counter.update(korean_words)
    counter.update(english_words)

    # 불용어 제거 (흔한 한국어 조사/접미사 단어)
    stopwords = {
        "그리고", "하지만", "그래서", "이것은", "이러한", "때문에",
        "통해서", "대해서", "위해서", "있습니다", "합니다", "됩니다",
        "하는", "있는", "되는", "것이", "수가", "것은", "에서",
        "으로", "에게", "부터", "까지", "the", "and", "for", "that",
        "this", "with", "from", "are", "was", "were", "been", "have",
        "has", "not", "but", "can",
    }

    # 2회 이상 등장, 불용어 제외
    topics = [
        word for word, cnt in counter.most_common(50)
        if cnt >= 2 and word not in stopwords
    ]

    return topics[:5]


def _detect_reading_style(content: str) -> tuple[str, list[str]]:
    """독서 스타일과 근거를 반환한다."""
    indicators: list[str] = []
    lines = content.split("\n")

    # 스캐너 점수: 목록/헤딩/굵은 글씨
    scanner_score = 0
    for line in lines:
        for pat in SCANNER_PATTERNS:
            if re.search(pat, line):
                scanner_score += 1
                break

    # 비주얼 점수
    visual_score = 0
    for pat in VISUAL_PATTERNS:
        visual_score += len(re.findall(pat, content))

    # 딥리더 점수: 100자 이상 문단 수
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    long_paragraphs = sum(1 for p in paragraphs if len(p) >= 100)

    if visual_score >= 3:
        indicators.append(f"이미지/시각 참조 {visual_score}회 → visual_learner")
        return "visual_learner", indicators

    if long_paragraphs >= 3 and scanner_score < long_paragraphs:
        indicators.append(f"긴 서술 문단 {long_paragraphs}개 → deep_reader")
        return "deep_reader", indicators

    if scanner_score >= 3:
        indicators.append(f"목록/헤딩/강조 {scanner_score}회 → scanner")
        return "scanner", indicators

    # 기본값
    indicators.append("특별한 형식 패턴 없음 → scanner (기본값)")
    return "scanner", indicators


def _detect_age_group(content: str) -> tuple[str, list[str]]:
    """연령대와 근거를 반환한다."""
    indicators: list[str] = []

    # 비격식체 점수
    informal_score = 0
    for pat in INFORMAL_PATTERNS:
        informal_score += len(re.findall(pat, content))

    # 격식 한자어 점수
    formal_score = 0
    lower = content.lower()
    for term in FORMAL_HANJA_TERMS:
        formal_score += lower.count(term)

    jargon_count = _count_jargon(content)

    if informal_score >= 3:
        indicators.append(f"비격식체/이모티콘/줄임말 {informal_score}회 → young 연령대")
        return "young", indicators

    if formal_score >= 3:
        indicators.append(f"격식적 한자어 표현 {formal_score}회 → senior 연령대")
        return "senior", indicators

    if jargon_count >= 3:
        indicators.append("전문용어 + 격식체 → middle 연령대")
        return "middle", indicators

    indicators.append("기본 연령대 → middle")
    return "middle", indicators


def _detect_professional_field(content: str) -> tuple[str, list[str]]:
    """직업군과 근거를 반환한다."""
    indicators: list[str] = []
    lower = content.lower()

    category_scores: dict[str, int] = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            score += len(re.findall(re.escape(kw), lower))
        if score > 0:
            category_scores[category] = score

    if not category_scores:
        indicators.append("특정 분야 키워드 미감지 → 일반 직장인")
        return "일반 직장인", indicators

    top_category = max(category_scores, key=lambda k: category_scores[k])
    field = CATEGORY_TO_FIELD.get(top_category, "일반 직장인")
    indicators.append(f"{top_category} 키워드 우세 ({category_scores[top_category]}회) → {field}")
    return field, indicators


def _calculate_confidence(
    content: str, expertise: str, field: str, reading_style: str
) -> float:
    """페르소나 추론 신뢰도 (0-100)를 계산한다."""
    score = 0.0

    # 콘텐츠 길이 500자+ → +20
    if len(content) >= 500:
        score += 20

    # 전문 키워드 5개+ → +20
    jargon_count = _count_jargon(content)
    if jargon_count >= 5:
        score += 20

    # 명확한 카테고리 (일반 직장인이 아니면) → +20
    if field != "일반 직장인":
        score += 20

    # 일관된 문체 (reading_style이 기본값 아닌 명시적 감지) → +20
    # reading_style이 명시적으로 감지되었으면 일관된 문체로 판단
    if reading_style in ("deep_reader", "visual_learner"):
        score += 20
    elif reading_style == "scanner":
        # 스캐너도 명시적 패턴이 있으면 +20
        lines = content.split("\n")
        scanner_count = 0
        for line in lines:
            for pat in SCANNER_PATTERNS:
                if re.search(pat, line):
                    scanner_count += 1
                    break
        if scanner_count >= 3:
            score += 20

    # 타겟 명시 패턴 → +20
    for pat in TARGET_EXPLICIT_PATTERNS:
        if re.search(pat, content):
            score += 20
            break

    return min(score, 100.0)


def _calculate_content_alignment(
    content: str, expertise: str, reading_style: str
) -> dict[str, float]:
    """콘텐츠 정합성 점수를 계산한다."""
    density = _jargon_density(content)
    jargon_count = _count_jargon(content)

    # complexity_match: expertise_level과 어휘 복잡도 매칭
    if expertise == "expert":
        complexity_match = min(density * 10, 100.0)
    elif expertise == "beginner":
        # 초보자 콘텐츠는 낮은 밀도일수록 좋음
        complexity_match = max(100.0 - density * 15, 0.0)
    else:
        complexity_match = min(50.0 + density * 5, 100.0)

    # vocabulary_match: 전문용어 사용이 타겟에 적합한지
    if expertise == "expert" and jargon_count >= 5:
        vocabulary_match = min(60.0 + jargon_count * 4, 100.0)
    elif expertise == "beginner" and jargon_count <= 3:
        vocabulary_match = 80.0
    elif expertise == "intermediate":
        vocabulary_match = min(50.0 + jargon_count * 5, 100.0)
    else:
        vocabulary_match = 50.0

    # format_match: 콘텐츠 형식이 reading_style에 맞는지
    lines = content.split("\n")
    scanner_count = sum(
        1 for line in lines
        if any(re.search(pat, line) for pat in SCANNER_PATTERNS)
    )
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    long_paragraphs = sum(1 for p in paragraphs if len(p) >= 100)
    visual_count = sum(len(re.findall(pat, content)) for pat in VISUAL_PATTERNS)

    if reading_style == "scanner":
        format_match = min(40.0 + scanner_count * 10, 100.0)
    elif reading_style == "deep_reader":
        format_match = min(40.0 + long_paragraphs * 15, 100.0)
    elif reading_style == "visual_learner":
        format_match = min(40.0 + visual_count * 15, 100.0)
    else:
        format_match = 50.0

    return {
        "complexity_match": round(complexity_match, 1),
        "vocabulary_match": round(vocabulary_match, 1),
        "format_match": round(format_match, 1),
    }


def _generate_suggestions(
    expertise: str, reading_style: str, age_group: str, field: str
) -> list[str]:
    """페르소나에 맞는 콘텐츠 개선 제안을 생성한다."""
    suggestions: list[str] = []

    if expertise == "beginner":
        suggestions.append("전문용어 사용 시 괄호 안에 설명을 추가하세요")
        suggestions.append("단계별 가이드 형식으로 구성하면 이해도가 높아집니다")
    elif expertise == "expert":
        suggestions.append("기초 설명을 줄이고 심화 내용에 집중하세요")
        suggestions.append("업계 사례와 벤치마크 데이터를 포함하면 신뢰도가 높아집니다")
    else:
        suggestions.append("핵심 개념은 간단히 설명하되 실전 예시를 추가하세요")

    if reading_style == "scanner":
        suggestions.append("핵심 포인트를 굵은 글씨나 목록으로 강조하세요")
    elif reading_style == "deep_reader":
        suggestions.append("서론-본론-결론 구조를 명확히 하세요")
    elif reading_style == "visual_learner":
        suggestions.append("다이어그램이나 스크린샷을 추가하면 효과적입니다")

    if age_group == "young":
        suggestions.append("짧고 임팩트 있는 문장을 사용하세요")

    return suggestions


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------

_EMPTY_RESULT = {
    "persona": {
        "expertise_level": "beginner",
        "interests": [],
        "reading_style": "scanner",
        "age_group": "middle",
        "professional_field": "일반 직장인",
    },
    "confidence": 0.0,
    "content_alignment": {
        "complexity_match": 0.0,
        "vocabulary_match": 0.0,
        "format_match": 0.0,
    },
    "indicators": ["콘텐츠가 비어 있어 기본값 사용"],
    "suggestions": ["분석할 콘텐츠를 제공해주세요"],
}


def _detect_all_traits(content: str) -> tuple:
    """모든 페르소나 특성을 감지합니다.

    Returns:
        (expertise, interests, reading_style, age_group, field, all_indicators)
    """
    all_indicators: list[str] = []

    expertise, exp_ind = _detect_expertise_level(content)
    all_indicators.extend(exp_ind)

    interests = _extract_interests(content)

    reading_style, rs_ind = _detect_reading_style(content)
    all_indicators.extend(rs_ind)

    age_group, ag_ind = _detect_age_group(content)
    all_indicators.extend(ag_ind)

    field, pf_ind = _detect_professional_field(content)
    all_indicators.extend(pf_ind)

    return expertise, interests, reading_style, age_group, field, all_indicators


def build_persona(content: str) -> dict:
    """콘텐츠를 분석하여 타겟 독자 페르소나를 규칙 기반으로 추론한다.

    Args:
        content: 분석할 콘텐츠 텍스트.

    Returns:
        페르소나 정보, 신뢰도, 콘텐츠 정합성, 추론 근거, 제안 사항을 담은 dict.
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        expertise, interests, reading_style, age_group, field, indicators = _detect_all_traits(content)

        return {
            "persona": {
                "expertise_level": expertise,
                "interests": interests,
                "reading_style": reading_style,
                "age_group": age_group,
                "professional_field": field,
            },
            "confidence": _calculate_confidence(content, expertise, field, reading_style),
            "content_alignment": _calculate_content_alignment(content, expertise, reading_style),
            "indicators": indicators,
            "suggestions": _generate_suggestions(expertise, reading_style, age_group, field),
        }
    except Exception as e:
        logger.error(f"페르소나 추론 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
