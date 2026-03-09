"""
권한 인지 편집 서비스.

사용자 역할별 편집 가능 범위를 제어하고, 편집 감사 로그를 생성한다.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class EditPermission:
    """역할별 편집 권한 정의."""
    role: str
    allowed_fields: list  # list[str]
    can_delete: bool
    can_publish: bool


@dataclass
class EditRequest:
    """편집 요청."""
    user_role: str
    field: str
    old_value: str
    new_value: str


@dataclass
class EditResult:
    """편집 결과."""
    approved: bool
    field: str
    new_value: str
    reason: str


def define_permissions(
    role: str,
    fields: list,
    can_delete: bool = False,
    can_publish: bool = False,
) -> EditPermission:
    """역할별 편집 권한을 정의한다."""
    return EditPermission(
        role=role,
        allowed_fields=list(fields),
        can_delete=can_delete,
        can_publish=can_publish,
    )


def check_permission(
    request: EditRequest,
    permissions: list,
) -> EditResult:
    """편집 요청의 권한을 확인한다."""
    # 해당 역할의 권한 찾기
    matched_perm = None
    for perm in permissions:
        if perm.role == request.user_role:
            matched_perm = perm
            break

    if matched_perm is None:
        return EditResult(
            approved=False,
            field=request.field,
            new_value=request.new_value,
            reason=f"역할 '{request.user_role}'에 대한 권한이 정의되지 않음",
        )

    if request.field not in matched_perm.allowed_fields:
        return EditResult(
            approved=False,
            field=request.field,
            new_value=request.new_value,
            reason=f"역할 '{request.user_role}'은(는) '{request.field}' 필드를 편집할 수 없음",
        )

    return EditResult(
        approved=True,
        field=request.field,
        new_value=request.new_value,
        reason=f"역할 '{request.user_role}'의 '{request.field}' 편집 승인됨",
    )


def filter_visible_fields(
    all_fields: list,
    role: str,
    permissions: list,
) -> list:
    """역할별 노출 가능한 필드 목록을 반환한다."""
    for perm in permissions:
        if perm.role == role:
            return [f for f in all_fields if f in perm.allowed_fields]
    # 권한 미정의 역할 — 빈 리스트
    return []


def audit_edit(request: EditRequest, result: EditResult) -> dict:
    """편집 감사 로그를 생성한다."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_role": request.user_role,
        "field": request.field,
        "old_value": request.old_value,
        "new_value": request.new_value,
        "approved": result.approved,
        "reason": result.reason,
    }
