"""
/api/admin/system-info 엔드포인트 테스트
"""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as c:
        yield c


ORIGIN = {'Origin': 'http://localhost:3000'}


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestSystemInfo:
    """시스템 정보 API 테스트."""

    def test_system_info_returns_python_version(self, _mock, client):
        """Python 버전 정보가 포함되어야 한다."""
        resp = client.get('/api/admin/system-info', headers=ORIGIN)
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert 'python' in data
        assert 'version' in data['python']
        # 버전 형식: X.Y.Z
        parts = data['python']['version'].split('.')
        assert len(parts) >= 2

    def test_system_info_returns_platform(self, _mock, client):
        """플랫폼 정보가 포함되어야 한다."""
        resp = client.get('/api/admin/system-info', headers=ORIGIN)
        data = json.loads(resp.data)
        assert 'platform' in data
        assert 'system' in data['platform']
        assert 'machine' in data['platform']

    def test_system_info_returns_dependencies(self, _mock, client):
        """의존성 버전 목록이 포함되어야 한다."""
        resp = client.get('/api/admin/system-info', headers=ORIGIN)
        data = json.loads(resp.data)
        assert 'dependencies' in data
        deps = data['dependencies']
        assert 'flask' in deps
        # flask는 반드시 설치됨
        assert deps['flask'] != 'not_installed'

    def test_system_info_returns_uptime(self, _mock, client):
        """uptime_seconds가 0 이상이어야 한다."""
        resp = client.get('/api/admin/system-info', headers=ORIGIN)
        data = json.loads(resp.data)
        assert 'uptime_seconds' in data
        assert data['uptime_seconds'] >= 0

    def test_system_info_uninstalled_package(self, _mock, client):
        """설치되지 않은 패키지는 not_installed로 표시."""
        resp = client.get('/api/admin/system-info', headers=ORIGIN)
        data = json.loads(resp.data)
        deps = data['dependencies']
        # 모든 값은 문자열이어야 함
        for pkg, ver in deps.items():
            assert isinstance(ver, str)
