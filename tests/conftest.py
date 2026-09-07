"""pytest conftest.py - 테스트 실행 시 프로젝트 루트를 PYTHONPATH에 추가"""
import sys
import os
import shutil
import tempfile
from pathlib import Path

import pytest

# 가짜 공급자 호출 테스트가 개발자 자격 증명이나 외부 서버를 사용하지 않게 격리합니다.
os.environ['CLIPROXYAPI_BASE_URL'] = 'http://127.0.0.1:8317/v1'
os.environ['CLIPROXYAPI_API_KEY'] = 'test-gateway-key'


@pytest.fixture(autouse=True)
def isolated_gateway_configuration(monkeypatch):
    monkeypatch.setenv('CLIPROXYAPI_BASE_URL', 'http://127.0.0.1:8317/v1')
    monkeypatch.setenv('CLIPROXYAPI_API_KEY', 'test-gateway-key')

# 로컬 서버가 필요한 수동 브라우저 점검 스크립트는 단위 테스트 수집에서 제외한다.
collect_ignore = ["web_feature_test.py"]

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
