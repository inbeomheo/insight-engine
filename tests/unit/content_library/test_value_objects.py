"""Content/Library 도메인 VO 단위 테스트."""
from __future__ import annotations

import pytest

from src.contexts.content_library.domain.value_objects import OwnerId, ReportId


class TestReportId:
    def test_valid_value(self):
        rid = ReportId("uuid-1234")
        assert str(rid) == "uuid-1234"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="ReportId"):
            ReportId("")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="ReportId"):
            ReportId(None)  # type: ignore[arg-type]

    def test_frozen(self):
        rid = ReportId("uuid-1234")
        with pytest.raises(AttributeError):
            rid.value = "other"  # type: ignore[misc]

    def test_equality(self):
        assert ReportId("x") == ReportId("x")
        assert ReportId("x") != ReportId("y")


class TestOwnerId:
    def test_valid_value(self):
        oid = OwnerId("user-abc")
        assert str(oid) == "user-abc"

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="OwnerId"):
            OwnerId("")

    def test_non_string_raises(self):
        with pytest.raises(ValueError, match="OwnerId"):
            OwnerId(None)  # type: ignore[arg-type]

    def test_equality(self):
        assert OwnerId("u1") == OwnerId("u1")
        assert OwnerId("u1") != OwnerId("u2")
