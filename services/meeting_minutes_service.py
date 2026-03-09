"""
회의록 생성 서비스

텍스트 전사(transcript)에서 규칙 기반으로 회의록을 생성하고,
실행 항목(Action Item)을 추출합니다.
외부 API 호출 없이 순수 파이썬으로 동작합니다.
"""
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


# 의사결정 키워드 패턴
_DECISION_KEYWORDS = ["결정", "합의", "확정", "승인", "채택", "동의"]
_DECISION_PATTERN = re.compile(
    r'[^.!?]*(?:' + '|'.join(_DECISION_KEYWORDS) + r')[^.!?]*[.!?]?',
    re.MULTILINE,
)

# 실행 항목 키워드 패턴 — "~해야", "~하겠", "~까지", "담당" 등
_ACTION_PATTERNS = [
    re.compile(r'([^.!?\n]*(?:해야|하여야|해주세요|해 주세요)[^.!?\n]*)', re.MULTILINE),
    re.compile(r'([^.!?\n]*(?:하겠습니다|하겠음|진행하겠)[^.!?\n]*)', re.MULTILINE),
    re.compile(r'([^.!?\n]*(?:까지\s*(?:완료|제출|보고|준비))[^.!?\n]*)', re.MULTILINE),
    re.compile(r'([^.!?\n]*(?:담당[:：]\s*\S+)[^.!?\n]*)', re.MULTILINE),
]

# 마감일 패턴 — "~월 ~일까지", "~까지", "이번 주", "다음 주" 등
_DEADLINE_PATTERNS = [
    re.compile(r'(\d{1,2}월\s*\d{1,2}일)'),
    re.compile(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'),
    re.compile(r'(이번\s*주|다음\s*주|금주|차주|내일|오늘)'),
    re.compile(r'(\d{1,2}일\s*까지)'),
]

# 우선순위 키워드
_PRIORITY_KEYWORDS = {
    "high": ["긴급", "즉시", "최우선", "ASAP", "시급"],
    "medium": ["중요", "가능하면", "이번 주"],
    "low": ["여유", "시간 될 때", "참고"],
}

# 주제 분리 패턴 — 숫자, 기호, 키워드 기반
_TOPIC_PATTERNS = [
    re.compile(r'^(?:\d+[.)]\s*|[-•]\s*|#{1,3}\s*)(.+)', re.MULTILINE),
    re.compile(r'^(?:주제|안건|의제)\s*[:：]\s*(.+)', re.MULTILINE),
]


@dataclass
class ActionItem:
    """실행 항목."""
    task: str
    assignee: str = "미정"
    deadline: str = "미정"
    priority: str = "medium"


@dataclass
class Discussion:
    """논의 항목."""
    topic: str
    summary: str
    participants: List[str] = field(default_factory=list)


@dataclass
class MeetingMinutes:
    """회의록."""
    title: str
    date: str
    attendees: List[str] = field(default_factory=list)
    agenda: List[str] = field(default_factory=list)
    discussions: List[Discussion] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)


def _extract_decisions(text: str) -> List[str]:
    """텍스트에서 의사결정 문장을 추출합니다."""
    decisions = []
    for match in _DECISION_PATTERN.finditer(text):
        sentence = match.group(0).strip()
        if sentence and len(sentence) > 5:
            decisions.append(sentence)
    return decisions


def _extract_deadline(text: str) -> str:
    """텍스트에서 마감일 표현을 추출합니다."""
    for pattern in _DEADLINE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return "미정"


def _extract_assignee(text: str, attendees: List[str]) -> str:
    """텍스트에서 담당자를 추출합니다."""
    # "담당: 홍길동" 패턴
    assignee_match = re.search(r'담당[:：]\s*(\S+)', text)
    if assignee_match:
        return assignee_match.group(1)

    # 참석자 이름이 텍스트에 있으면 해당 참석자를 담당자로
    for attendee in attendees:
        if attendee in text:
            return attendee

    return "미정"


def _determine_priority(text: str) -> str:
    """텍스트에서 우선순위를 판단합니다."""
    for priority, keywords in _PRIORITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return priority
    return "medium"


def _split_into_paragraphs(text: str) -> List[str]:
    """텍스트를 문단(빈 줄 기준) 또는 줄 단위로 분리합니다."""
    # 빈 줄 기준으로 분리
    paragraphs = re.split(r'\n\s*\n', text.strip())
    result = []
    for p in paragraphs:
        stripped = p.strip()
        if stripped:
            result.append(stripped)
    return result if result else [text.strip()]


def _extract_topics(text: str) -> List[str]:
    """텍스트에서 주제/안건을 추출합니다."""
    topics = []
    for pattern in _TOPIC_PATTERNS:
        for match in pattern.finditer(text):
            topic = match.group(1).strip()
            if topic and topic not in topics:
                topics.append(topic)
    return topics


def _build_discussions(
    paragraphs: List[str], attendees: List[str]
) -> List[Discussion]:
    """문단별 Discussion 객체를 생성합니다."""
    discussions = []
    for para in paragraphs:
        if len(para) < 10:
            continue

        # 첫 줄을 주제로, 나머지를 요약으로
        lines = para.split('\n', 1)
        topic = lines[0].strip()
        # 주제에서 번호/기호 제거
        topic = re.sub(r'^(?:\d+[.)]\s*|[-•]\s*|#{1,3}\s*)', '', topic).strip()
        if not topic:
            continue

        summary = lines[1].strip() if len(lines) > 1 else topic

        # 참석자 중 텍스트에 언급된 사람 추출
        participants = [a for a in attendees if a in para]

        discussions.append(Discussion(
            topic=topic,
            summary=summary,
            participants=participants,
        ))

    return discussions


def _extract_raw_action_items(text: str) -> List[str]:
    """텍스트에서 실행 항목 후보 문장을 추출합니다."""
    items = []
    seen = set()
    for pattern in _ACTION_PATTERNS:
        for match in pattern.finditer(text):
            sentence = match.group(1).strip()
            if sentence and sentence not in seen and len(sentence) > 5:
                seen.add(sentence)
                items.append(sentence)
    return items


def transcribe_to_minutes(
    transcript: str, attendees: Optional[List[str]] = None
) -> MeetingMinutes:
    """텍스트 전사에서 회의록을 생성합니다.

    Args:
        transcript: 회의 전사 텍스트
        attendees: 참석자 목록 (None이면 빈 리스트)

    Returns:
        MeetingMinutes 데이터클래스

    Raises:
        ValueError: 전사 텍스트가 비어 있는 경우
    """
    if not transcript or not transcript.strip():
        raise ValueError("전사 텍스트가 비어 있습니다.")

    transcript = transcript.strip()
    attendees = attendees or []

    # 제목 생성 — 첫 줄 기반
    first_line = transcript.split('\n', 1)[0].strip()
    title = re.sub(r'^(?:\d+[.)]\s*|[-•]\s*|#{1,3}\s*)', '', first_line)
    title = title[:50] if len(title) > 50 else title
    if not title:
        title = "회의록"
    title = f"{title} — 회의록"

    # 현재 날짜
    date = datetime.now().strftime("%Y-%m-%d")

    # 안건 추출
    agenda = _extract_topics(transcript)

    # 문단 분리 및 논의 사항 생성
    paragraphs = _split_into_paragraphs(transcript)
    discussions = _build_discussions(paragraphs, attendees)

    # 의사결정 추출
    decisions = _extract_decisions(transcript)

    # 실행 항목 추출
    raw_items = _extract_raw_action_items(transcript)
    action_items = []
    for raw in raw_items:
        action_items.append(ActionItem(
            task=raw,
            assignee=_extract_assignee(raw, attendees),
            deadline=_extract_deadline(raw),
            priority=_determine_priority(raw),
        ))

    return MeetingMinutes(
        title=title,
        date=date,
        attendees=attendees,
        agenda=agenda,
        discussions=discussions,
        decisions=decisions,
        action_items=action_items,
    )


def extract_action_items(minutes: MeetingMinutes) -> List[ActionItem]:
    """회의록에서 실행 항목을 추출합니다.

    이미 회의록에 포함된 action_items를 반환하며,
    discussions 내용에서 추가 항목을 탐색합니다.

    Args:
        minutes: MeetingMinutes 데이터클래스

    Returns:
        ActionItem 리스트
    """
    items = list(minutes.action_items)
    existing_tasks = {item.task for item in items}

    # discussions에서 추가 실행 항목 탐색
    for discussion in minutes.discussions:
        combined_text = f"{discussion.topic} {discussion.summary}"
        raw_items = _extract_raw_action_items(combined_text)
        for raw in raw_items:
            if raw not in existing_tasks:
                existing_tasks.add(raw)
                items.append(ActionItem(
                    task=raw,
                    assignee=(
                        discussion.participants[0]
                        if discussion.participants
                        else "미정"
                    ),
                    deadline=_extract_deadline(raw),
                    priority=_determine_priority(raw),
                ))

    return items
