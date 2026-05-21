"""utility 서브 라우트 패키지 — utility_routes.py에서 분리된 모듈들.

서브모듈:
- operations: 헬스/heartbeat/close/providers/ollama (8개 엔드포인트)
"""
from routes.utility import operations  # noqa: F401 — 부수효과 import
