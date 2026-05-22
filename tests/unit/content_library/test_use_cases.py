"""Content/Library UseCase 단위 테스트 (Mock Repository)."""
from __future__ import annotations

from src.contexts.content_library.application.ports import IHistoryRepository
from src.contexts.content_library.application.use_cases import (
    DeleteHistoryEntryUseCase,
    ListHistoryEntriesUseCase,
    SaveHistoryEntryUseCase,
    ToggleFavoriteUseCase,
    UpdateHistoryEntryUseCase,
)
from src.contexts.content_library.domain.history_entry import HistoryEntry


class FakeRepo(IHistoryRepository):
    def __init__(self):
        self.saved: list[HistoryEntry] = []
        self.list_response: dict = {"histories": [], "total": 0}
        self.update_calls: list[tuple] = []
        self.toggle_response: dict = {"success": True, "is_favorite": True}
        self.delete_calls: list[tuple] = []

    def save(self, entry):
        self.saved.append(entry)
        return {"saved": True, "report_id": str(entry.report_id)}

    def save_many(self, entries):
        self.saved.extend(entries)
        return len(entries)

    def list_for_user(self, user_id, page=1, per_page=20):
        return {**self.list_response, "page": page, "per_page": per_page}

    def update(self, user_id, report_id, updates):
        self.update_calls.append((user_id, report_id, updates))
        return True

    def toggle_favorite(self, user_id, report_id):
        return self.toggle_response

    def delete(self, user_id, report_id):
        self.delete_calls.append((user_id, report_id))
        return True


class TestSave:
    def test_save_basic(self):
        repo = FakeRepo()
        uc = SaveHistoryEntryUseCase(repo)
        result = uc.execute("user-1", {"id": "r-1", "title": "T"})
        assert result == {"saved": True, "report_id": "r-1"}
        assert len(repo.saved) == 1
        assert repo.saved[0].owner_id.value == "user-1"

    def test_save_user_id_none(self):
        repo = FakeRepo()
        uc = SaveHistoryEntryUseCase(repo)
        result = uc.execute(None, {"id": "r-1"})
        assert result is None
        assert not repo.saved

    def test_save_user_id_empty_string(self):
        repo = FakeRepo()
        uc = SaveHistoryEntryUseCase(repo)
        result = uc.execute("", {"id": "r-1"})
        assert result is None

    def test_save_data_missing_id(self):
        repo = FakeRepo()
        uc = SaveHistoryEntryUseCase(repo)
        result = uc.execute("user-1", {"title": "T"})
        assert result is None
        assert not repo.saved


class TestList:
    def test_list_with_user(self):
        repo = FakeRepo()
        repo.list_response = {"histories": [{"id": 1}], "total": 1}
        uc = ListHistoryEntriesUseCase(repo)
        result = uc.execute("user-1", page=2, per_page=10)
        assert result["total"] == 1
        assert result["page"] == 2
        assert result["per_page"] == 10

    def test_list_no_user(self):
        repo = FakeRepo()
        uc = ListHistoryEntriesUseCase(repo)
        result = uc.execute(None)
        assert result == {
            "histories": [],
            "total": 0,
            "page": 1,
            "per_page": 20,
            "total_pages": 0,
            "has_more": False,
        }


class TestUpdate:
    def test_update_ok(self):
        repo = FakeRepo()
        uc = UpdateHistoryEntryUseCase(repo)
        assert uc.execute("u", "r-1", {"title": "X"}) is True
        assert repo.update_calls == [("u", "r-1", {"title": "X"})]

    def test_update_no_user(self):
        assert UpdateHistoryEntryUseCase(FakeRepo()).execute(None, "r-1", {}) is False

    def test_update_no_report_id(self):
        assert UpdateHistoryEntryUseCase(FakeRepo()).execute("u", "", {}) is False


class TestToggle:
    def test_toggle_ok(self):
        repo = FakeRepo()
        result = ToggleFavoriteUseCase(repo).execute("u", "r-1")
        assert result == {"success": True, "is_favorite": True}

    def test_toggle_no_user(self):
        result = ToggleFavoriteUseCase(FakeRepo()).execute(None, "r-1")
        assert result == {"success": False, "error": "Not authenticated"}

    def test_toggle_no_report(self):
        result = ToggleFavoriteUseCase(FakeRepo()).execute("u", "")
        assert result == {"success": False, "error": "Not authenticated"}


class TestDelete:
    def test_delete_ok(self):
        repo = FakeRepo()
        assert DeleteHistoryEntryUseCase(repo).execute("u", "r-1") is True
        assert repo.delete_calls == [("u", "r-1")]

    def test_delete_no_user(self):
        assert DeleteHistoryEntryUseCase(FakeRepo()).execute(None, "r-1") is False

    def test_delete_no_report(self):
        assert DeleteHistoryEntryUseCase(FakeRepo()).execute("u", "") is False
