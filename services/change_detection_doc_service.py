"""
변경 감지 문서 서비스.

문서 버전 간 변경 탐지 + diff를 제공한다.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class DocVersion:
    """문서 버전"""
    version_id: str = ""
    content: str = ""
    timestamp: str = ""
    author: str = ""


@dataclass
class ChangeReport:
    """변경 보고서"""
    old_version: str = ""
    new_version: str = ""
    added_lines: list = field(default_factory=list)
    removed_lines: list = field(default_factory=list)
    modified_count: int = 0
    change_ratio: float = 0.0


def detect_changes(old_text: str, new_text: str) -> ChangeReport:
    """
    라인 기반 diff.

    두 텍스트의 라인별 차이를 계산한다.
    """
    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    old_set = set(old_lines)
    new_set = set(new_lines)

    added = [line for line in new_lines if line not in old_set]
    removed = [line for line in old_lines if line not in new_set]

    # 변경 비율: 변경된 라인 / 전체 라인
    total_lines = max(len(old_lines), len(new_lines), 1)
    change_ratio = (len(added) + len(removed)) / total_lines

    return ChangeReport(
        old_version="old",
        new_version="new",
        added_lines=added,
        removed_lines=removed,
        modified_count=len(added) + len(removed),
        change_ratio=round(min(1.0, change_ratio), 4),
    )


def highlight_changes(report: ChangeReport) -> str:
    """
    변경 하이라이트.

    추가된 라인은 '+ ' 접두사, 제거된 라인은 '- ' 접두사.
    """
    lines = []
    for line in report.removed_lines:
        lines.append(f"- {line}")
    for line in report.added_lines:
        lines.append(f"+ {line}")
    return "\n".join(lines)


def is_significant_change(report: ChangeReport, threshold: float = 0.1) -> bool:
    """
    유의미 변경 여부.

    change_ratio가 threshold를 초과하면 유의미한 변경으로 판단한다.
    """
    return report.change_ratio > threshold


def summarize_changes(report: ChangeReport) -> str:
    """변경 요약 텍스트 생성"""
    parts = []

    if report.added_lines:
        parts.append(f"{len(report.added_lines)}개 라인 추가")
    if report.removed_lines:
        parts.append(f"{len(report.removed_lines)}개 라인 삭제")

    if not parts:
        return "변경 사항 없음"

    ratio_pct = round(report.change_ratio * 100, 1)
    summary = ", ".join(parts)
    return f"{summary} (변경률: {ratio_pct}%)"
