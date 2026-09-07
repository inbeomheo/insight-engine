"""HistoryEntry Aggregate 단위 테스트."""
from __future__ import annotations

import pytest

from src.contexts.content_library.domain.history_entry import HistoryEntry
from src.contexts.content_library.domain.value_objects import OwnerId, ReportId


class TestFromDict:
    def test_basic_fields(self):
        entry = HistoryEntry.from_dict(
            {"id": "r-1", "url": "https://y/v", "title": "T", "style": "blog_seo"},
            owner_id="user-1",
        )
        assert entry.report_id == ReportId("r-1")
        assert entry.owner_id == OwnerId("user-1")
        assert entry.url == "https://y/v"
        assert entry.title == "T"
        assert entry.style == "blog_seo"

    def test_missing_id_raises(self):
        with pytest.raises(ValueError, match="id/report_id"):
            HistoryEntry.from_dict({"url": "https://y/v"}, owner_id="user-1")

    def test_report_id_fallback(self):
        entry = HistoryEntry.from_dict(
            {"report_id": "r-2", "title": "T"}, owner_id="u"
        )
        assert entry.report_id == ReportId("r-2")

    def test_keywords_default_empty(self):
        entry = HistoryEntry.from_dict({"id": "r-1"}, owner_id="u")
        assert entry.keywords == []

    def test_keywords_preserved(self):
        entry = HistoryEntry.from_dict(
            {"id": "r-1", "keywords": ["a", "b"]}, owner_id="u"
        )
        assert entry.keywords == ["a", "b"]

    def test_mindmap_field_camel_to_snake(self):
        entry = HistoryEntry.from_dict(
            {"id": "r-1", "mindmapMarkdown": "# Map"}, owner_id="u"
        )
        assert entry.mindmap_markdown == "# Map"

    def test_owner_id_none_raises(self):
        with pytest.raises(ValueError, match="OwnerId"):
            HistoryEntry.from_dict({"id": "r-1"}, owner_id="")


class TestToRow:
    def test_basic_serialization(self):
        entry = HistoryEntry.from_dict(
            {"id": "r-1", "url": "u", "title": "t", "style": "s"},
            owner_id="user-1",
        )
        row = entry.to_row()
        assert row["user_id"] == "user-1"
        assert row["report_id"] == "r-1"
        assert row["url"] == "u"
        assert row["title"] == "t"
        assert row["style"] == "s"

    def test_keywords_default_list(self):
        entry = HistoryEntry.from_dict({"id": "r-1"}, owner_id="u")
        assert entry.to_row()["keywords"] == []

    def test_mindmap_field_name(self):
        entry = HistoryEntry.from_dict(
            {"id": "r-1", "mindmapMarkdown": "# Map"}, owner_id="u"
        )
        assert entry.to_row()["mindmap_markdown"] == "# Map"

    def test_row_uses_bounded_schema_transcript_preview(self):
        entry = HistoryEntry.from_dict(
            {
                "id": "r-1",
                "transcript": "x" * 600,
                "transcript_source": "api",
            },
            owner_id="u",
        )

        row = entry.to_row()

        assert row["transcript_preview"] == "x" * 500
        assert "transcript" not in row
        assert "transcript_source" not in row
