"""팬 앵글 서비스 — 팬 해석 각도 제안"""
from dataclasses import dataclass, field


# 각도 타입별 키워드 매핑
_ANGLE_KEYWORDS = {
    "behind_the_scenes": {
        "keywords": ["비하인드", "촬영", "제작", "만들기", "과정", "메이킹", "현장", "뒷이야기", "준비"],
        "title": "비하인드 스토리",
        "description": "제작 과정과 뒷이야기를 깊이 파헤칩니다.",
    },
    "deep_dive": {
        "keywords": ["분석", "심층", "자세히", "깊이", "탐구", "연구", "원리", "이유", "원인", "배경"],
        "title": "심층 분석",
        "description": "핵심 주제를 깊이 있게 분석합니다.",
    },
    "comparison": {
        "keywords": ["vs", "비교", "차이", "대결", "비교하면", "반면", "대비", "상대"],
        "title": "비교 분석",
        "description": "유사 주제나 대상을 비교하여 차이점을 분석합니다.",
    },
    "reaction": {
        "keywords": ["반응", "리액션", "댓글", "의견", "평가", "후기", "리뷰", "감상"],
        "title": "반응 분석",
        "description": "시청자/팬 반응을 수집하고 분석합니다.",
    },
    "timeline": {
        "keywords": ["역사", "타임라인", "연대기", "변천", "발전", "과거", "미래", "전망", "흐름"],
        "title": "타임라인 정리",
        "description": "시간 순서대로 주요 사건과 변화를 정리합니다.",
    },
    "theory": {
        "keywords": ["이론", "추측", "가설", "예측", "떡밥", "복선", "해석", "숨겨진", "의미"],
        "title": "팬 이론",
        "description": "숨겨진 의미와 팬 해석을 탐구합니다.",
    },
}


@dataclass
class FanAngle:
    """팬 해석 각도"""
    angle_type: str = ""
    title: str = ""
    description: str = ""
    relevance_score: int = 0
    source_keywords: list = field(default_factory=list)


def _count_keyword_matches(text: str, keywords: list) -> tuple:
    """텍스트에서 키워드 매칭 수와 매칭된 키워드 반환"""
    text_lower = text.lower()
    matched = []
    for kw in keywords:
        if kw.lower() in text_lower:
            matched.append(kw)
    return len(matched), matched


def _calculate_relevance_score(match_count: int, total_keywords: int) -> int:
    """키워드 매칭 수 기반 관련도 점수 (0~100)"""
    if total_keywords == 0 or match_count == 0:
        return 0
    # 매칭 비율 기반, 최소 매칭 1개 = 20점, 비율에 따라 증가
    base_score = min(match_count / total_keywords, 1.0) * 80
    # 매칭 수 보너스 (절대적 매칭 수도 반영)
    count_bonus = min(match_count * 5, 20)
    score = int(base_score + count_bonus)
    return max(0, min(100, score))


def suggest_fan_angles(content: str, comments: list = None) -> list:
    """팬 해석 각도 제안

    Args:
        content: 콘텐츠 본문 텍스트
        comments: 댓글 리스트 (선택)

    Returns:
        FanAngle 리스트 (매칭된 각도만)
    """
    if not content or not content.strip():
        return []

    # 콘텐츠 + 댓글 합산 텍스트
    combined_text = content
    if comments:
        combined_text += ' ' + ' '.join(c for c in comments if c)

    angles = []

    for angle_type, config in _ANGLE_KEYWORDS.items():
        keywords = config["keywords"]
        match_count, matched_keywords = _count_keyword_matches(combined_text, keywords)

        if match_count > 0:
            score = _calculate_relevance_score(match_count, len(keywords))
            angles.append(FanAngle(
                angle_type=angle_type,
                title=config["title"],
                description=config["description"],
                relevance_score=score,
                source_keywords=matched_keywords,
            ))

    return angles


def rank_angles(angles: list) -> list:
    """관련도 순 정렬 (높은 점수 우선)

    Args:
        angles: FanAngle 리스트

    Returns:
        정렬된 FanAngle 리스트 (내림차순)
    """
    if not angles:
        return []
    return sorted(angles, key=lambda a: a.relevance_score, reverse=True)
