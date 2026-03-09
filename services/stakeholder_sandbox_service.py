"""
이해관계자 샌드박스 서비스.

이해관계자별 역할에 따라 콘텐츠를 필터링/마스킹하고 주석을 추가한다.
"""

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Stakeholder:
    """이해관계자."""
    stakeholder_id: str
    name: str
    role: str  # executive / legal / marketing / technical / external
    view_preferences: dict  # 표시 선호 설정


@dataclass
class SandboxView:
    """샌드박스 뷰."""
    view_id: str
    stakeholder_id: str
    content_filtered: str
    annotations: list  # list[str]
    redacted_fields: list  # list[str]


# 역할별 민감 패턴 정의
_ROLE_REDACTION_PATTERNS = {
    "external": [
        r"\b\d{3}[-.]?\d{4}[-.]?\d{4}\b",  # 전화번호
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # 이메일
        r"\b\d{6}[-]?\d{7}\b",  # 주민등록번호 패턴
    ],
    "marketing": [
        r"\b\d{6}[-]?\d{7}\b",  # 주민등록번호
    ],
    "executive": [],  # 임원은 전체 접근
    "legal": [],  # 법무도 전체 접근
    "technical": [
        r"\b\d{6}[-]?\d{7}\b",  # 주민등록번호
    ],
}

# 역할별 기본 주석
_ROLE_ANNOTATIONS = {
    "executive": "경영진 뷰 — 요약 중심으로 표시됩니다",
    "legal": "법무 뷰 — 모든 콘텐츠가 표시됩니다",
    "marketing": "마케팅 뷰 — 개인정보 일부가 마스킹됩니다",
    "technical": "기술 뷰 — 민감 개인정보가 마스킹됩니다",
    "external": "외부 뷰 — 연락처/개인정보가 마스킹됩니다",
}


def apply_redaction(content: str, sensitive_patterns: list) -> str:
    """민감 정보를 [REDACTED]로 마스킹한다."""
    result = content
    for pattern in sensitive_patterns:
        result = re.sub(pattern, "[REDACTED]", result)
    return result


def create_sandbox(content: dict, stakeholder: Stakeholder) -> SandboxView:
    """역할별 필터링된 뷰를 생성한다."""
    text = content.get("text", "")
    role = stakeholder.role

    # 역할별 마스킹 패턴 적용
    patterns = _ROLE_REDACTION_PATTERNS.get(role, [])
    filtered = apply_redaction(text, patterns)

    # 마스킹된 필드 목록
    redacted = []
    if filtered != text:
        redacted.append("personal_info")

    # 기본 주석 추가
    annotations = []
    default_note = _ROLE_ANNOTATIONS.get(role)
    if default_note:
        annotations.append(default_note)

    return SandboxView(
        view_id=f"sv_{uuid.uuid4().hex[:8]}",
        stakeholder_id=stakeholder.stakeholder_id,
        content_filtered=filtered,
        annotations=annotations,
        redacted_fields=redacted,
    )


def add_annotation(view: SandboxView, annotation: str) -> SandboxView:
    """뷰에 주석을 추가한다."""
    new_annotations = list(view.annotations) + [annotation]
    return SandboxView(
        view_id=view.view_id,
        stakeholder_id=view.stakeholder_id,
        content_filtered=view.content_filtered,
        annotations=new_annotations,
        redacted_fields=list(view.redacted_fields),
    )


def compare_views(views: list) -> dict:
    """여러 뷰 간 차이를 비교한다."""
    if len(views) < 2:
        return {"compared": False, "reason": "비교할 뷰가 2개 이상 필요합니다"}

    comparison = {
        "compared": True,
        "view_count": len(views),
        "views": [],
    }

    for view in views:
        comparison["views"].append({
            "view_id": view.view_id,
            "stakeholder_id": view.stakeholder_id,
            "content_length": len(view.content_filtered),
            "annotation_count": len(view.annotations),
            "redacted_count": len(view.redacted_fields),
            "has_redactions": len(view.redacted_fields) > 0,
        })

    # 콘텐츠 길이 차이 (마스킹으로 인한)
    lengths = [len(v.content_filtered) for v in views]
    comparison["max_length_diff"] = max(lengths) - min(lengths)

    return comparison
