"""
커뮤니티 배심원 서비스 — 다수 리뷰어의 평가를 집계하여 최종 판정
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


VALID_VERDICTS = {"approve", "reject", "revise"}


@dataclass
class JuryVote:
    """배심원 투표"""
    vote_id: str
    juror_id: str
    content_id: str
    verdict: str  # approve / reject / revise
    score: float  # 0.0 ~ 1.0
    comment: str


@dataclass
class JuryVerdict:
    """최종 판정 결과"""
    content_id: str
    total_votes: int
    approve_count: int
    reject_count: int
    revise_count: int
    avg_score: float
    final_verdict: str
    consensus_level: float


def _new_id(prefix: str = "vote") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def cast_vote(
    juror_id: str,
    content_id: str,
    verdict: str,
    score: float,
    comment: str = "",
) -> JuryVote:
    """투표

    Args:
        juror_id: 배심원 ID
        content_id: 콘텐츠 ID
        verdict: 판정 (approve/reject/revise)
        score: 점수 (0.0~1.0)
        comment: 코멘트

    Returns:
        JuryVote: 생성된 투표
    """
    if verdict not in VALID_VERDICTS:
        raise ValueError(f"유효하지 않은 판정: {verdict}. 허용: {VALID_VERDICTS}")
    if not (0.0 <= score <= 1.0):
        raise ValueError(f"점수는 0.0~1.0 범위여야 합니다: {score}")

    return JuryVote(
        vote_id=_new_id(),
        juror_id=juror_id,
        content_id=content_id,
        verdict=verdict,
        score=score,
        comment=comment,
    )


def calculate_consensus(votes: list) -> float:
    """합의 수준 계산 (0~1, 최다 득표 비율)

    Args:
        votes: 투표 목록

    Returns:
        float: 합의 수준
    """
    if not votes:
        return 0.0

    counts = {"approve": 0, "reject": 0, "revise": 0}
    for v in votes:
        if v.verdict in counts:
            counts[v.verdict] += 1

    total = len(votes)
    max_count = max(counts.values())

    return round(max_count / total, 3) if total > 0 else 0.0


def tally_votes(votes: list) -> JuryVerdict:
    """투표 집계 — 과반수 결정, 동률 시 revise

    Args:
        votes: 투표 목록

    Returns:
        JuryVerdict: 집계 결과
    """
    if not votes:
        return JuryVerdict(
            content_id="",
            total_votes=0,
            approve_count=0,
            reject_count=0,
            revise_count=0,
            avg_score=0.0,
            final_verdict="revise",
            consensus_level=0.0,
        )

    content_id = votes[0].content_id
    counts = {"approve": 0, "reject": 0, "revise": 0}
    total_score = 0.0

    for v in votes:
        if v.verdict in counts:
            counts[v.verdict] += 1
        total_score += v.score

    total = len(votes)
    avg_score = round(total_score / total, 3) if total > 0 else 0.0

    # 최다 득표 판정
    max_count = max(counts.values())
    winners = [k for k, v in counts.items() if v == max_count]

    if len(winners) == 1:
        final_verdict = winners[0]
    else:
        # 동률 시 revise (안전한 선택)
        final_verdict = "revise"

    consensus = calculate_consensus(votes)

    return JuryVerdict(
        content_id=content_id,
        total_votes=total,
        approve_count=counts["approve"],
        reject_count=counts["reject"],
        revise_count=counts["revise"],
        avg_score=avg_score,
        final_verdict=final_verdict,
        consensus_level=consensus,
    )


def get_minority_opinions(votes: list, final_verdict: str) -> list:
    """소수 의견 추출 — 최종 판정과 다른 투표

    Args:
        votes: 투표 목록
        final_verdict: 최종 판정

    Returns:
        list[JuryVote]: 소수 의견 투표 목록
    """
    return [v for v in votes if v.verdict != final_verdict]
