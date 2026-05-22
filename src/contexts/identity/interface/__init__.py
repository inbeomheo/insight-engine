"""Identity & Access 인터페이스 계층 — HTTP/CLI/스케줄러 어댑터.

Phase 2-c 시점에는 비어있음.
다음 PR에서 다음 항목을 이관할 예정.

- `routes/auth/admin.py::_require_admin` → 데코레이터
- `services/usage/usage_decorator.py::require_usage` → 미들웨어
- `services/data/supabase_service.py::require_auth/optional_auth` → 인증 데코레이터
"""
