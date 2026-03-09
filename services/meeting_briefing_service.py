"""
미팅 브리핑 서비스.

회의 전 브리핑 자료를 생성한다.
"""

from dataclasses import dataclass, field
import uuid
import math


@dataclass
class MeetingInfo:
    """회의 정보"""
    meeting_id: str = ""
    title: str = ""
    attendees: list = field(default_factory=list)
    agenda: list = field(default_factory=list)
    date: str = ""
    duration_min: int = 60


@dataclass
class Briefing:
    """브리핑 자료"""
    meeting_id: str = ""
    executive_summary: str = ""
    key_topics: list = field(default_factory=list)
    action_items: list = field(default_factory=list)
    preparation_notes: list = field(default_factory=list)


def create_briefing(
    meeting_info: MeetingInfo,
    context_docs: list = None
) -> Briefing:
    """
    브리핑 생성.

    회의 정보와 참조 문서를 기반으로 브리핑 자료를 구성한다.
    """
    context_docs = context_docs or []

    # 핵심 요약
    summary = generate_summary(meeting_info.agenda, context_docs)

    # 주요 토픽: 안건에서 추출
    key_topics = list(meeting_info.agenda) if meeting_info.agenda else ["안건 미정"]

    # 액션 아이템: 참조 문서에서 추출
    action_items = []
    for doc in context_docs:
        items = extract_action_items(doc)
        action_items.extend(items)

    # 준비 사항
    preparation_notes = []
    if meeting_info.attendees:
        preparation_notes.append(f"참석자 {len(meeting_info.attendees)}명 확인")
    if meeting_info.agenda:
        preparation_notes.append(f"안건 {len(meeting_info.agenda)}개 검토 필요")
    if context_docs:
        preparation_notes.append(f"참조 문서 {len(context_docs)}개 사전 검토 권장")

    return Briefing(
        meeting_id=meeting_info.meeting_id,
        executive_summary=summary,
        key_topics=key_topics,
        action_items=action_items,
        preparation_notes=preparation_notes,
    )


def extract_action_items(notes: str) -> list:
    """
    액션 아이템 추출.

    동사로 시작하는 문장이나 특정 키워드가 포함된 문장을 추출한다.
    """
    if not notes:
        return []

    action_keywords = [
        "해야", "필요", "진행", "확인", "검토", "완료",
        "준비", "보고", "작성", "전달", "공유", "정리",
    ]

    items = []
    lines = notes.splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 목록 항목 (-, *, 1. 등) 처리
        clean_line = line.lstrip("-*•·")
        # 번호 목록 처리
        if clean_line and clean_line[0].isdigit():
            clean_line = clean_line.lstrip("0123456789.)")
        clean_line = clean_line.strip()

        if not clean_line:
            continue

        # 액션 키워드 포함 여부
        for keyword in action_keywords:
            if keyword in clean_line:
                items.append(clean_line)
                break

    return items


def generate_summary(agenda: list, context: list = None) -> str:
    """핵심 요약 생성"""
    context = context or []

    parts = []

    if agenda:
        agenda_text = ", ".join(agenda[:5])
        parts.append(f"본 회의에서는 {agenda_text} 등을 논의합니다.")

    if context:
        parts.append(f"참조 문서 {len(context)}건이 제공되었습니다.")

    if not parts:
        return "회의 안건 및 참조 자료가 제공되지 않았습니다."

    return " ".join(parts)


def estimate_time_allocation(agenda: list, duration: int) -> list:
    """
    안건별 시간 배분.

    균등 분배를 기본으로 하되, 마지막 안건에 나머지 시간을 할당한다.
    """
    if not agenda or duration <= 0:
        return []

    # 마무리/QA 시간 (전체의 10%, 최소 5분)
    closing_time = max(5, int(duration * 0.1))
    available_time = duration - closing_time

    time_per_item = available_time // len(agenda) if len(agenda) > 0 else 0

    allocations = []
    remaining = available_time

    for i, item in enumerate(agenda):
        if i == len(agenda) - 1:
            # 마지막 안건에 남은 시간 할당
            allocated = remaining
        else:
            allocated = time_per_item
            remaining -= time_per_item

        allocations.append({
            "agenda_item": item,
            "allocated_min": allocated,
            "order": i + 1,
        })

    # 마무리 시간 추가
    allocations.append({
        "agenda_item": "마무리 / Q&A",
        "allocated_min": closing_time,
        "order": len(agenda) + 1,
    })

    return allocations
