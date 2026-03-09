"""
딥리서치 에이전트.

여러 소스의 리서치 결과를 구조화하고,
관련성/신뢰도를 평가하여 종합 보고서를 생성한다.
"""

from dataclasses import dataclass, field
import uuid
import re
from collections import Counter


@dataclass
class ResearchQuery:
    """리서치 쿼리."""
    query_id: str
    topic: str
    sub_questions: list[str] = field(default_factory=list)
    depth: str = "medium"  # shallow / medium / deep


@dataclass
class ResearchFinding:
    """리서치 결과."""
    finding_id: str
    query_id: str
    source: str
    content: str
    relevance_score: float = 0.0  # 0.0 ~ 1.0
    credibility: str = "medium"  # high / medium / low


# 깊이별 하위 질문 수
_DEPTH_QUESTION_COUNT = {
    "shallow": 3,
    "medium": 4,
    "deep": 5,
}

# 신뢰도 가중치
_CREDIBILITY_WEIGHT = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}


def decompose_query(topic: str) -> ResearchQuery:
    """
    토픽을 하위 질문 3~5개로 분해.

    토픽의 주요 키워드를 기반으로 자동 분해한다.
    """
    query_id = uuid.uuid4().hex[:12]

    # 토픽 키워드 추출 (2글자 이상)
    words = topic.replace(",", " ").replace(".", " ").split()
    keywords = [w.strip() for w in words if len(w.strip()) >= 2]

    # 기본 질문 템플릿
    templates = [
        f"{topic}의 핵심 개념은 무엇인가?",
        f"{topic}의 최신 동향은 어떠한가?",
        f"{topic}의 장단점은 무엇인가?",
        f"{topic}의 실제 적용 사례는 무엇인가?",
        f"{topic}의 미래 전망은 어떠한가?",
    ]

    # 깊이에 따라 질문 수 조절 (기본 medium = 4)
    depth = "medium"
    count = _DEPTH_QUESTION_COUNT[depth]
    sub_questions = templates[:count]

    return ResearchQuery(
        query_id=query_id,
        topic=topic,
        sub_questions=sub_questions,
        depth=depth,
    )


def evaluate_finding(content: str, topic: str) -> ResearchFinding:
    """
    관련성/신뢰도 평가 (키워드 매칭 기반).

    - 관련성: 토픽 키워드가 content에 등장하는 비율
    - 신뢰도: 콘텐츠 길이 + 구조 기반 추정
    """
    finding_id = uuid.uuid4().hex[:12]

    # 토픽 키워드 추출
    topic_words = set(
        w.strip().lower()
        for w in topic.replace(",", " ").replace(".", " ").split()
        if len(w.strip()) >= 2
    )

    # 관련성 점수: 키워드 매칭 비율
    if topic_words:
        content_lower = content.lower()
        matched = sum(1 for w in topic_words if w in content_lower)
        relevance_score = min(matched / len(topic_words), 1.0)
    else:
        relevance_score = 0.5

    # 신뢰도 추정: 콘텐츠 길이 기반
    content_len = len(content.strip())
    if content_len >= 200:
        credibility = "high"
    elif content_len >= 50:
        credibility = "medium"
    else:
        credibility = "low"

    return ResearchFinding(
        finding_id=finding_id,
        query_id="",
        source="",
        content=content,
        relevance_score=round(relevance_score, 2),
        credibility=credibility,
    )


def synthesize_findings(findings: list[ResearchFinding]) -> str:
    """
    결과 종합.

    관련성 높은 순으로 정렬 후 합쳐서 종합 보고서 생성.
    """
    if not findings:
        return ""

    # 관련성 순 정렬
    sorted_findings = sorted(findings, key=lambda f: f.relevance_score, reverse=True)

    parts = []
    for i, f in enumerate(sorted_findings, 1):
        source_label = f.source if f.source else "Unknown"
        parts.append(
            f"{i}. [{source_label}] (관련성: {f.relevance_score}, "
            f"신뢰도: {f.credibility})\n   {f.content}"
        )

    return "\n\n".join(parts)


def rank_findings(findings: list[ResearchFinding]) -> list[ResearchFinding]:
    """
    관련성 + 신뢰도 복합 정렬.

    복합 점수 = relevance_score * credibility_weight.
    내림차순 정렬.
    """
    def composite_score(f: ResearchFinding) -> float:
        weight = _CREDIBILITY_WEIGHT.get(f.credibility, 0.5)
        return f.relevance_score * weight

    return sorted(findings, key=composite_score, reverse=True)
