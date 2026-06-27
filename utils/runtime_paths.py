"""Runtime filesystem path helpers."""
from __future__ import annotations

import os
from pathlib import Path


def app_data_dir() -> Path:
    """Return the configured app data directory without creating it."""
    return Path((os.getenv('APP_DATA_DIR') or '').strip() or 'data')


def app_data_path(*parts: str) -> str:
    """Return a path under APP_DATA_DIR, or local ./data in development."""
    return str(app_data_dir().joinpath(*parts))
