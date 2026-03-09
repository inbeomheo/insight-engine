"""
브랜치 버전 서비스 — 콘텐츠의 브랜치 기반 버전 관리
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ContentBranch:
    """콘텐츠 브랜치"""
    branch_id: str
    parent_id: str  # None이면 루트
    name: str
    content: str
    created_at: str = ""
    is_merged: bool = False


def _new_id() -> str:
    return f"branch_{uuid.uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_branch(parent_id: str, name: str, content: str) -> ContentBranch:
    """브랜치 생성

    Args:
        parent_id: 부모 브랜치 ID (루트면 빈 문자열 또는 None)
        name: 브랜치 이름
        content: 콘텐츠 텍스트

    Returns:
        ContentBranch: 생성된 브랜치
    """
    if not name.strip():
        raise ValueError("브랜치 이름은 비어있을 수 없습니다.")

    return ContentBranch(
        branch_id=_new_id(),
        parent_id=parent_id or "",
        name=name.strip(),
        content=content,
        created_at=_timestamp(),
        is_merged=False,
    )


def list_branches(parent_id: str, branches: list) -> list:
    """특정 부모의 하위 브랜치 목록

    Args:
        parent_id: 부모 브랜치 ID
        branches: 전체 브랜치 목록

    Returns:
        list[ContentBranch]: 하위 브랜치들
    """
    return [b for b in branches if b.parent_id == parent_id]


def merge_branches(branch_a: ContentBranch, branch_b: ContentBranch) -> ContentBranch:
    """두 브랜치 병합 (공통 접두사 + a 전용 + b 전용)

    Args:
        branch_a: 첫 번째 브랜치
        branch_b: 두 번째 브랜치

    Returns:
        ContentBranch: 병합 결과 브랜치
    """
    lines_a = branch_a.content.splitlines()
    lines_b = branch_b.content.splitlines()

    # 공통 접두사 찾기
    common_len = 0
    for i in range(min(len(lines_a), len(lines_b))):
        if lines_a[i] == lines_b[i]:
            common_len = i + 1
        else:
            break

    common = lines_a[:common_len]
    only_a = lines_a[common_len:]
    only_b = lines_b[common_len:]

    merged_lines = common + only_a + only_b
    merged_content = "\n".join(merged_lines)

    return ContentBranch(
        branch_id=_new_id(),
        parent_id=branch_a.parent_id,
        name=f"merge({branch_a.name}+{branch_b.name})",
        content=merged_content,
        created_at=_timestamp(),
        is_merged=True,
    )


def detect_conflicts(branch_a: ContentBranch, branch_b: ContentBranch) -> list:
    """충돌 탐지 — 동일 라인 위치에서 서로 다른 내용

    Args:
        branch_a: 첫 번째 브랜치
        branch_b: 두 번째 브랜치

    Returns:
        list[str]: 충돌 설명 목록
    """
    lines_a = branch_a.content.splitlines()
    lines_b = branch_b.content.splitlines()

    conflicts = []
    min_len = min(len(lines_a), len(lines_b))

    for i in range(min_len):
        if lines_a[i] != lines_b[i]:
            conflicts.append(
                f"라인 {i + 1} 충돌: '{lines_a[i][:50]}' vs '{lines_b[i][:50]}'"
            )

    # 길이가 다른 부분도 충돌로 간주
    if len(lines_a) != len(lines_b):
        conflicts.append(
            f"라인 수 불일치: {len(lines_a)}줄 vs {len(lines_b)}줄"
        )

    return conflicts


def get_branch_history(branches: list, branch_id: str) -> list:
    """조상 이력 추적 (현재 → 루트)

    Args:
        branches: 전체 브랜치 목록
        branch_id: 시작 브랜치 ID

    Returns:
        list[ContentBranch]: 조상 이력 (현재 브랜치 포함, 루트까지)
    """
    branch_map = {b.branch_id: b for b in branches}
    history = []
    visited = set()  # 순환 방지

    current_id = branch_id
    while current_id and current_id in branch_map:
        if current_id in visited:
            break  # 순환 참조 방지
        visited.add(current_id)

        branch = branch_map[current_id]
        history.append(branch)
        current_id = branch.parent_id

    return history
