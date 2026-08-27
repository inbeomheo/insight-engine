"""Chroma must remain an embedded implementation detail, never a network service."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REVIEWED_SERVER_ADVISORIES = {
    "CVE-2026-45829",
    "CVE-2026-45830",
    "CVE-2026-45831",
    "CVE-2026-45833",
}


def test_chroma_factory_only_constructs_an_embedded_persistent_client():
    factory = (ROOT / "services/rag/chroma_client_factory.py").read_text(encoding="utf-8")

    assert "chromadb.PersistentClient" in factory
    assert "chromadb.HttpClient" not in factory
    assert "chromadb.Client(" not in factory


def test_release_artifacts_never_start_or_publish_a_chroma_server():
    deployment_text = "\n".join(
        (ROOT / name).read_text(encoding="utf-8")
        for name in ("Dockerfile", "docker-compose.yml", "docker-compose.deploy.yml")
    ).lower()

    assert "chromadb/chroma" not in deployment_text
    assert "chroma run" not in deployment_text
    assert "chroma server" not in deployment_text


def test_security_policy_tracks_every_temporary_chroma_audit_exception():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    for advisory in REVIEWED_SERVER_ADVISORIES:
        assert advisory in policy
    assert "PersistentClient" in policy
    assert "no patched PyPI release" in policy
