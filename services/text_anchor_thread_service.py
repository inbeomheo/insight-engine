"""
텍스트 앵커 쓰레드 서비스 — 텍스트의 특정 범위에 쓰레드 토론 연결
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class TextAnchor:
    """텍스트 앵커 (특정 텍스트 범위)"""
    anchor_id: str
    document_id: str
    start_offset: int
    end_offset: int
    selected_text: str


@dataclass
class ThreadComment:
    """쓰레드 코멘트"""
    comment_id: str
    anchor_id: str
    author: str
    content: str
    timestamp: str
    resolved: bool = False


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_anchor(
    document_id: str,
    start: int,
    end: int,
    text: str,
) -> TextAnchor:
    """앵커 생성

    Args:
        document_id: 문서 ID
        start: 시작 오프셋
        end: 끝 오프셋
        text: 선택된 텍스트

    Returns:
        TextAnchor: 생성된 앵커
    """
    if start < 0 or end < 0:
        raise ValueError("오프셋은 0 이상이어야 합니다.")
    if start >= end:
        raise ValueError("시작 오프셋은 끝 오프셋보다 작아야 합니다.")
    if not text.strip():
        raise ValueError("선택 텍스트가 비어있습니다.")

    return TextAnchor(
        anchor_id=_new_id("anchor"),
        document_id=document_id,
        start_offset=start,
        end_offset=end,
        selected_text=text,
    )


def add_comment(
    anchor_id: str,
    author: str,
    content: str,
) -> ThreadComment:
    """앵커에 코멘트 추가

    Args:
        anchor_id: 앵커 ID
        author: 작성자
        content: 코멘트 내용

    Returns:
        ThreadComment: 생성된 코멘트
    """
    if not author.strip():
        raise ValueError("작성자 이름이 비어있습니다.")
    if not content.strip():
        raise ValueError("코멘트 내용이 비어있습니다.")

    return ThreadComment(
        comment_id=_new_id("comment"),
        anchor_id=anchor_id,
        author=author.strip(),
        content=content.strip(),
        timestamp=_timestamp(),
        resolved=False,
    )


def resolve_thread(comments: list, anchor_id: str) -> list:
    """쓰레드 해결 처리 — 해당 앵커의 모든 코멘트를 resolved로 표시

    Args:
        comments: 전체 코멘트 목록
        anchor_id: 해결할 앵커 ID

    Returns:
        list[ThreadComment]: resolved=True로 업데이트된 코멘트 목록
    """
    result = []
    for c in comments:
        if c.anchor_id == anchor_id:
            resolved = ThreadComment(
                comment_id=c.comment_id,
                anchor_id=c.anchor_id,
                author=c.author,
                content=c.content,
                timestamp=c.timestamp,
                resolved=True,
            )
            result.append(resolved)
        else:
            result.append(c)
    return result


def get_active_threads(comments: list) -> list:
    """미해결 쓰레드 목록 (앵커별 코멘트 수)

    Args:
        comments: 전체 코멘트 목록

    Returns:
        list[dict]: [{anchor_id, comment_count, latest_timestamp}]
    """
    # 미해결 코멘트만 앵커별 집계
    anchor_stats = {}
    for c in comments:
        if c.resolved:
            continue
        if c.anchor_id not in anchor_stats:
            anchor_stats[c.anchor_id] = {
                "anchor_id": c.anchor_id,
                "comment_count": 0,
                "latest_timestamp": c.timestamp,
            }
        anchor_stats[c.anchor_id]["comment_count"] += 1
        if c.timestamp > anchor_stats[c.anchor_id]["latest_timestamp"]:
            anchor_stats[c.anchor_id]["latest_timestamp"] = c.timestamp

    # 최신 순 정렬
    threads = sorted(
        anchor_stats.values(),
        key=lambda x: x["latest_timestamp"],
        reverse=True,
    )
    return threads
