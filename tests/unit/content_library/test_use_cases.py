"""Content/Library UseCase 단위 테스트 (Mock Repository)."""
from __future__ import annotations

from src.contexts.content_library.application.ports import IHistoryRepository
from src.contexts.content_library.application.use_cases import SaveHistoryEntryUseCase
from src.contexts.content_library.domain.history_entry import HistoryEntry


class FakeRepo(IHistoryRepository):
    def __init__(self):
        self.saved: list[HistoryEntry] = []

    def save(self, entry):
        self.saved.append(entry)
        return {"saved": True, "report_id": str(entry.report_id)}

    def save_many(self, entries):
        self.saved.extend(entries)
        return len(entries)


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

