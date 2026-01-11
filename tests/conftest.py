"""pytest conftest.py - 테스트 실행 시 프로젝트 루트를 PYTHONPATH에 추가"""
import sys
from pathlib import Path

# 프로젝트 루트 (tests 폴더의 부모)를 sys.path에 추가
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
