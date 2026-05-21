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

import logging
from datetime import date, datetime, timezone
from typing import Any, Optional

from src.contexts.identity.application.ports import IAccountRepository
from src.contexts.identity.domain.constants import DEFAULT_DAILY_LIMIT
from src.contexts.identity.domain.exceptions import QuotaExceeded
from src.contexts.identity.domain.user_account import (
    ApiKey,
    CreditBalance,
    RbacRole,
    UsageQuota,
    UserAccount,
)
from src.shared.domain.value_objects import AccountId

# 기존 `services/data/supabase_service`의 `ie_api_keys` 테이블은
# 단일 row에 provider별 컬럼(`gemini_key`, `deepseek_key` ...)을 가진 형태.
# Domain 모델은 ApiKey의 list이므로 컬럼명 → provider 매핑이 필요하다.
_API_KEY_COLUMN_TO_PROVIDER: dict[str, str] = {
    "gemini_key": "gemini",
    "deepseek_key": "deepseek",
    "zhipu_key": "zhipu",
    "openai_key": "openai",
    "anthropic_key": "anthropic",
    "openrouter_key": "openrouter",
    "youtube_key": "youtube",
    "supadata_key": "supadata",
}

logger = logging.getLogger(__name__)


# Supabase 비활성 / RPC 실패 시 사용량 차단을 풀어주는 개발 모드 sentinel.
# 운영 환경에서 이 값이 반환되면 경고 로그가 남으므로 사후 추적 가능하다.
# Phase 7 (Publishing 트랜잭션) 에서 RPC 트랜잭션 + 환불 로직과 통합 예정.
_UNLIMITED_DEV_QUOTA: int = 999


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

    def _get_admin_client(self) -> Optional[Any]:
        """Supabase service_role 클라이언트 (admin API용)."""
        from services.data.supabase_service import _get_admin_client

        return _get_admin_client()

    # ---- 내부 매핑 헬퍼 ----------------------------------------------------

    def _load_usage_quota(self, client: Any, user_id: str) -> UsageQuota:
        """`ie_usage` 테이블에서 사용량을 읽어 `UsageQuota`로 변환.

        스키마: `usage_count` (남은 횟수), `max_usage` (총 한도).
        도메인은 `used_today` (이미 사용한 횟수)로 표현하므로 변환 필요:
            used_today = max_usage - usage_count
        레코드가 없으면 기본값 (`UsageQuota.create_default()`).
        """
        try:
            res = (
                client.table("ie_usage")
                .select("usage_count, max_usage")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if not rows:
                return UsageQuota.create_default()
            row = rows[0]
            max_usage = int(row.get("max_usage") or DEFAULT_DAILY_LIMIT)
            remaining = int(row.get("usage_count") or 0)
            used_today = max(0, max_usage - remaining)
            return UsageQuota(daily_limit=max_usage, used_today=used_today)
        except Exception as exc:
            logger.warning(
                "ie_usage 조회 실패 — 기본값 사용 (user_id=%s, error=%s)",
                user_id,
                exc,
            )
            return UsageQuota.create_default()

    def _load_api_keys(self, client: Any, user_id: str) -> list[ApiKey]:
        """`ie_api_keys` 테이블에서 API 키 메타데이터를 읽어 ApiKey 목록 생성.

        평문은 도메인에 보관하지 않으므로 `masked_key`만 채운다.
        실제 평문 노출은 `IApiKeyVault.reveal()`을 통해서만 가능.
        """
        try:
            res = (
                client.table("ie_api_keys")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if not rows:
                return []
            row = rows[0]
            created_at = self._parse_timestamp(row.get("created_at"))
            keys: list[ApiKey] = []
            for column, provider in _API_KEY_COLUMN_TO_PROVIDER.items():
                encrypted = row.get(column)
                if not encrypted:
                    continue
                # 평문 복호화 금지 (도메인 보호) — 항상 마스킹된 형태로만.
                masked = self._mask(encrypted)
                try:
                    keys.append(
                        ApiKey(
                            provider=provider,
                            masked_key=masked,
                            label="default",
                            is_active=True,
                            created_at=created_at,
                        )
                    )
                except Exception as inner_exc:
                    logger.warning(
                        "ApiKey 변환 실패 (provider=%s, error=%s)",
                        provider,
                        inner_exc,
                    )
            return keys
        except Exception as exc:
            logger.warning(
                "ie_api_keys 조회 실패 (user_id=%s, error=%s)", user_id, exc
            )
            return []

    def _load_credits(self, client: Any, user_id: str) -> CreditBalance:
        """`ie_credits.balance` 읽기. 없으면 0."""
        try:
            res = (
                client.table("ie_credits")
                .select("balance")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if not rows:
                return CreditBalance()
            balance = int(rows[0].get("balance") or 0)
            return CreditBalance(balance=max(0, balance))
        except Exception as exc:
            logger.warning(
                "ie_credits 조회 실패 (user_id=%s, error=%s)", user_id, exc
            )
            return CreditBalance()

    def _load_roles(self, user_id: str) -> list[RbacRole]:
        """`is_admin()` 결과 + 기본 owner 역할 부여.

        현재 시스템은 admin/일반 사용자만 구분하므로,
        admin이면 `RbacRole('admin')`, 아니면 `RbacRole('owner')` (자기 소유).
        """
        try:
            from services.data.supabase_service import is_admin

            roles: list[RbacRole] = []
            if is_admin(user_id):
                roles.append(RbacRole(name="admin"))
            else:
                roles.append(RbacRole(name="owner"))
            return roles
        except Exception as exc:
            logger.warning(
                "is_admin 조회 실패 — owner로 기본값 (user_id=%s, error=%s)",
                user_id,
                exc,
            )
            return [RbacRole(name="owner")]

    @staticmethod
    def _mask(secret: str) -> str:
        """평문/암호문에 관계없이 마지막 4자리만 노출하는 마스킹."""
        if not secret or len(secret) <= 4:
            return "****"
        return "****" + secret[-4:]

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        """Supabase timestamp 문자열 → datetime (timezone-aware)."""
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, str) and value:
            try:
                # Supabase는 ISO8601 (예: '2026-05-21T13:00:00+00:00')
                # 'Z' suffix는 fromisoformat이 못 읽으므로 변환
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass
        return datetime.now(timezone.utc)

    @staticmethod
    def _extract_email_from_user(user_obj: Any) -> Optional[str]:
        """Supabase admin.get_user_by_id 응답에서 이메일 추출.

        응답 형식이 SDK 버전마다 다를 수 있어 다양한 경로를 시도한다.
        """
        if user_obj is None:
            return None
        # supabase-py: user_obj가 dict-like (User 모델)
        user = getattr(user_obj, "user", user_obj)
        email = getattr(user, "email", None)
        if email:
            return str(email)
        # dict-style fallback
        if isinstance(user, dict):
            return user.get("email")
        return None

    # ---- IAccountRepository 구현 ------------------------------------------

    def find_by_id(self, account_id: AccountId) -> Optional[UserAccount]:
        """주어진 `AccountId`로 UserAccount Aggregate를 조립하여 반환.

        다음 소스를 합성한다:
        1. `auth.users` (admin API) — 이메일
        2. `ie_usage` — UsageQuota
        3. `ie_api_keys` — ApiKey 목록 (masked만)
        4. `ie_credits` — CreditBalance
        5. `ie_admins` (`is_admin()`) — RbacRole

        Supabase 미설정 또는 사용자 미존재 시 None.
        """
        client = self._get_client()
        if client is None:
            logger.debug(
                "Supabase 비활성 — find_by_id 반환 None (account_id=%s)",
                account_id,
            )
            return None

        user_id = str(account_id)
        admin = self._get_admin_client()
        email: Optional[str] = None
        if admin is None:
            # service_role 키 미설정 — 운영에서는 모든 find_by_id가 실패하므로
            # 운영자가 즉시 인지할 수 있게 warning + 추적 가능한 메시지 로깅.
            # silent None은 운영 디버깅을 어렵게 하므로 명시적 경고로 처리.
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY 미설정 — find_by_id로 이메일 조회 불가. "
                "운영 환경이면 service_role 키를 설정해야 합니다 (user_id=%s)",
                user_id,
            )
        else:
            try:
                user_resp = admin.auth.admin.get_user_by_id(user_id)
                email = self._extract_email_from_user(user_resp)
            except Exception as exc:
                logger.warning(
                    "auth.admin.get_user_by_id 실패 (user_id=%s, error=%s)",
                    user_id,
                    exc,
                )
        if not email:
            # 이메일을 못 가져오면 Aggregate 불변식(__init__의 email 검증)을 만족 못 함.
            # 사용자 미존재이거나 admin 미설정이면 None 반환.
            logger.info(
                "UserAccount.find_by_id: 이메일 미확인 — None 반환 (user_id=%s)",
                user_id,
            )
            return None

        quota = self._load_usage_quota(client, user_id)
        credits = self._load_credits(client, user_id)
        api_keys = self._load_api_keys(client, user_id)
        roles = self._load_roles(user_id)

        return UserAccount(
            account_id=account_id,
            email=email,
            quota=quota,
            credits=credits,
            api_keys=api_keys,
            roles=roles,
        )

    # find_by_email 페이지네이션 한도 — 무한 루프 방지.
    # 1000 users/page × 10 pages = 최대 10,000명 스캔.
    # 이 한도를 넘는 운영 환경은 ie_usage_with_email 뷰 등 별도 인덱스 활용으로 전환 필요.
    _FIND_BY_EMAIL_PER_PAGE: int = 1000
    _FIND_BY_EMAIL_MAX_PAGES: int = 10

    def find_by_email(self, email: str) -> Optional[UserAccount]:
        """이메일로 UserAccount를 조회.

        Supabase는 직접적인 이메일 검색 API가 없으므로 admin
        `list_users(page, per_page)`를 페이지 단위로 순회 탐색한다.
        결과 발견 시 `find_by_id`에 위임하여 Aggregate를 조립한다.

        페이지네이션 정책:
        - per_page = `_FIND_BY_EMAIL_PER_PAGE` (1000)
        - 최대 페이지 = `_FIND_BY_EMAIL_MAX_PAGES` (10) → 최대 10,000명 스캔
        - 한도 초과 시 warning 로그 + None (fail-silent 방지)

        주의: 대규모 사용자 환경에서는 비효율 — Phase 5에서 `ie_usage_with_email`
        뷰 또는 별도 인덱스 활용으로 개선 예정.
        """
        if not email or "@" not in email:
            return None
        admin = self._get_admin_client()
        if admin is None:
            logger.warning(
                "SUPABASE_SERVICE_ROLE_KEY 미설정 — find_by_email로 조회 불가 (email=%s)",
                email,
            )
            return None

        target_email = email.strip().lower()
        for page in range(1, self._FIND_BY_EMAIL_MAX_PAGES + 1):
            try:
                users_resp = admin.auth.admin.list_users(
                    page=page, per_page=self._FIND_BY_EMAIL_PER_PAGE
                )
            except TypeError:
                # 일부 supabase-py 버전은 page/per_page kwarg를 받지 않음 — 1회만 호출
                try:
                    users_resp = admin.auth.admin.list_users()
                except Exception as exc:
                    logger.warning(
                        "auth.admin.list_users 실패 (email=%s, error=%s)",
                        email,
                        exc,
                    )
                    return None
                # 호환 모드 — 단일 페이지로 처리하고 종료
                users = users_resp if isinstance(users_resp, list) else getattr(
                    users_resp, "users", []
                )
                return self._scan_users_for_email(users or [], target_email)
            except Exception as exc:
                logger.warning(
                    "auth.admin.list_users 실패 (email=%s, page=%d, error=%s)",
                    email,
                    page,
                    exc,
                )
                return None

            # supabase-py 응답: list[User] 또는 obj.users
            users = users_resp if isinstance(users_resp, list) else getattr(
                users_resp, "users", []
            )
            users = list(users or [])
            if not users:
                # 빈 페이지 = 더 이상 사용자 없음
                return None

            found = self._scan_users_for_email(users, target_email)
            if found is not None:
                return found

            # 마지막 페이지 (per_page 미만 반환) — 더 순회할 필요 없음
            if len(users) < self._FIND_BY_EMAIL_PER_PAGE:
                return None

        # MAX_PAGES 초과 — 운영자가 인지하도록 warning
        logger.warning(
            "find_by_email 페이지 한도(%d) 초과 — 사용자를 못 찾았거나 환경이 너무 큼 (email=%s)",
            self._FIND_BY_EMAIL_MAX_PAGES,
            email,
        )
        return None

    def _scan_users_for_email(
        self, users: list, target_email: str
    ) -> Optional[UserAccount]:
        """단일 페이지 내에서 이메일 일치 사용자를 찾아 `find_by_id` 위임."""
        for user in users:
            u_email = getattr(user, "email", None) or (
                user.get("email") if isinstance(user, dict) else None
            )
            if u_email and str(u_email).strip().lower() == target_email:
                u_id = getattr(user, "id", None) or (
                    user.get("id") if isinstance(user, dict) else None
                )
                if u_id:
                    return self.find_by_id(AccountId(value=str(u_id)))
        return None

    def save(self, account: UserAccount) -> None:
        """UserAccount의 변경 사항을 저장소에 upsert.

        반영 항목:
        - `ie_usage` : usage_count (= daily_limit - used_today), max_usage
        - `ie_credits`: balance

        반영하지 않는 항목 (다른 책임):
        - `auth.users.email` — Identity Provider 영역, 직접 수정 금지
        - `api_keys` — `IApiKeyVault` 책임 (평문 보유)
        - `roles` (admin) — 별도 관리자 도구로 수정

        TODO(Phase 7 — 트랜잭션):
            현재 두 테이블 upsert가 별도 호출이라 부분 실패 가능. Supabase RPC
            (PL/pgSQL 트랜잭션)로 묶을 것.
        """
        client = self._get_client()
        if client is None:
            logger.debug(
                "Supabase 비활성 — save no-op (account_id=%s)",
                account.account_id,
            )
            return

        user_id = str(account.account_id)
        today = date.today().isoformat()

        # 1) ie_usage upsert
        try:
            quota = account.quota
            remaining = max(0, quota.daily_limit - quota.used_today)
            client.table("ie_usage").upsert(
                {
                    "user_id": user_id,
                    "usage_count": remaining,
                    "max_usage": quota.daily_limit,
                    "last_reset_date": today,
                }
            ).execute()
        except Exception as exc:
            logger.warning(
                "ie_usage upsert 실패 (user_id=%s, error=%s)", user_id, exc
            )

        # 2) ie_credits upsert
        try:
            client.table("ie_credits").upsert(
                {
                    "user_id": user_id,
                    "balance": account.credits.balance,
                }
            ).execute()
        except Exception as exc:
            logger.warning(
                "ie_credits upsert 실패 (user_id=%s, error=%s)", user_id, exc
            )

    def consume_quota_atomic(self, account_id: AccountId, amount: int = 1) -> int:
        """기존 `UsageService.decrement_atomic` 행동을 인터페이스 뒤로 캡슐화.

        Supabase RPC `decrement_usage_safe`를 호출하며, 다음 응답을 처리한다.

        - `{"success": true, "new_count": N}` → N 반환
        - `{"success": false, "reason": "no_usage_left"}` → `QuotaExceeded`
        - 그 외 예외/실패 → `_UNLIMITED_DEV_QUOTA` 반환 + warning 로그
          (개발 모드/장애 시 사용자가 막히지 않도록 fallback, 운영 추적은 로그로)

        주의: `amount > 1` 차감은 RPC가 지원하지 않으므로 반복 호출이 필요하다.
        본 메서드는 단일 차감(`amount=1`) 기준으로 동작하며,
        호출자는 amount만큼 반복 호출하거나 별도 RPC를 구현해야 한다.

        TODO(Phase 7 — Publishing 트랜잭션):
            - 차감과 콘텐츠 생성을 원자적으로 묶기 위해 `IUsageGateway.refund`
              구현 + Saga 패턴 도입.
            - `_UNLIMITED_DEV_QUOTA` fallback은 그때 제거 (장애 시 503 응답).
        """
        client = self._get_client()
        if client is None:
            # Supabase 비활성 (개발 모드) — 기본 허용 + 추적용 디버그 로그
            logger.debug(
                "Supabase 비활성 상태 — _UNLIMITED_DEV_QUOTA fallback "
                "(account_id=%s)",
                account_id,
            )
            return _UNLIMITED_DEV_QUOTA

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
        except Exception as exc:
            # 인프라 실패 시 기본 허용 — 운영 가시성을 위해 warning 로그 (with stack)
            # 한도 초과는 위에서 명시적 QuotaExceeded로 raise 되므로 여기 도달하지 않음.
            logger.warning(
                "consume_quota_atomic RPC 실패 — _UNLIMITED_DEV_QUOTA fallback "
                "(account_id=%s, error=%s)",
                account_id,
                exc,
                exc_info=True,
            )
            return _UNLIMITED_DEV_QUOTA


__all__ = [
    "SupabaseAccountRepository",
]
