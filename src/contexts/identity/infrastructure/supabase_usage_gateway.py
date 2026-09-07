"""IUsageGateway의 Supabase 구현 어댑터.

services/usage/usage_decorator.py의 @require_usage 데코레이터가
본 게이트웨이의 원자적 예약/멱등 환불 계약을 사용한다.
"""
from typing import Optional

from src.contexts.identity.application.ports import (
    IAccountRepository,
    IUsageGateway,
    QuotaReservation,
)
from src.shared.domain.value_objects import AccountId
from src.shared.infrastructure.supabase_client import (
    get_service_supabase,
    get_user_supabase,
)

class SupabaseUsageGateway(IUsageGateway):
    """Supabase RPC를 통한 원자적 사용량 예약/환불.

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
        """멱등 예약 원장에서 최근 일별 순사용량을 조회한다.

        Args:
            account_id: 특정 사용자 (None이면 모든 사용자 — admin 용도)
            days: 최근 N일

        Returns:
            list[dict] — [{'date': str, 'used_count': int}, ...]
        """
        if isinstance(days, bool) or not isinstance(days, int) or not 1 <= days <= 90:
            raise ValueError('days must be an integer between 1 and 90')

        client = (
            get_user_supabase()
            if account_id is not None
            else get_service_supabase()
        )
        if client is None:
            return []
        result = client.rpc(
            'get_daily_usage_history',
            {
                'p_user_id': str(account_id) if account_id is not None else None,
                'p_days': days,
            },
        ).execute()
        rows = getattr(result, 'data', None)
        if rows is None:
            return []
        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise RuntimeError('malformed usage history RPC response')
        return [
            {
                'date': row.get('date'),
                'used_count': int(row.get('used_count') or 0),
            }
            for row in rows
        ]

    def check_and_consume(self, account_id: AccountId, amount: int = 1) -> int:
        """사용량을 한 번의 원자적 RPC로 차감하고 남은 양을 반환."""
        return self.accounts.consume_quota_atomic(account_id, amount)

    def reserve(
        self,
        account_id: AccountId,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token_hash: str,
        amount: int = 1,
    ) -> QuotaReservation:
        """비용 작업 전 사용량을 멱등 예약한다."""
        return self.accounts.reserve_quota_atomic(
            account_id,
            idempotency_key,
            request_fingerprint,
            owner_token_hash,
            amount,
        )

    def refund(
        self,
        account_id: AccountId,
        reservation: QuotaReservation,
    ) -> int:
        """현재 요청이 소유한 예약을 멱등 환불한다."""
        return self.accounts.refund_quota_reservation(account_id, reservation)


__all__ = ["SupabaseUsageGateway"]
