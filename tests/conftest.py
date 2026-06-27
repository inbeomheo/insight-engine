"""pytest conftest.py - 테스트 실행 시 프로젝트 루트를 PYTHONPATH에 추가"""
import os
import sys
import shutil
import tempfile
from pathlib import Path

import pytest

_TEST_RUNTIME_ROOT = Path(
    tempfile.mkdtemp(prefix='insight-engine-test-runtime-')
)

# 로컬 .env가 production Redis 설정을 갖고 있어도 테스트는 외부 Redis 없이 격리 실행한다.
os.environ.setdefault('APP_DATA_DIR', str(_TEST_RUNTIME_ROOT / 'app_data'))
os.environ.setdefault('APP_CACHE_DIR', str(_TEST_RUNTIME_ROOT / 'app_cache'))
os.environ.setdefault(
    'AI_CACHE_DB',
    str(_TEST_RUNTIME_ROOT / 'app_cache' / 'ai_cache.db'),
)
os.environ.setdefault('RATE_LIMIT_ENABLED', 'false')
os.environ.setdefault('REDIS_URL', 'memory://')
os.environ.setdefault('PUBLISH_QUEUE_BACKEND', 'file')
os.environ.setdefault('SCHEDULER_ENABLED', 'false')
os.environ.setdefault('ZAI_API_KEY', '')

# 프로젝트 루트 (tests 폴더의 부모)를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


@pytest.fixture
def tmp_path():
    """Windows Python 3.13 + pytest 9 호환 tmp_path 대체.

    pytest 내장 tmp_path가 pathlib.resolve()에서 Windows reparse point
    OSError [WinError 448]을 발생시키는 문제를 우회한다.
    """
    d = Path(tempfile.mkdtemp())
    yield d
    shutil.rmtree(d, ignore_errors=True)
