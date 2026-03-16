"""
/api/cache/purge 및 purge_expired_cache 테스트
"""
from __future__ import annotations

import json
import os
import tempfile
import time
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


class TestPurgeExpiredCache:
    """purge_expired_cache 서비스 함수 테스트."""

    def test_purge_old_files(self):
        """만료된 파일만 삭제하고 최신 파일은 유지."""
        from services.core import content_service

        tmpdir = tempfile.mkdtemp()
        original_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = tmpdir
        try:
            # 오래된 파일 (2일 전)
            old_file = os.path.join(tmpdir, 'old_transcript.json')
            with open(old_file, 'w') as f:
                f.write('{}')
            os.utime(old_file, (time.time() - 200000, time.time() - 200000))

            # 최신 파일
            new_file = os.path.join(tmpdir, 'new_transcript.json')
            with open(new_file, 'w') as f:
                f.write('{}')

            result = content_service.purge_expired_cache(max_age_hours=24)
            assert result['purged'] == 1
            assert result['remaining'] == 1
            assert not os.path.exists(old_file)
            assert os.path.exists(new_file)
        finally:
            content_service.CACHE_DIR = original_cache_dir

    def test_purge_empty_dir(self):
        """빈 디렉토리에서는 0/0 반환."""
        from services.core import content_service

        tmpdir = tempfile.mkdtemp()
        original_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = tmpdir
        try:
            result = content_service.purge_expired_cache()
            assert result['purged'] == 0
            assert result['remaining'] == 0
        finally:
            content_service.CACHE_DIR = original_cache_dir

    def test_purge_nonexistent_dir(self):
        """존재하지 않는 디렉토리에서는 0/0 반환."""
        from services.core import content_service

        original_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = '/nonexistent/path/cache'
        try:
            result = content_service.purge_expired_cache()
            assert result == {'purged': 0, 'remaining': 0, 'freed_bytes': 0}
        finally:
            content_service.CACHE_DIR = original_cache_dir

    def test_purge_returns_freed_bytes(self):
        """삭제된 파일의 바이트 수를 freed_bytes로 반환."""
        from services.core import content_service

        tmpdir = tempfile.mkdtemp()
        original_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = tmpdir
        try:
            # 오래된 파일 (2일 전, 100바이트)
            old_file = os.path.join(tmpdir, 'old.json')
            with open(old_file, 'w') as f:
                f.write('x' * 100)
            os.utime(old_file, (time.time() - 200000, time.time() - 200000))

            result = content_service.purge_expired_cache(max_age_hours=24)
            assert result['purged'] == 1
            assert result['freed_bytes'] >= 100
            assert 'freed_bytes' in result
        finally:
            content_service.CACHE_DIR = original_cache_dir

    def test_purge_empty_dir_freed_bytes_zero(self):
        """빈 디렉토리에서는 freed_bytes가 0."""
        from services.core import content_service

        tmpdir = tempfile.mkdtemp()
        original_cache_dir = content_service.CACHE_DIR
        content_service.CACHE_DIR = tmpdir
        try:
            result = content_service.purge_expired_cache()
            assert result['freed_bytes'] == 0
        finally:
            content_service.CACHE_DIR = original_cache_dir


@patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
class TestCachePurgeAPI:
    """캐시 퍼지 API 엔드포인트 테스트."""

    @patch('services.core.content_service.purge_expired_cache', return_value={'purged': 3, 'remaining': 5, 'freed_bytes': 1024})
    def test_purge_default(self, mock_purge, _mock_supa, client):
        """기본 호출 시 24시간 기준 정리."""
        resp = client.post('/api/cache/purge',
                           headers={**ORIGIN, 'Content-Type': 'application/json'},
                           data=json.dumps({}))
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True
        assert data['purged'] == 3
        assert data['freed_bytes'] == 1024
        mock_purge.assert_called_once_with(24)

    @patch('services.core.content_service.purge_expired_cache', return_value={'purged': 0, 'remaining': 2, 'freed_bytes': 0})
    def test_purge_custom_hours(self, mock_purge, _mock_supa, client):
        """사용자 지정 시간 기준."""
        resp = client.post('/api/cache/purge',
                           headers={**ORIGIN, 'Content-Type': 'application/json'},
                           data=json.dumps({'max_age_hours': 48}))
        assert resp.status_code == 200
        mock_purge.assert_called_once_with(48)

    def test_purge_invalid_hours(self, _mock_supa, client):
        """음수/0 max_age_hours는 400 에러."""
        resp = client.post('/api/cache/purge',
                           headers={**ORIGIN, 'Content-Type': 'application/json'},
                           data=json.dumps({'max_age_hours': -1}))
        assert resp.status_code == 400

    def test_purge_zero_hours(self, _mock_supa, client):
        """0 max_age_hours는 400 에러."""
        resp = client.post('/api/cache/purge',
                           headers={**ORIGIN, 'Content-Type': 'application/json'},
                           data=json.dumps({'max_age_hours': 0}))
        assert resp.status_code == 400
