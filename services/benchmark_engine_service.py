"""
벤치마크 엔진 서비스 — 콘텐츠 품질 벤치마크 채점
"""

from dataclasses import dataclass, field
import re


@dataclass
class BenchmarkScore:
    """벤치마크 채점 결과"""
    content_id: str
    overall: float  # 0 ~ 100
    scores: dict[str, float] = field(default_factory=dict)
    grade: str = "C"
    recommendations: list[str] = field(default_factory=list)


# 기본 채점 루브릭 (항목별 가중치)
DEFAULT_RUBRIC = {
    "length": {"weight": 0.15, "description": "글 길이 적정성"},
    "structure": {"weight": 0.20, "description": "구조 (제목/소제목/단락)"},
    "readability": {"weight": 0.20, "description": "가독성"},
    "keyword_density": {"weight": 0.15, "description": "키워드 밀도"},
    "engagement": {"weight": 0.15, "description": "인게이지먼트 요소"},
    "formatting": {"weight": 0.15, "description": "서식 활용"},
}


def _score_length(text: str) -> float:
    """글 길이 채점 (0~100). 1000~3000자가 최적"""
    length = len(text)
    if length < 200:
        return 20.0
    elif length < 500:
        return 50.0
    elif length < 1000:
        return 70.0
    elif length <= 3000:
        return 100.0
    elif length <= 5000:
        return 85.0
    else:
        return 60.0


def _score_structure(text: str) -> float:
    """구조 채점 — 제목/소제목/단락 수 기반"""
    score = 0.0

    # 마크다운 헤딩 검출
    headings = re.findall(r'^#{1,3}\s+.+', text, re.MULTILINE)
    if len(headings) >= 3:
        score += 40
    elif len(headings) >= 1:
        score += 20

    # 단락 수 (빈 줄 기준)
    paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
    if len(paragraphs) >= 5:
        score += 30
    elif len(paragraphs) >= 3:
        score += 20
    elif len(paragraphs) >= 1:
        score += 10

    # 리스트 항목
    list_items = re.findall(r'^[\-\*]\s+', text, re.MULTILINE)
    if len(list_items) >= 3:
        score += 30
    elif len(list_items) >= 1:
        score += 15

    return min(score, 100.0)


def _score_readability(text: str) -> float:
    """가독성 채점 — 평균 문장 길이 기반"""
    # 문장 분리 (마침표/물음표/느낌표)
    sentences = re.split(r'[.!?。]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 30.0

    avg_len = sum(len(s) for s in sentences) / len(sentences)

    # 한국어 기준 15~50자가 적정
    if 15 <= avg_len <= 50:
        return 100.0
    elif 10 <= avg_len <= 80:
        return 70.0
    elif avg_len < 10:
        return 50.0  # 너무 짧은 문장
    else:
        return 40.0  # 너무 긴 문장


def _score_keyword_density(text: str) -> float:
    """키워드 밀도 채점 — 반복 단어 비율"""
    words = re.findall(r'[가-힣a-zA-Z]{2,}', text.lower())
    if len(words) < 10:
        return 40.0

    from collections import Counter
    counter = Counter(words)
    top_word_count = counter.most_common(1)[0][1] if counter else 0
    density = top_word_count / len(words)

    # 적정 밀도: 1~5%
    if 0.01 <= density <= 0.05:
        return 100.0
    elif density <= 0.08:
        return 70.0
    elif density > 0.15:
        return 30.0  # 키워드 스터핑
    else:
        return 50.0


def _score_engagement(text: str) -> float:
    """인게이지먼트 요소 채점"""
    score = 0.0

    # 질문형 문장
    questions = re.findall(r'\?', text)
    if len(questions) >= 2:
        score += 30
    elif len(questions) >= 1:
        score += 15

    # CTA (Call to Action) 패턴
    cta_patterns = ["확인", "시작", "클릭", "구독", "댓글", "공유",
                    "시도", "다운로드", "가입", "click", "subscribe", "try"]
    cta_count = sum(1 for p in cta_patterns if p in text.lower())
    if cta_count >= 2:
        score += 35
    elif cta_count >= 1:
        score += 20

    # 강조 표현 (볼드/이탤릭)
    bold = re.findall(r'\*\*[^*]+\*\*', text)
    if len(bold) >= 2:
        score += 35
    elif len(bold) >= 1:
        score += 20

    return min(score, 100.0)


def _score_formatting(text: str) -> float:
    """서식 활용 채점"""
    score = 0.0

    # 코드 블록
    if '```' in text:
        score += 25

    # 인용 블록
    blockquotes = re.findall(r'^>\s+', text, re.MULTILINE)
    if blockquotes:
        score += 20

    # 링크
    links = re.findall(r'\[.+?\]\(.+?\)', text)
    if links:
        score += 20

    # 이미지
    images = re.findall(r'!\[.*?\]\(.+?\)', text)
    if images:
        score += 20

    # 기본 마크다운 사용
    if '#' in text or '**' in text or '- ' in text:
        score += 15

    return min(score, 100.0)


# 채점 함수 매핑
_SCORING_FUNCTIONS = {
    "length": _score_length,
    "structure": _score_structure,
    "readability": _score_readability,
    "keyword_density": _score_keyword_density,
    "engagement": _score_engagement,
    "formatting": _score_formatting,
}


def _assign_grade(score: float) -> str:
    """점수를 등급으로 변환"""
    if score >= 90:
        return "A+"
    elif score >= 80:
        return "A"
    elif score >= 70:
        return "B+"
    elif score >= 60:
        return "B"
    elif score >= 50:
        return "C+"
    elif score >= 40:
        return "C"
    elif score >= 30:
        return "D"
    else:
        return "F"


def _generate_recommendations(scores: dict[str, float]) -> list[str]:
    """낮은 점수 항목에 대한 개선 추천"""
    rec_map = {
        "length": "글 길이를 1000~3000자 범위로 조정하세요",
        "structure": "소제목(##)과 리스트(-)를 추가하여 구조를 개선하세요",
        "readability": "문장 길이를 15~50자로 유지하여 가독성을 높이세요",
        "keyword_density": "핵심 키워드를 적정 빈도(1~5%)로 포함하세요",
        "engagement": "질문과 CTA(행동 유도)를 추가하세요",
        "formatting": "코드 블록, 인용, 링크 등 서식을 활용하세요",
    }
    recs = []
    # 점수 낮은 순으로 추천
    sorted_scores = sorted(scores.items(), key=lambda x: x[1])
    for name, score in sorted_scores:
        if score < 60 and name in rec_map:
            recs.append(f"[{name}: {score:.0f}점] {rec_map[name]}")
    return recs


def benchmark_against(
    content: str,
    rubric: dict | None = None,
    content_id: str = "",
) -> BenchmarkScore:
    """
    콘텐츠 벤치마크 채점.

    Args:
        content: 채점할 콘텐츠 텍스트
        rubric: 커스텀 루브릭 (None이면 기본 루브릭 사용)
        content_id: 콘텐츠 식별자

    Returns:
        BenchmarkScore: 채점 결과
    """
    if not content or not content.strip():
        return BenchmarkScore(
            content_id=content_id,
            overall=0.0,
            scores={},
            grade="F",
            recommendations=["콘텐츠가 비어 있습니다"],
        )

    active_rubric = rubric or DEFAULT_RUBRIC
    scores: dict[str, float] = {}
    weighted_sum = 0.0
    total_weight = 0.0

    for metric, config in active_rubric.items():
        weight = config.get("weight", 0.0)
        scoring_fn = _SCORING_FUNCTIONS.get(metric)

        if scoring_fn:
            score = scoring_fn(content)
        else:
            score = 50.0  # 알 수 없는 메트릭은 중간값

        scores[metric] = round(score, 1)
        weighted_sum += score * weight
        total_weight += weight

    overall = round(weighted_sum / total_weight, 1) if total_weight > 0 else 0.0
    grade = _assign_grade(overall)
    recommendations = _generate_recommendations(scores)

    return BenchmarkScore(
        content_id=content_id,
        overall=overall,
        scores=scores,
        grade=grade,
        recommendations=recommendations,
    )
