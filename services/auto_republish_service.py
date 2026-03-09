"""자동 재발행 서비스 -- 콘텐츠 업데이트 및 재발행 처리"""
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class RepublishResult:
    """재발행 결과"""
    content_id: str = ""
    original_hash: str = ""
    updated_hash: str = ""
    changes: list = field(default_factory=list)  # list[str]
    republished_at: str = ""


def _compute_hash(content: str) -> str:
    """콘텐츠의 SHA-256 해시를 계산한다."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _apply_text_updates(content: str, updates: dict) -> tuple[str, list[str]]:
    """업데이트 사항을 콘텐츠에 적용하고 변경 목록을 반환한다.

    Args:
        content: 원본 콘텐츠
        updates: {
            "replacements": [{"old": "...", "new": "..."}],
            "append": "추가할 텍스트",
            "prepend": "앞에 추가할 텍스트",
            "title": "새 제목",
        }

    Returns:
        (수정된 콘텐츠, 변경 목록)
    """
    changes: list[str] = []
    result = content

    # 텍스트 치환
    replacements = updates.get("replacements", [])
    for rep in replacements:
        old = rep.get("old", "")
        new = rep.get("new", "")
        if old and old in result:
            result = result.replace(old, new)
            changes.append(f"텍스트 치환: '{old[:30]}...' → '{new[:30]}...'")

    # 앞에 추가
    prepend = updates.get("prepend", "")
    if prepend:
        result = prepend + "\n\n" + result
        changes.append("콘텐츠 앞에 텍스트 추가")

    # 뒤에 추가
    append = updates.get("append", "")
    if append:
        result = result + "\n\n" + append
        changes.append("콘텐츠 뒤에 텍스트 추가")

    # 제목 변경
    title = updates.get("title", "")
    if title:
        # 첫 번째 마크다운 헤딩 교체
        heading_pattern = r'^#\s+.+$'
        if re.search(heading_pattern, result, re.MULTILINE):
            result = re.sub(heading_pattern, f"# {title}", result, count=1, flags=re.MULTILINE)
            changes.append(f"제목 변경: '{title}'")

    return result, changes


def auto_republish(
    content_id: str,
    content: str,
    updates: dict | None = None,
) -> RepublishResult:
    """콘텐츠를 업데이트하고 재발행 결과를 생성한다.

    Args:
        content_id: 콘텐츠 식별자
        content: 원본 콘텐츠
        updates: 업데이트 사항 (없으면 해시만 갱신)

    Returns:
        RepublishResult
    """
    original_hash = _compute_hash(content)
    changes: list[str] = []

    if updates:
        updated_content, changes = _apply_text_updates(content, updates)
    else:
        updated_content = content
        changes.append("변경 없음 — 해시 갱신만 수행")

    updated_hash = _compute_hash(updated_content)
    now = datetime.now(timezone.utc).isoformat()

    return RepublishResult(
        content_id=content_id,
        original_hash=original_hash,
        updated_hash=updated_hash,
        changes=changes,
        republished_at=now,
    )
