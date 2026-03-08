"""콘텐츠 성과 예측 서비스.

콘텐츠의 성과(조회수, 공유, 참여)를 규칙 기반으로 예측합니다.
AI API 호출 없이 순수 규칙/통계 기반으로 동작합니다.
"""

import re
import statistics


# 감정어 목록
_EMOTION_WORDS = [
    "놀라운", "중요한", "핵심", "반드시", "꼭",
    "필수", "강력", "최신", "효과적", "실전",
    "비밀", "특별", "완벽", "추천", "인기",
]

# CTA 표현 목록
_CTA_PHRASES = [
    "확인하세요", "시작하세요", "클릭", "지금 바로",
    "도전해보세요", "시도해보세요", "따라해보세요",
    "알아보세요", "신청하세요", "구독",
]

# 독자 호칭
_READER_ADDRESSES = ["여러분", "당신", "독자"]

# 카테고리별 개선 제안 매핑
_SUGGESTIONS = {
    "readability": "문장 길이를 15-30자로 조절하고, 단락을 3개 이상으로 나눠보세요.",
    "engagement": "질문문이나 CTA(행동 유도 표현)를 추가하고, 독자에게 직접 말하듯 작성해보세요.",
    "seo_signals": "제목을 10-60자로 맞추고, 핵심 키워드를 본문에 2회 이상 반복하세요. 헤딩(##)을 활용하세요.",
    "structure": "헤딩과 목록을 활용해 콘텐츠를 구조화하고, 단락 길이를 균일하게 맞춰보세요.",
    "shareability": "구체적인 숫자, 통계, 인용문을 추가하면 공유 가능성이 높아집니다.",
}

# 카테고리 한국어 이름
_CATEGORY_NAMES = {
    "readability": "가독성",
    "engagement": "참여도",
    "seo_signals": "SEO 신호",
    "structure": "구조",
    "shareability": "공유 가능성",
}


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리한다."""
    # 마침표, 물음표, 느낌표 기준으로 분리
    sentences = re.split(r'[.?!。！？]\s*', text)
    return [s.strip() for s in sentences if s.strip()]


def _split_paragraphs(text: str) -> list[str]:
    """텍스트를 단락 단위로 분리한다."""
    paragraphs = re.split(r'\n\s*\n', text)
    return [p.strip() for p in paragraphs if p.strip()]


def _count_headings(text: str) -> int:
    """마크다운 헤딩(#, ##, ### 등) 개수를 센다."""
    return len(re.findall(r'^#{1,6}\s+', text, re.MULTILINE))


def _count_list_items(text: str) -> int:
    """목록 항목(-, *, 1.) 개수를 센다."""
    return len(re.findall(r'^[\s]*[-*]\s+|^[\s]*\d+\.\s+', text, re.MULTILINE))


def _score_readability(content: str) -> float:
    """가독성 점수를 계산한다 (0-100)."""
    score = 0.0
    sentences = _split_sentences(content)
    paragraphs = _split_paragraphs(content)
    total_chars = len(content.strip())

    # 평균 문장 길이
    if sentences:
        avg_len = sum(len(s) for s in sentences) / len(sentences)
        if 15 <= avg_len <= 30:
            score += 30
        elif 10 <= avg_len <= 40:
            score += 20
        else:
            score += 10

    # 단락 수 3개 이상
    if len(paragraphs) >= 3:
        score += 20

    # 전체 글자 수
    if 300 <= total_chars <= 3000:
        score += 30
    else:
        score += 15

    # 짧은 문장 비율 (20자 이하)
    if sentences:
        short_ratio = sum(1 for s in sentences if len(s) <= 20) / len(sentences)
        if 0.3 <= short_ratio <= 0.5:
            score += 20

    return min(score, 100.0)


def _score_engagement(content: str) -> float:
    """참여도 점수를 계산한다 (0-100)."""
    score = 0.0

    # 질문문 개수
    question_count = content.count('?')
    if question_count >= 2:
        score += 25

    # 감정어 개수
    emotion_count = sum(1 for word in _EMOTION_WORDS if word in content)
    score += min(emotion_count * 5, 25)

    # CTA 표현
    if any(phrase in content for phrase in _CTA_PHRASES):
        score += 25

    # 독자 호칭
    if any(addr in content for addr in _READER_ADDRESSES):
        score += 25

    return min(score, 100.0)


def _score_seo_signals(content: str, title: str) -> float:
    """SEO 신호 점수를 계산한다 (0-100)."""
    score = 0.0

    # 제목 길이 10-60자
    if title and 10 <= len(title) <= 60:
        score += 30

    # 본문에 제목 키워드 반복 2회 이상
    if title:
        # 제목에서 의미 있는 단어 추출 (2자 이상)
        title_words = [w for w in re.findall(r'[가-힣a-zA-Z0-9]+', title) if len(w) >= 2]
        if title_words:
            keyword_found = any(content.count(word) >= 2 for word in title_words)
            if keyword_found:
                score += 25

    # 헤딩 2개 이상
    if _count_headings(content) >= 2:
        score += 25

    # 메타 설명 길이 (첫 160자 존재)
    if len(content.strip()) >= 160:
        score += 20

    return min(score, 100.0)


def _score_structure(content: str) -> float:
    """구조 점수를 계산한다 (0-100)."""
    score = 0.0
    paragraphs = _split_paragraphs(content)

    # 단락 3-10개
    if 3 <= len(paragraphs) <= 10:
        score += 25

    # 목록 포함
    if _count_list_items(content) > 0:
        score += 25

    # 헤딩 2개 이상
    if _count_headings(content) >= 2:
        score += 25

    # 단락 길이 균형 (표준편차 < 평균의 50%)
    if len(paragraphs) >= 2:
        lengths = [len(p) for p in paragraphs]
        avg = statistics.mean(lengths)
        if avg > 0:
            stdev = statistics.stdev(lengths)
            if stdev < avg * 0.5:
                score += 25

    return min(score, 100.0)


def _score_shareability(content: str) -> float:
    """공유 가능성 점수를 계산한다 (0-100)."""
    score = 0.0

    # 숫자/통계 포함
    if re.search(r'\d+', content):
        score += 25

    # 인용문 포함 (" " 또는 「」)
    if re.search(r'["\u201C\u201D]|[「」]', content):
        score += 25

    # 구체적 데이터 (%, 배, 원, 달러 등)
    if re.search(r'\d+\s*(%|배|원|달러|만|억|건|개|명|회)', content):
        score += 25

    # 리스트형 콘텐츠 (3개 이상 항목)
    if _count_list_items(content) >= 3:
        score += 25

    return min(score, 100.0)


def _map_grade(score: float) -> str:
    """점수를 등급으로 매핑한다."""
    if score >= 90:
        return "S"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B"
    elif score >= 60:
        return "C"
    elif score >= 50:
        return "D"
    return "F"


def _map_prediction(score: float) -> str:
    """점수를 예측 등급으로 매핑한다."""
    if score >= 75:
        return "high"
    elif score >= 50:
        return "medium"
    return "low"


_EMPTY_RESULT = {
    "overall_score": 0.0,
    "grade": "F",
    "category_scores": {
        "readability": 0.0, "engagement": 0.0,
        "seo_signals": 0.0, "structure": 0.0, "shareability": 0.0,
    },
    "prediction": "low",
    "strengths": [],
    "weaknesses": [f"{_CATEGORY_NAMES[c]}이(가) 부족합니다" for c in _CATEGORY_NAMES],
    "suggestions": list(_SUGGESTIONS.values()),
}


def _classify_strengths_weaknesses(category_scores: dict) -> tuple:
    """카테고리 점수에서 강점/약점/제안을 분류합니다.

    Returns:
        (strengths, weaknesses, suggestions)
    """
    strengths = []
    weaknesses = []
    suggestions = []
    for cat, score in category_scores.items():
        name = _CATEGORY_NAMES[cat]
        if score >= 70:
            strengths.append(f"{name}이(가) 우수합니다")
        if score < 50:
            weaknesses.append(f"{name}이(가) 부족합니다")
            suggestions.append(_SUGGESTIONS[cat])
    return strengths, weaknesses, suggestions


def predict_performance(content: str, title: str = '') -> dict:
    """콘텐츠 성과를 규칙 기반으로 예측한다.

    Args:
        content: 분석할 콘텐츠 텍스트
        title: 콘텐츠 제목 (선택)

    Returns:
        성과 예측 결과 딕셔너리
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    category_scores = {
        "readability": _score_readability(content),
        "engagement": _score_engagement(content),
        "seo_signals": _score_seo_signals(content, title),
        "structure": _score_structure(content),
        "shareability": _score_shareability(content),
    }

    overall_score = sum(category_scores.values()) / len(category_scores)
    strengths, weaknesses, suggestions = _classify_strengths_weaknesses(category_scores)

    return {
        "overall_score": round(overall_score, 1),
        "grade": _map_grade(overall_score),
        "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
        "prediction": _map_prediction(overall_score),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
    }
