from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _dockerignore_patterns() -> set[str]:
    return {
        line.strip()
        for line in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def test_runtime_user_data_is_excluded_from_docker_build_context():
    patterns = _dockerignore_patterns()

    assert {
        "/data/",
        "/cache/",
        "/logs/",
        "/downloads/",
        "**/*.db",
        "**/*.db-*",
        "**/*.sqlite",
        "**/*.sqlite-*",
        "**/*.sqlite3",
        "**/*.sqlite3-*",
        "**/*.jsonl",
        "**/notebooklm_state.json*",
    } <= patterns


def test_runtime_excludes_are_anchored_without_hiding_source_directories():
    patterns = _dockerignore_patterns()

    assert "/data/" in patterns
    assert "/cache/" in patterns
    assert "data/" not in patterns
    assert "cache/" not in patterns
    assert "services/data/" not in patterns


def test_docker_image_does_not_rely_on_late_database_deletion():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "COPY . ." in dockerfile
    assert "**/*.db" in _dockerignore_patterns()
    assert "**/*.sqlite3" in _dockerignore_patterns()
