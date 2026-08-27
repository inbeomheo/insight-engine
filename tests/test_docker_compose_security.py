"""Docker Compose host exposure regression tests."""
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_standard_compose_publishes_ports_on_loopback_only():
    compose = yaml.safe_load(
        (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    )

    published_services = {
        name: service.get('ports', [])
        for name, service in compose['services'].items()
        if service.get('ports')
    }

    assert published_services
    for service_name, ports in published_services.items():
        assert ports, service_name
        for port in ports:
            assert str(port).startswith('127.0.0.1:'), (
                f'{service_name} publishes a non-loopback host port: {port}'
            )


def test_standard_compose_documents_local_development_boundary():
    compose = (ROOT / 'docker-compose.yml').read_text(encoding='utf-8')
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')

    assert 'FLASK_ENV=${FLASK_ENV:-development}' in compose
    assert '127.0.0.1' in readme
    assert 'LAN이나 인터넷에는 기본 공개되지 않습니다' in readme
    assert 'docker-compose.deploy.yml' in readme
