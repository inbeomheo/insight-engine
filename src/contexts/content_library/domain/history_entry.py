"""HistoryEntry Aggregate Root.

콘텐츠 생성 1회의 결과를 1 레코드로 묶는 Aggregate. `ie_histories` 테이블의
한 행에 대응. 비즈니스 불변식은 현재 단순(소유자/식별자만 검증)하므로 도메인
로직이 얇음 — 향후 챕터/메모리/태그 도입 시 확장 예정.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .value_objects import OwnerId, ReportId


@dataclass(slots=True)
class HistoryEntry:
    """사용자 콘텐츠 히스토리 Aggregate Root."""

    report_id: ReportId
    owner_id: OwnerId
    url: str | None = None
    title: str | None = None
    style: str | None = None
    content: str | None = None
    html: str | None = None
    transcript: str | None = None
    transcript_source: str | None = None
    mindmap_markdown: str | None = None
    keywords: list[str] = field(default_factory=list)
    usage: dict | None = None
    elapsed_time: float | None = None
    is_favorite: bool = False
    extras: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict, owner_id: str) -> "HistoryEntry":
        """프론트엔드 dict → HistoryEntry 변환.

        `data['id']`가 ReportId. 없으면 ValueError.
        """
        report_id_value = data.get("id") or data.get("report_id")
        if not report_id_value:
            raise ValueError("HistoryEntry 변환 실패: id/report_id 누락")

        return cls(
            report_id=ReportId(report_id_value),
            owner_id=OwnerId(owner_id),
            url=data.get("url"),
            title=data.get("title"),
            style=data.get("style"),
            content=data.get("content"),
            html=data.get("html"),
            transcript=data.get("transcript"),
            transcript_source=data.get("transcript_source"),
            mindmap_markdown=data.get("mindmapMarkdown"),
            keywords=data.get("keywords", []) or [],
            usage=data.get("usage"),
            elapsed_time=data.get("elapsed_time"),
        )

    def to_row(self) -> dict:
        """현재 ``ie_histories`` 스키마의 INSERT 행으로 직렬화."""
        return {
            "user_id": str(self.owner_id),
            "report_id": str(self.report_id),
            "url": self.url or "",
            "title": self.title or "",
            "style": self.style or "unknown",
            "content": self.content,
            "html": self.html,
            "transcript_preview": (
                self.transcript[:500]
                if isinstance(self.transcript, str)
                else None
            ),
            "mindmap_markdown": self.mindmap_markdown,
            "keywords": self.keywords,
            "usage": self.usage,
            "elapsed_time": self.elapsed_time,
        }


__all__ = ["HistoryEntry"]
