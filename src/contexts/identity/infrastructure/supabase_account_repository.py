"""Supabase 기반 `IAccountRepository` 구현.

내부적으로 `services/data/supabase_service.get_supabase()`를 **lazy import**해서
기존 클라이언트 팩토리를 재사용한다. Phase 2 마이그레이션 완료 후
Supabase 클라이언트는 `src/shared/infrastructure/`로 이동 예정이다.

현재 상태 (Phase 2-c)
---------------------
- `consume_quota_atomic` : 실제 동작 (RPC `decrement_usage_safe` 호출)
- 나머지 메서드          : `NotImplementedError` (인터페이스만 정의)

Phase 2-d/e/f에서 `find_by_id`, `find_by_email`, `save`를 본격 구현하면서
기존 `services/data/*` 호출처를 새 인터페이스로 마이그레이션한다.
"""

from __future__ import annotations

from typing import Any, Optional

from src.contexts.identity.application.ports import IAccountRepository
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.contexts.identity.domain.user_account import UserAccount
from src.shared.domain.value_objects import AccountId


class SupabaseAccountRepository(IAccountRepository):
    """Supabase를 백엔드로 사용하는 `IAccountRepository` 구현.

    내부적으로 `services/data/supabase_service.get_supabase()`를 lazy import하여
    기존 클라이언트 팩토리를 재사용한다. Phase 2 마이그레이션 완료 후
    Supabase 클라이언트는 `shared/infrastructure/`로 이동 예정.
    """

    # ---- 내부 헬퍼 --------------------------------------------------------

    def _get_client(self) -> Optional[Any]:
        """Supabase 클라이언트를 lazy import로 획득.

        Supabase 미설정(개발 모드) 시 None 반환.
        """
        # lazy import — 본 클래스를 import해도 supabase 미설치 환경에서 폭발하지 않도록
        from services.data.supabase_service import get_supabase, is_supabase_enabled

        if not is_supabase_enabled():
            return None
        return get_supabase()

    # ---- IAccountRepository 구현 ------------------------------------------

    def find_by_id(self, account_id: AccountId) -> Optional[UserAccount]:
        """주어진 `AccountId`로 UserAccount를 조회.

        Phase 2 다음 단계에서 완성 — 현재는 인터페이스만 정의.
        본격 구현 시 `auth.users` + `ie_usage` + `ie_api_keys` + `ie_admins`를
        조인하여 Aggregate를 복원한다.
        """
        raise NotImplementedError(
            "Phase 2 다음 단계에서 완성 — auth.users/ie_usage/ie_api_keys 조인 필요"
        )

    def find_by_email(self, email: str) -> Optional[UserAccount]:
        """이메일로 UserAccount를 조회."""
        raise NotImplementedError("Phase 2 다음 단계에서 완성")

    def save(self, account: UserAccount) -> None:
        """UserAccount의 변경 사항을 저장소에 반영."""
        raise NotImplementedError("Phase 2 다음 단계에서 완성")

    def consume_quota_atomic(self, account_id: AccountId, amount: int = 1) -> int:
        """기존 `UsageService.decrement_atomic` 행동을 인터페이스 뒤로 캡슐화.

        Supabase RPC `decrement_usage_safe`를 호출하며, 다음 응답을 처리한다.

        - `{"success": true, "new_count": N}` → N 반환
        - `{"success": false, "reason": "no_usage_left"}` → `QuotaExceeded`
        - 그 외 예외/실패 → 기존 동작 모방하여 999 반환 (개발 모드 등에서 차단 X)

        주의: `amount > 1` 차감은 RPC가 지원하지 않으므로 반복 호출이 필요하다.
        본 메서드는 단일 차감(`amount=1`) 기준으로 동작하며,
        호출자는 amount만큼 반복 호출하거나 별도 RPC를 구현해야 한다.
        """
        client = self._get_client()
        if client is None:
            # Supabase 비활성 (개발 모드) — 기본 허용
            return 999

        try:
            res = client.rpc(
                "decrement_usage_safe",
                {"p_user_id": str(account_id)},
            ).execute()
            data = getattr(res, "data", None)

            if isinstance(data, dict):
                if data.get("success"):
                    return int(data.get("new_count", 0))
                if data.get("reason") == "no_usage_left":
                    raise QuotaExceeded(
                        f"daily quota exceeded for {account_id}"
                    )

            # 응답 형식이 예상과 다른 경우 — 안전을 위해 한도 초과 처리
            raise QuotaExceeded(
                f"decrement_usage_safe returned unexpected payload: {data!r}"
            )
        except QuotaExceeded:
            raise
        except Exception:
            # 기존 동작 모방: 인프라 실패 시 기본 허용 (운영 가시성은 별도 로깅 필요)
            # TODO(Phase 2 후속): 여기서 silent 999 반환은 위험 — 로깅/모니터링 추가
            return 999


__all__ = [
    "SupabaseAccountRepository",
]
