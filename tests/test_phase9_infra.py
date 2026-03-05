"""
Phase 9 인프라 & 성능 서비스 테스트
F9-01~F9-25 핵심 단위 테스트
"""
import json
import os
import sys
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

# 프로젝트 루트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── F9-02: TaskQueueService ───────────────────────────────────────────────────

class TestTaskQueueService:

    def test_enqueue_and_get(self):
        from services.task_queue_service import TaskQueueService, TaskStatus

        svc = TaskQueueService(num_workers=1)
        svc.start()

        results = []
        def sample_task(x):
            results.append(x * 2)
            return x * 2

        task_id = svc.enqueue(sample_task, 5)
        assert task_id

        # 완료 대기
        for _ in range(20):
            info = svc.get_task(task_id)
            if info and info['status'] in ('success', 'failed'):
                break
            time.sleep(0.1)

        info = svc.get_task(task_id)
        assert info is not None
        assert info['status'] == 'success'
        assert info['result'] == 10

        svc.stop(timeout=3.0)

    def test_task_failure(self):
        from services.task_queue_service import TaskQueueService, TaskStatus

        svc = TaskQueueService(num_workers=1)
        svc.start()

        def failing_task():
            raise ValueError("테스트 오류")

        task_id = svc.enqueue(failing_task)
        for _ in range(20):
            info = svc.get_task(task_id)
            if info and info['status'] in ('success', 'failed'):
                break
            time.sleep(0.1)

        info = svc.get_task(task_id)
        assert info['status'] == 'failed'
        assert '테스트 오류' in info['error']

        svc.stop(timeout=3.0)

    def test_cancel_pending_task(self):
        from services.task_queue_service import TaskQueueService, TaskStatus

        # 워커 없이 취소 테스트 (큐에만 추가)
        svc = TaskQueueService(num_workers=0)

        def dummy():
            return 'done'

        task_id = svc.enqueue(dummy)
        result = svc.cancel_task(task_id)
        assert result is True

        info = svc.get_task(task_id)
        assert info['status'] == 'cancelled'

    def test_get_stats(self):
        from services.task_queue_service import TaskQueueService

        svc = TaskQueueService(num_workers=1)
        svc.start()
        stats = svc.get_stats()
        assert 'total_tasks' in stats
        assert 'num_workers' in stats
        svc.stop(timeout=3.0)


# ── F9-06: 구조화 로깅 (logging_config) ──────────────────────────────────────

class TestLoggingConfig:

    def test_get_logger(self):
        from services.logging_config import get_logger
        logger = get_logger('test_logger')
        assert logger is not None
        assert logger.name == 'test_logger'

    def test_service_logger(self):
        from services.logging_config import ServiceLogger
        slogger = ServiceLogger('TestService')
        # 예외 없이 로그 출력 가능해야 함
        slogger.info("테스트 메시지")
        slogger.warning("경고 메시지")
        slogger.error("오류 메시지")


# ── F9-09: 메트릭 서비스 ─────────────────────────────────────────────────────

class TestMetricsService:

    def test_record_functions(self):
        from services.metrics_service import (
            record_http_request, record_ai_generation,
            record_cache_hit, record_cache_miss, record_error
        )
        # 예외 없이 실행되어야 함 (prometheus 미설치 시 노옵)
        record_http_request('GET', 'test_endpoint', 200, 0.5)
        record_ai_generation('blog_seo', 'gemini', 'success', 5.0)
        record_cache_hit('ai')
        record_cache_miss('ai')
        record_error('ValueError', 'test_service')

    def test_get_metrics_output(self):
        from services.metrics_service import get_metrics_output
        data, content_type = get_metrics_output()
        assert isinstance(data, bytes)
        assert 'text' in content_type


# ── F9-18: 요청 검증 미들웨어 ────────────────────────────────────────────────

class TestRequestValidator:

    def test_validate_url_valid(self):
        from middleware.request_validator import validate_url
        assert validate_url('https://www.youtube.com/watch?v=abc123') is True
        assert validate_url('http://localhost:5001/test') is True

    def test_validate_url_invalid(self):
        from middleware.request_validator import validate_url
        assert validate_url('not-a-url') is False
        assert validate_url('ftp://example.com') is False
        assert validate_url('') is False

    def test_validate_generate_request_valid(self):
        from middleware.request_validator import validate_generate_request
        errors = validate_generate_request({
            'url': 'https://www.youtube.com/watch?v=abc',
            'style_id': 'blog_seo',
            'length': 'medium',
            'language': 'ko',
        })
        assert errors == []

    def test_validate_generate_request_invalid(self):
        from middleware.request_validator import validate_generate_request
        errors = validate_generate_request({
            'style_id': 'invalid_style',
            'length': 'extra',
        })
        assert len(errors) > 0

    def test_sanitize_string(self):
        from middleware.request_validator import sanitize_string
        assert sanitize_string('  hello  ') == 'hello'
        assert sanitize_string('x' * 5000, max_length=100) == 'x' * 100


# ── F9-21: 시크릿 관리 ───────────────────────────────────────────────────────

class TestSecretManager:

    def test_get_secret_from_env(self):
        from services.secret_manager_service import get_secret, clear_cache

        clear_cache()
        with patch.dict(os.environ, {'TEST_SECRET_KEY': 'my_test_secret'}):
            value = get_secret('TEST_SECRET_KEY', 'TEST_SECRET_KEY')
            assert value == 'my_test_secret'

    def test_get_secret_not_found(self):
        from services.secret_manager_service import get_secret, clear_cache

        clear_cache()
        value = get_secret('NON_EXISTENT_SECRET_12345', '')
        assert value == ''

    def test_clear_cache(self):
        from services.secret_manager_service import get_secret, clear_cache, _SECRET_CACHE

        clear_cache()
        assert len(_SECRET_CACHE) == 0


# ── F9-22: 암호화 서비스 ─────────────────────────────────────────────────────

class TestEncryptionService:

    @pytest.fixture(autouse=True)
    def skip_if_no_crypto(self):
        try:
            from cryptography.fernet import Fernet
        except ImportError:
            pytest.skip("cryptography 패키지 미설치")

    def test_encrypt_decrypt(self):
        from services.encryption_service import EncryptionService

        svc = EncryptionService()
        if not svc.available:
            pytest.skip("암호화 서비스 비활성화")

        plaintext = "민감한 데이터 테스트 1234"
        encrypted = svc.encrypt(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0

        decrypted = svc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_decrypt_tampered_data(self):
        from services.encryption_service import EncryptionService

        svc = EncryptionService()
        if not svc.available:
            pytest.skip("암호화 서비스 비활성화")

        with pytest.raises(ValueError):
            svc.decrypt("tampered_data_abc123")

    def test_hash_sensitive(self):
        from services.encryption_service import EncryptionService

        svc = EncryptionService()
        hash1 = svc.hash_sensitive('test@example.com', salt='salt1')
        hash2 = svc.hash_sensitive('test@example.com', salt='salt1')
        hash3 = svc.hash_sensitive('test@example.com', salt='salt2')

        assert hash1 == hash2       # 동일 입력 → 동일 해시
        assert hash1 != hash3       # 다른 salt → 다른 해시
        assert len(hash1) == 64     # SHA256 hex 길이


# ── F9-23: 요청 추적 미들웨어 ────────────────────────────────────────────────

class TestTracingMiddleware:

    def test_request_id_generation(self):
        from middleware.tracing import generate_request_id, get_request_id

        rid = generate_request_id()
        assert len(rid) == 36  # UUID4 포맷 (8-4-4-4-12)
        assert rid.count('-') == 4

    def test_get_request_id_default(self):
        from middleware.tracing import get_request_id
        # 컨텍스트 없으면 빈 문자열
        # (ContextVar 기본값)
        rid = get_request_id()
        assert isinstance(rid, str)
