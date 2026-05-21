"""auth 서브 라우트 패키지 — auth_routes.py에서 분리된 모듈들.

각 서브모듈은 auth_bp 데코레이터로 라우트를 등록.

서브모듈:
- admin: 관리자 라우트 (6개 엔드포인트)
- user_settings: API 키 / 커스텀 스타일 / 사용량 (6개 엔드포인트)
- history_account: 히스토리 + 프로필/비밀번호/계정 삭제 (7개 엔드포인트)

테스트 patch 호환을 위해 새 모듈들은 `routes.auth_routes` namespace를 통해
supabase 함수에 접근한다 (`_ar.is_admin(...)` 형식).
"""
from routes.auth import admin, history_account, user_settings  # noqa: F401 — 부수효과 import
