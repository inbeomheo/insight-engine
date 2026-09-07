"""Chroma must remain an embedded implementation detail, never a network service."""
from pathlib import Path

import yaml


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


def test_embedded_chroma_release_surfaces_use_one_backend_process():
    supervisor = (ROOT / "scripts/run_full_stack.py").read_text(encoding="utf-8")
    procfile = (ROOT / "Procfile").read_text(encoding="utf-8")
    nixpacks = (ROOT / "nixpacks.toml").read_text(encoding="utf-8")

    assert "'gunicorn', '--workers=1'" in supervisor
    assert "--workers 1" in procfile
    assert "--preload" not in procfile
    assert "--workers 1" in nixpacks

    manifests = list(
        yaml.safe_load_all((ROOT / "k8s/deployment.yaml").read_text(encoding="utf-8"))
    )
    backend = next(
        item
        for item in manifests
        if item.get("kind") == "Deployment"
        and item.get("metadata", {}).get("name") == "insight-backend"
    )
    backend_hpas = [
        item
        for item in manifests
        if item.get("kind") == "HorizontalPodAutoscaler"
        and item.get("spec", {}).get("scaleTargetRef", {}).get("name")
        == "insight-backend"
    ]

    assert backend["spec"]["replicas"] == 1
    assert backend["spec"]["strategy"]["type"] == "Recreate"
    assert backend_hpas == []


def test_security_policy_tracks_every_temporary_chroma_audit_exception():
    policy = (ROOT / "SECURITY.md").read_text(encoding="utf-8")

    for advisory in REVIEWED_SERVER_ADVISORIES:
        assert advisory in policy
    assert "PersistentClient" in policy
    assert "no patched PyPI release" in policy
