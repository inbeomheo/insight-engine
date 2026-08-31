"""pytest conftest.py - 테스트 실행 시 프로젝트 루트를 PYTHONPATH에 추가"""
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# extensions.limiter와 외부 통합은 모듈 import 시 환경을 읽는다. 테스트가
# 개발/운영 .env에 의존하지 않도록 앱 import 전에 명시적으로 중립화한다.
os.environ.setdefault('RATELIMIT_STORAGE_URI', 'memory://')
os.environ.setdefault('RATE_LIMIT_ENABLED', 'false')
os.environ['CLIPROXY_BASE_URL'] = 'http://cli-proxy-api:8317/v1'
os.environ['CLIPROXY_API_KEY'] = 'test-cliproxy-key'
for _external_env in (
    'SUPPORT_GITHUB_TOKEN', 'GITHUB_TOKEN',
    'SUPPORT_GITHUB_REPO', 'GITHUB_REPOSITORY',
):
    os.environ[_external_env] = ''

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
