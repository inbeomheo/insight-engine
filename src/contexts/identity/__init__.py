"""Identity & Access Bounded Context.

책임: 인증, 어카운트, API 키, 사용량 쿼터, 크레딧, RBAC를 단일 권위로 관리.

외부에 노출되는 진입점은 `application/ports.py`의 인터페이스이며,
다른 BC는 절대로 `domain/` 또는 `infrastructure/`를 직접 import하지 않는다.

추가로 라우트가 즉시 사용할 수 있는 편의 함수 몇 가지를 제공한다:
- `fetch_daily_usage_history(account_id, days)` — 일일 사용량 raw 조회

참고: `README.md` (유비쿼터스 언어 + 의존 방향).
"""
from __future__ import annotations


def fetch_daily_usage_history(
    account_id: str | None = None, days: int = 7
) -> list[dict]:
    """편의 함수 — `SupabaseUsageGateway.daily_usage_history` 단축 호출.

    Args:
        account_id: 특정 사용자 (None이면 전체 — admin 대시보드)
        days: 최근 N일

    Returns:
        list[dict] — [{'date': str, 'used_count': int, ...}, ...]
    """
    from src.contexts.identity.infrastructure.supabase_account_repository import (
        SupabaseAccountRepository,
    )
    from src.contexts.identity.infrastructure.supabase_usage_gateway import (
        SupabaseUsageGateway,
    )
    from src.shared.domain.value_objects import AccountId

    gateway = SupabaseUsageGateway(SupabaseAccountRepository())
    aid = AccountId(value=account_id) if account_id else None
    return gateway.daily_usage_history(aid, days)


__all__ = ["fetch_daily_usage_history"]
