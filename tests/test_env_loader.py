"""Regression tests for the read-only local env loader."""
import os
from pathlib import Path

from utils.env_loader import load_env_file


def test_load_env_file_parses_simple_and_quoted_values(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "PLAIN=value\n"
        "SINGLE='literal $value # kept'\n"
        'DOUBLE="line\\nnext"\n'
        "export WITH_COMMENT=visible # hidden\n"
        "URL=https://example.com/path#fragment\n",
        encoding="utf-8",
    )
    for key in ("PLAIN", "SINGLE", "DOUBLE", "WITH_COMMENT", "URL"):
        monkeypatch.delenv(key, raising=False)

    assert load_env_file(env_file) is True
    assert os.environ["PLAIN"] == "value"
    assert os.environ["SINGLE"] == "literal $value # kept"
    assert os.environ["DOUBLE"] == "line\nnext"
    assert os.environ["WITH_COMMENT"] == "visible"
    assert os.environ["URL"] == "https://example.com/path#fragment"


def test_load_env_file_preserves_existing_values_without_override(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING=file\n", encoding="utf-8")
    monkeypatch.setenv("EXISTING", "process")

    assert load_env_file(env_file) is False
    assert os.environ["EXISTING"] == "process"
    assert load_env_file(env_file, override=True) is True
    assert os.environ["EXISTING"] == "file"


def test_load_env_file_is_read_only_and_ignores_invalid_lines(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    original = "INVALID-KEY=value\nBROKEN='unterminated\nVALID=ok\n"
    env_file.write_text(original, encoding="utf-8")
    monkeypatch.delenv("VALID", raising=False)

    assert load_env_file(Path(env_file)) is True
    assert os.environ["VALID"] == "ok"
    assert env_file.read_text(encoding="utf-8") == original


def test_load_env_file_missing_file_is_a_noop(tmp_path):
    assert load_env_file(tmp_path / "missing.env") is False
