"""Content/Library 애플리케이션 계층 — 포트 + UseCase."""
from .ports import IHistoryRepository
from .use_cases import SaveHistoryEntryUseCase

__all__ = [
    "IHistoryRepository",
    "SaveHistoryEntryUseCase",
]
