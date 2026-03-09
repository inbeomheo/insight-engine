"""
AI 멘토 마켓 서비스 — 멘토-멘티 매칭
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class Mentor:
    """멘토"""
    mentor_id: str
    name: str
    expertise: list[str]
    availability: bool
    rating: float
    sessions_completed: int


@dataclass
class MentorMatch:
    """멘토 매칭 결과"""
    mentor_id: str
    mentee_id: str
    compatibility_score: float
    matched_skills: list[str]


def match_mentors(mentee_interests: list[str], mentors: list[Mentor], mentee_id: str = '') -> list[MentorMatch]:
    """전문성 + 가용성 기반 멘토 매칭"""
    if not mentee_id:
        mentee_id = str(uuid.uuid4())[:8]

    matches = []
    mentee_lower = {i.lower() for i in mentee_interests}

    for mentor in mentors:
        if not mentor.availability:
            continue

        mentor_lower = {e.lower() for e in mentor.expertise}
        matched = mentee_lower & mentor_lower
        if not matched:
            continue

        # 호환성 점수: 겹치는 비율 * 평점 가중치
        overlap_ratio = len(matched) / max(len(mentee_lower), 1)
        rating_weight = mentor.rating / 5.0
        score = round(overlap_ratio * 0.7 + rating_weight * 0.3, 3)

        matches.append(MentorMatch(
            mentor_id=mentor.mentor_id,
            mentee_id=mentee_id,
            compatibility_score=score,
            matched_skills=sorted(matched)
        ))

    # 점수 내림차순 정렬
    matches.sort(key=lambda m: m.compatibility_score, reverse=True)
    return matches


def rate_mentor(mentor: Mentor, rating: float) -> Mentor:
    """평점 업데이트 (가중 평균)"""
    total = mentor.rating * mentor.sessions_completed + rating
    new_sessions = mentor.sessions_completed + 1
    new_rating = round(total / new_sessions, 2)

    return Mentor(
        mentor_id=mentor.mentor_id,
        name=mentor.name,
        expertise=mentor.expertise,
        availability=mentor.availability,
        rating=new_rating,
        sessions_completed=new_sessions
    )


def get_top_mentors(mentors: list[Mentor], count: int = 3) -> list[Mentor]:
    """상위 멘토 반환 (평점 내림차순)"""
    sorted_mentors = sorted(mentors, key=lambda m: m.rating, reverse=True)
    return sorted_mentors[:count]
