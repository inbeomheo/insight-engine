"""
퀴즈/설문 응답 기반 맞춤형 후속 콘텐츠 생성 서비스

퀴즈 응답 결과를 분석하여 사용자별 지식 격차를 식별하고,
맞춤형 요약/추천/다음 학습 단계를 생성합니다.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class PersonalizedContent:
    """퀴즈 응답 기반 맞춤 후속 콘텐츠"""
    response_id: str
    summary: str                        # 응답 맞춤 요약
    recommendations: list[str]          # 추천 콘텐츠/액션
    knowledge_gaps: list[str]           # 부족한 지식 영역
    next_steps: list[str]              # 다음 학습 단계
    score: float = 0.0                  # 정답률 (0.0~1.0)
    total_questions: int = 0
    correct_count: int = 0


def generate_followup(
    quiz_responses: list[dict],
    video_id: str = "",
) -> PersonalizedContent:
    """퀴즈 응답별 맞춤 후속 콘텐츠를 생성합니다.

    Args:
        quiz_responses: 응답 목록
            [{"question": "...", "answer": "...", "correct": bool}, ...]
        video_id: 원본 영상 ID (선택)

    Returns:
        PersonalizedContent 데이터클래스
    """
    # 빈 입력 처리
    if not quiz_responses:
        return _empty_result(video_id)

    # 유효 응답만 필터링
    valid = _filter_valid_responses(quiz_responses)
    if not valid:
        return _empty_result(video_id)

    # 정답/오답 분리
    correct, incorrect = _split_responses(valid)
    total = len(valid)
    correct_count = len(correct)
    score = correct_count / total if total > 0 else 0.0

    # 응답 ID 생성
    response_id = _build_response_id(valid, video_id)

    # 지식 격차 추출 (오답 문제에서)
    knowledge_gaps = _extract_knowledge_gaps(incorrect)

    # 맞춤 요약 생성
    summary = _build_summary(score, total, correct_count, knowledge_gaps)

    # 추천 액션 생성
    recommendations = _build_recommendations(score, incorrect, correct)

    # 다음 학습 단계 생성
    next_steps = _build_next_steps(score, knowledge_gaps)

    return PersonalizedContent(
        response_id=response_id,
        summary=summary,
        recommendations=recommendations,
        knowledge_gaps=knowledge_gaps,
        next_steps=next_steps,
        score=round(score, 2),
        total_questions=total,
        correct_count=correct_count,
    )


def _empty_result(video_id: str = "") -> PersonalizedContent:
    """빈 결과를 반환합니다."""
    rid = hashlib.md5((video_id or "empty").encode()).hexdigest()[:8]
    return PersonalizedContent(
        response_id=rid,
        summary="분석할 응답이 없습니다.",
        recommendations=[],
        knowledge_gaps=[],
        next_steps=[],
    )


def _filter_valid_responses(responses: list[dict]) -> list[dict]:
    """유효한 응답만 필터링합니다.

    유효 조건: question과 correct 키가 존재하고 question이 비어있지 않아야 함.
    """
    valid = []
    for r in responses:
        if not isinstance(r, dict):
            continue
        if "question" not in r or "correct" not in r:
            continue
        if not r.get("question", "").strip():
            continue
        valid.append(r)
    return valid


def _split_responses(responses: list[dict]) -> tuple[list[dict], list[dict]]:
    """정답/오답 응답을 분리합니다."""
    correct = [r for r in responses if r.get("correct") is True]
    incorrect = [r for r in responses if r.get("correct") is not True]
    return correct, incorrect


def _build_response_id(responses: list[dict], video_id: str) -> str:
    """응답 기반 고유 ID를 생성합니다."""
    seed = video_id + "".join(r.get("question", "")[:20] for r in responses[:5])
    return hashlib.md5(seed.encode()).hexdigest()[:8]


def _extract_knowledge_gaps(incorrect: list[dict]) -> list[str]:
    """오답 문제에서 지식 격차를 추출합니다."""
    gaps = []
    for r in incorrect:
        question = r.get("question", "").strip()
        if not question:
            continue
        # 질문에서 핵심 주제를 추출
        topic = _extract_topic_from_question(question)
        if topic and topic not in gaps:
            gaps.append(topic)
    return gaps


def _extract_topic_from_question(question: str) -> str:
    """질문 문자열에서 핵심 주제를 추출합니다."""
    # 마크다운/인용부호 제거
    clean = re.sub(r'["""\'`]', '', question)
    clean = re.sub(r'다음 중|다음 설명|맞으면|틀리면|선택하세요|빈칸에 들어갈', '', clean)
    clean = re.sub(r'[OX을를은는이가의에?？]', '', clean)
    clean = clean.strip()

    # 15자 이상이면 앞 30자만
    if len(clean) > 30:
        clean = clean[:30] + "..."

    return clean if len(clean) >= 3 else ""


# ── 수준별 메시지 상수 ──

_LEVEL_THRESHOLDS = [
    (0.8, "excellent"),
    (0.5, "average"),
    (0.0, "needs_work"),
]

_SUMMARY_TEMPLATES = {
    "excellent": "우수한 이해도를 보여주셨습니다! {total}문제 중 {correct}개 정답({pct}%)으로 핵심 내용을 잘 파악하고 계십니다.",
    "average": "기본적인 이해는 갖추셨습니다. {total}문제 중 {correct}개 정답({pct}%)으로, 일부 영역에서 추가 학습이 필요합니다.",
    "needs_work": "핵심 내용에 대한 추가 학습이 필요합니다. {total}문제 중 {correct}개 정답({pct}%)으로, 아래 영역을 집중적으로 복습해 주세요.",
}


def _get_level(score: float) -> str:
    """점수에 따른 수준 레이블을 반환합니다."""
    for threshold, level in _LEVEL_THRESHOLDS:
        if score >= threshold:
            return level
    return "needs_work"


def _build_summary(
    score: float,
    total: int,
    correct_count: int,
    knowledge_gaps: list[str],
) -> str:
    """점수 기반 맞춤 요약을 생성합니다."""
    level = _get_level(score)
    pct = round(score * 100)
    summary = _SUMMARY_TEMPLATES[level].format(
        total=total, correct=correct_count, pct=pct,
    )

    if knowledge_gaps:
        gap_text = ", ".join(knowledge_gaps[:3])
        summary += f" 부족한 영역: {gap_text}."

    return summary


def _build_recommendations(
    score: float,
    incorrect: list[dict],
    correct: list[dict],
) -> list[str]:
    """점수와 오답 기반 추천 액션을 생성합니다."""
    recs = []
    level = _get_level(score)

    if level == "excellent":
        recs.append("심화 학습 콘텐츠로 넘어가세요.")
        recs.append("학습한 내용을 다른 사람에게 설명해 보세요.")
    elif level == "average":
        recs.append("오답 문제의 관련 영상 구간을 다시 시청하세요.")
        recs.append("핵심 개념을 노트에 정리해 보세요.")
    else:
        recs.append("영상을 처음부터 다시 시청하는 것을 권장합니다.")
        recs.append("각 챕터별로 핵심 내용을 메모하며 학습하세요.")

    # 오답 기반 개별 추천
    for r in incorrect[:3]:
        q = r.get("question", "")
        if len(q) > 10:
            short = q[:40] + "..." if len(q) > 40 else q
            recs.append(f'"{short}" 관련 내용을 복습하세요.')

    return recs


def _build_next_steps(score: float, knowledge_gaps: list[str]) -> list[str]:
    """다음 학습 단계를 생성합니다."""
    steps = []
    level = _get_level(score)

    if level == "excellent":
        steps.append("관련 주제의 심화 영상을 탐색하세요.")
        steps.append("학습 내용을 활용한 실습 프로젝트를 시작하세요.")
        steps.append("1주 후 복습 퀴즈를 풀어 장기 기억을 강화하세요.")
    elif level == "average":
        steps.append("오답 영역의 영상 구간을 다시 시청하세요.")
        for gap in knowledge_gaps[:2]:
            steps.append(f'"{gap}" 관련 내용을 집중 복습하세요.')
        steps.append("복습 후 퀴즈를 다시 풀어보세요.")
    else:
        steps.append("영상 전체를 다시 시청하세요.")
        steps.append("핵심 용어와 개념을 정리하세요.")
        for gap in knowledge_gaps[:2]:
            steps.append(f'"{gap}" 주제를 별도로 검색하여 학습하세요.')
        steps.append("기본 개념을 확인한 후 퀴즈를 다시 도전하세요.")

    return steps
