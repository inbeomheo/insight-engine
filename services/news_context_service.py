"""시사 맥락 주입 서비스 — 콘텐츠에 관련 시사 맥락 문장을 삽입"""
import re
from dataclasses import dataclass


@dataclass
class ContextualContent:
    """맥락이 주입된 콘텐츠"""
    original_content: str
    injected_content: str
    context_points: list  # list[str]
    relevance_score: float  # 0.0 ~ 1.0


# 토픽별 맥락 사전 (외부 API 없이 키워드 매칭)
_CONTEXT_DATABASE: dict[str, list[str]] = {
    "ai": [
        "AI 기술의 급속한 발전으로 산업 전반에 걸쳐 변화가 일어나고 있습니다.",
        "생성형 AI의 등장으로 콘텐츠 제작 방식이 근본적으로 변화하고 있습니다.",
        "AI 규제에 대한 글로벌 논의가 활발히 진행 중입니다.",
    ],
    "경제": [
        "글로벌 경제 불확실성이 지속되고 있어 기업들의 전략 수정이 필요합니다.",
        "디지털 전환이 가속화되면서 새로운 비즈니스 모델이 등장하고 있습니다.",
        "ESG 경영이 기업 가치 평가의 핵심 지표로 부상하고 있습니다.",
    ],
    "기술": [
        "클라우드 네이티브 기술의 채택이 빠르게 확산되고 있습니다.",
        "사이버 보안 위협이 증가하면서 보안 투자의 중요성이 커지고 있습니다.",
        "오픈소스 생태계가 기술 혁신의 주요 동력으로 자리잡았습니다.",
    ],
    "교육": [
        "평생교육의 중요성이 강조되면서 온라인 학습 플랫폼이 성장하고 있습니다.",
        "코딩 교육이 필수 교과로 확대되는 추세입니다.",
        "개인 맞춤형 학습의 수요가 급증하고 있습니다.",
    ],
    "환경": [
        "탄소 중립 목표 달성을 위한 기업과 정부의 노력이 강화되고 있습니다.",
        "친환경 기술에 대한 투자가 전 세계적으로 확대되고 있습니다.",
        "순환경제 모델이 지속 가능한 성장의 대안으로 주목받고 있습니다.",
    ],
    "건강": [
        "디지털 헬스케어 시장이 급성장하고 있습니다.",
        "정신건강에 대한 사회적 인식이 높아지고 있습니다.",
        "원격 의료 서비스의 제도화가 진행 중입니다.",
    ],
    "마케팅": [
        "퍼스트파티 데이터 전략이 마케팅의 핵심으로 부상하고 있습니다.",
        "숏폼 콘텐츠가 마케팅 채널의 주류가 되고 있습니다.",
        "개인화 마케팅의 정교함이 갈수록 높아지고 있습니다.",
    ],
}

# 키워드 → 토픽 매핑
_KEYWORD_TO_TOPIC: dict[str, str] = {
    # AI 관련
    "인공지능": "ai", "ai": "ai", "머신러닝": "ai", "딥러닝": "ai",
    "machine learning": "ai", "deep learning": "ai", "gpt": "ai", "llm": "ai",
    # 경제 관련
    "경제": "경제", "투자": "경제", "주식": "경제", "금융": "경제",
    "비즈니스": "경제", "스타트업": "경제", "창업": "경제",
    # 기술 관련
    "기술": "기술", "개발": "기술", "프로그래밍": "기술", "소프트웨어": "기술",
    "클라우드": "기술", "보안": "기술", "데이터": "기술",
    # 교육 관련
    "교육": "교육", "학습": "교육", "강의": "교육", "공부": "교육",
    # 환경 관련
    "환경": "환경", "탄소": "환경", "친환경": "환경", "기후": "환경",
    # 건강 관련
    "건강": "건강", "의료": "건강", "헬스": "건강", "운동": "건강",
    # 마케팅 관련
    "마케팅": "마케팅", "광고": "마케팅", "브랜딩": "마케팅", "sns": "마케팅",
}


def _find_relevant_topics(content: str, topic: str) -> list[str]:
    """콘텐츠와 토픽에서 관련 맥락 문장을 찾는다."""
    topic_lower = topic.lower().strip()

    # 직접 매핑
    matched_topic = _KEYWORD_TO_TOPIC.get(topic_lower)

    # 키워드 부분 매칭
    if not matched_topic:
        for keyword, mapped_topic in _KEYWORD_TO_TOPIC.items():
            if keyword in topic_lower or topic_lower in keyword:
                matched_topic = mapped_topic
                break

    # 콘텐츠 본문에서도 키워드 탐색
    content_lower = content.lower()
    secondary_topics = set()
    for keyword, mapped_topic in _KEYWORD_TO_TOPIC.items():
        if keyword in content_lower and mapped_topic != matched_topic:
            secondary_topics.add(mapped_topic)

    # 맥락 문장 수집
    context_points = []
    if matched_topic and matched_topic in _CONTEXT_DATABASE:
        context_points.extend(_CONTEXT_DATABASE[matched_topic])

    # 부가 토픽에서 1개씩 추가
    for sec_topic in list(secondary_topics)[:2]:
        if sec_topic in _CONTEXT_DATABASE:
            context_points.append(_CONTEXT_DATABASE[sec_topic][0])

    return context_points


def _calculate_relevance(content: str, topic: str, context_points: list[str]) -> float:
    """관련성 점수를 계산한다 (0.0 ~ 1.0)."""
    if not context_points:
        return 0.0

    topic_lower = topic.lower()
    content_lower = content.lower()

    score = 0.0

    # 토픽 키워드가 콘텐츠에 존재하면 기본 점수
    if topic_lower in content_lower:
        score += 0.4

    # 관련 키워드 빈도
    topic_key = _KEYWORD_TO_TOPIC.get(topic_lower)
    related_keywords = [k for k, v in _KEYWORD_TO_TOPIC.items() if v == topic_key]
    match_count = sum(1 for kw in related_keywords if kw in content_lower)
    score += min(0.3, match_count * 0.1)

    # 맥락 포인트 수 반영
    score += min(0.3, len(context_points) * 0.1)

    return round(min(1.0, score), 2)


def _inject_context_sentences(content: str, context_points: list[str]) -> str:
    """콘텐츠에 맥락 문장을 자연스럽게 삽입한다."""
    if not context_points:
        return content

    paragraphs = content.split("\n\n")
    if not paragraphs:
        return content

    result_paragraphs = []

    # 첫 문단 뒤에 맥락 블록 삽입
    result_paragraphs.append(paragraphs[0])

    if context_points:
        context_block = "\n\n📌 **관련 시사 맥락:**\n"
        for point in context_points:
            context_block += f"- {point}\n"
        result_paragraphs.append(context_block.strip())

    # 나머지 문단 추가
    result_paragraphs.extend(paragraphs[1:])

    return "\n\n".join(result_paragraphs)


def inject_news_context(content: str, topic: str) -> ContextualContent:
    """콘텐츠에 시사 맥락을 주입한다.

    Args:
        content: 원본 콘텐츠 텍스트
        topic: 주제 키워드 (예: "AI", "경제", "기술")

    Returns:
        ContextualContent 구조
    """
    if not content or not content.strip():
        return ContextualContent(
            original_content=content or "",
            injected_content=content or "",
            context_points=[],
            relevance_score=0.0,
        )

    if not topic or not topic.strip():
        return ContextualContent(
            original_content=content,
            injected_content=content,
            context_points=[],
            relevance_score=0.0,
        )

    context_points = _find_relevant_topics(content, topic)
    relevance = _calculate_relevance(content, topic, context_points)
    injected = _inject_context_sentences(content, context_points)

    return ContextualContent(
        original_content=content,
        injected_content=injected,
        context_points=context_points,
        relevance_score=relevance,
    )
