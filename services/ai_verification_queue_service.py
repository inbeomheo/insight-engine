"""AI 검증 큐 서비스

AI 생성 콘텐츠의 검증 티켓을 관리하는 인메모리 큐.
티켓 생성 → 검토 → 승인/반려/수정요청 워크플로우를 지원한다.
"""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class VerificationTicket:
    """검증 티켓"""
    ticket_id: str                      # 티켓 고유 ID
    content_id: str                     # 대상 콘텐츠 ID
    content_preview: str                # 콘텐츠 미리보기 (앞 200자)
    status: str = 'pending'             # "pending" | "approved" | "rejected" | "needs_revision"
    priority: str = 'normal'            # "low" | "normal" | "high" | "urgent"
    created_at: str = ''                # ISO 8601 생성 시각
    reviewer: str = ''                  # 검토자 ID
    decided_at: str = ''                # ISO 8601 결정 시각


# 유효한 상태 / 우선순위 / 결정 값
_VALID_STATUSES = {'pending', 'approved', 'rejected', 'needs_revision'}
_VALID_PRIORITIES = {'low', 'normal', 'high', 'urgent'}
_VALID_DECISIONS = {'approved', 'rejected', 'needs_revision'}

# 인메모리 저장소
_ticket_store: dict[str, VerificationTicket] = {}


def _now_iso() -> str:
    """현재 시각을 ISO 8601 UTC 문자열로 반환한다."""
    return datetime.now(timezone.utc).isoformat()


def _make_preview(content: str, max_len: int = 200) -> str:
    """콘텐츠 미리보기를 생성한다.

    Args:
        content: 원본 콘텐츠
        max_len: 최대 길이

    Returns:
        잘라낸 미리보기 문자열
    """
    content = content.strip()
    if len(content) <= max_len:
        return content
    return content[:max_len] + '...'


def queue_for_verification(
    content_id: str,
    content: str,
    priority: str = 'normal',
) -> VerificationTicket:
    """콘텐츠를 검증 큐에 등록한다.

    Args:
        content_id: 콘텐츠 식별자
        content: 검증 대상 콘텐츠 전문
        priority: 우선순위 ("low" | "normal" | "high" | "urgent")

    Returns:
        생성된 VerificationTicket

    Raises:
        ValueError: content_id가 빈 문자열이거나, priority가 유효하지 않은 경우
    """
    if not content_id or not content_id.strip():
        raise ValueError("content_id는 비어있을 수 없습니다")

    if priority not in _VALID_PRIORITIES:
        raise ValueError(
            f"유효하지 않은 priority: '{priority}'. "
            f"허용값: {sorted(_VALID_PRIORITIES)}"
        )

    ticket = VerificationTicket(
        ticket_id=str(uuid.uuid4()),
        content_id=content_id.strip(),
        content_preview=_make_preview(content),
        status='pending',
        priority=priority,
        created_at=_now_iso(),
    )

    _ticket_store[ticket.ticket_id] = ticket
    return ticket


def process_ticket(
    ticket_id: str,
    decision: str,
    reviewer: str,
) -> VerificationTicket:
    """티켓을 처리(승인/반려/수정요청)한다.

    Args:
        ticket_id: 처리할 티켓 ID
        decision: 결정 ("approved" | "rejected" | "needs_revision")
        reviewer: 검토자 식별자

    Returns:
        업데이트된 VerificationTicket

    Raises:
        ValueError: ticket_id가 존재하지 않거나, decision이 유효하지 않거나,
                    reviewer가 빈 문자열인 경우
        RuntimeError: 이미 처리된 티켓을 다시 처리하려는 경우
    """
    if ticket_id not in _ticket_store:
        raise ValueError(f"존재하지 않는 ticket_id: '{ticket_id}'")

    if decision not in _VALID_DECISIONS:
        raise ValueError(
            f"유효하지 않은 decision: '{decision}'. "
            f"허용값: {sorted(_VALID_DECISIONS)}"
        )

    if not reviewer or not reviewer.strip():
        raise ValueError("reviewer는 비어있을 수 없습니다")

    ticket = _ticket_store[ticket_id]

    if ticket.status != 'pending':
        raise RuntimeError(
            f"이미 처리된 티켓입니다 (현재 상태: '{ticket.status}')"
        )

    ticket.status = decision
    ticket.reviewer = reviewer.strip()
    ticket.decided_at = _now_iso()

    return ticket


def list_tickets(status: str | None = None) -> list[VerificationTicket]:
    """티켓 목록을 조회한다.

    Args:
        status: 필터 상태 (None이면 전체 조회)

    Returns:
        VerificationTicket 리스트 (생성일 내림차순)

    Raises:
        ValueError: status가 유효하지 않은 경우
    """
    if status is not None and status not in _VALID_STATUSES:
        raise ValueError(
            f"유효하지 않은 status: '{status}'. "
            f"허용값: {sorted(_VALID_STATUSES)}"
        )

    tickets = list(_ticket_store.values())

    if status is not None:
        tickets = [t for t in tickets if t.status == status]

    # 생성일 내림차순 정렬
    tickets.sort(key=lambda t: t.created_at, reverse=True)

    return tickets


def clear_store() -> None:
    """인메모리 저장소를 초기화한다 (테스트용)."""
    _ticket_store.clear()
