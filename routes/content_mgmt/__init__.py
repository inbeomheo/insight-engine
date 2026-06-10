"""content_mgmt 서브패키지 — content_mgmt_routes.py에서 분리된 모듈들.

각 서브모듈이 content_mgmt_bp 데코레이터로 라우트를 등록한다.

서브모듈:
- backup_io: F8-22 백업/복원 + F8-23 데이터 가져오기/내보내기
"""
from routes.content_mgmt import (  # noqa: F401 — 부수효과 import
    backup_io,
)
