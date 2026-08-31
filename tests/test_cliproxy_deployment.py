from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _compose():
    return yaml.safe_load((ROOT / "docker-compose.deploy.yml").read_text())


def test_deployment_uses_pinned_cliproxy_service_without_chatmock():
    services = _compose()["services"]

    assert "cli-proxy-api" in services
    assert "chatmock" not in services
    proxy = services["cli-proxy-api"]
    assert proxy["image"] == "eceasy/cli-proxy-api:v7.2.146"
    assert proxy["ports"] == ["127.0.0.1:8317:8317"]


def test_backend_waits_for_healthy_cliproxy_and_uses_internal_endpoint():
    backend = _compose()["services"]["backend"]

    assert backend["depends_on"]["cli-proxy-api"]["condition"] == "service_healthy"
    assert backend["environment"]["CLIPROXY_BASE_URL"] == "http://cli-proxy-api:8317/v1"
    assert backend["environment"]["CLIPROXY_API_KEY"] == "${CLIPROXY_API_KEY}"


def test_cliproxy_secrets_are_host_mounted_not_committed():
    proxy = _compose()["services"]["cli-proxy-api"]
    volumes = set(proxy["volumes"])

    assert "/home/heo/cliproxyapi/config.yaml:/CLIProxyAPI/config.yaml:ro" in volumes
    assert "/home/heo/cliproxyapi/auths:/root/.cli-proxy-api" in volumes
    assert "/home/heo/cliproxyapi/logs:/CLIProxyAPI/logs" in volumes
    assert "healthcheck" in proxy
