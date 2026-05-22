"""IUsageGateway의 Supabase 구현 어댑터.

현재 services/usage/usage_decorator.py의 @require_usage 데코레이터가
Phase 2 다음 PR에서 본 게이트웨이를 통해 동작하도록 마이그레이션 예정.
"""
import logging
from typing import Optional

from src.contexts.identity.application.ports import IUsageGateway, IAccountRepository
from src.shared.domain.value_objects import AccountId
from src.shared.infrastructure.supabase_client import get_supabase

logger = logging.getLogger(__name__)


class SupabaseUsageGateway(IUsageGateway):
    """Supabase RPC decrement_usage_safe를 통한 원자적 사용량 차감.

    내부적으로 IAccountRepository.consume_quota_atomic으로 위임.
    """

    _TABLE = "ie_usage"

    def __init__(self, accounts: IAccountRepository) -> None:
        self.accounts = accounts

    def daily_usage_history(
        self,
        account_id: Optional[AccountId] = None,
        days: int = 7,
    ) -> list[dict]:
        """일일 사용량 raw 조회.

        Args:
            account_id: 특정 사용자 (None이면 모든 사용자 — admin 용도)
            days: 최근 N일

        Returns:
            list[dict] — [{'date': str, 'used_count': int, ...}, ...]
            Supabase 비활성/예외 시 빈 리스트.
        """
        from datetime import datetime, timedelta, timezone

        client = get_supabase()
        if client is None:
            return []
        try:
            since_date = (
                datetime.now(timezone.utc) - timedelta(days=days)
            ).isoformat()[:10]
            query = (
                client.table(self._TABLE)
                .select("date,used_count")
                .gte("date", since_date)
                .order("date", desc=False)
            )
            if account_id is not None:
                query = query.eq("user_id", str(account_id))
            result = query.execute()
            return result.data or []
        except Exception as exc:
            logger.error("일일 사용량 조회 실패: %s", exc)
            return []

    def check_and_consume(self, account_id: AccountId, amount: int = 1) -> int:
        """남은 사용량 반환. 부족 시 QuotaExceeded.

        Note: amount > 1은 현재 RPC가 지원하지 않으므로 반복 호출 (TODO).
        """
        if amount == 1:
            return self.accounts.consume_quota_atomic(account_id, 1)
        # amount > 1: RPC를 amount번 반복 (트랜잭션 미보장)
        remaining = 0
        for _ in range(amount):
            remaining = self.accounts.consume_quota_atomic(account_id, 1)
        return remaining

    def refund(self, account_id: AccountId, amount: int = 1) -> None:
        """생성 실패 시 사용량 환불.

        현재 미구현 — Supabase에 increment_usage_safe RPC 추가 후 Phase 7에서.
        """
        logger.warning(
            "SupabaseUsageGateway.refund: 미구현 (account=%s, amount=%d) — Phase 7에서 트랜잭션 도입과 함께 구현 예정",
            account_id, amount
        )


__all__ = ["SupabaseUsageGateway"]
