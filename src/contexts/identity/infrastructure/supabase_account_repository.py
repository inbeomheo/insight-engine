"""Supabase 기반 `IAccountRepository` 구현.

내부적으로 `src.shared.infrastructure.supabase_client`를 **lazy import**해서
요청별 JWT 또는 서버 전용 클라이언트를 사용한다.

현재 구현 범위
-------------
- `find_by_id` / `find_by_email` / `save` : 계정 aggregate 조회·저장
- `consume_quota_atomic` : 레거시 단일 차감 RPC
- `reserve_quota_atomic` / `refund_quota_reservation` : 비용 작업용 멱등 원장 RPC

아직 남은 레거시 직접 호출은 점진적으로 이 ACL 뒤로 옮긴다.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.contexts.identity.application.ports import (
    IAccountRepository,
    QuotaReservation,
    QuotaReservationConflict,
)
from src.contexts.identity.domain.constants import DEFAULT_DAILY_LIMIT
from src.contexts.identity.domain.exceptions import (
    QuotaBackendUnavailable,
    QuotaExceeded,
)
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


# Supabase 비활성 로컬 개발 모드에서만 사용하는 무제한 sentinel.
_UNLIMITED_DEV_QUOTA: int = 999


class AmbiguousQuotaReservation(QuotaBackendUnavailable):
    """예약 커밋 여부와 즉시 보상 여부를 모두 확인하지 못한 상태.

    ``reservation``은 DB 예약 ID를 모르는 상태에서도 같은 멱등 키와 소유
    토큰으로 다음 요청이 보상 환불을 재시도할 수 있게 하는 합성 예약이다.
    """

    def __init__(self, message: str, reservation: QuotaReservation) -> None:
        super().__init__(message)
        self.reservation = reservation


class SupabaseAccountRepository(IAccountRepository):
    """Supabase를 백엔드로 사용하는 `IAccountRepository` 구현.

    내부적으로 공유 Supabase 클라이언트를 lazy import하며, 비용 RPC에는
    요청별 검증 JWT 또는 서버 전용 service-role 클라이언트만 사용한다.
    """

    # ---- 내부 헬퍼 --------------------------------------------------------

    def _get_client(self) -> Optional[Any]:
        """Supabase 클라이언트를 lazy import로 획득.

        Supabase 미설정(개발 모드) 시 None 반환.
        """
        # lazy import — 본 클래스를 import해도 supabase 미설치 환경에서 폭발하지 않도록
        from src.shared.infrastructure.supabase_client import (
            get_user_supabase,
            is_supabase_enabled,
        )

        if not is_supabase_enabled():
            return None
        return get_user_supabase()

    def _get_admin_client(self) -> Optional[Any]:
        """Supabase service_role 클라이언트 (admin API용)."""
        from src.shared.infrastructure.supabase_client import get_service_supabase

        return get_service_supabase()

    def _get_usage_rpc_client(self, account_id: AccountId) -> Optional[Any]:
        """Return the server-only accounting client for a validated account.

        Reservation RPCs are not exposed to ``authenticated`` because arbitrary
        direct calls could amplify the durable ledger. Inside a Flask request we
        still require ``require_auth``'s validated JWT context and an exact account
        match before using the service-role client. Background reconciliation has
        no request context and is allowed only with the explicit server secret.
        """
        from src.shared.infrastructure.supabase_client import (
            get_service_supabase,
            get_validated_request_access_token,
            is_supabase_enabled,
        )

        if not is_supabase_enabled():
            return None

        from flask import g, has_request_context

        if has_request_context():
            access_token = get_validated_request_access_token()
            request_user_id = g.get('user_id')
            if not access_token:
                raise QuotaBackendUnavailable(
                    'usage RPC requires a validated request JWT'
                )
            if not request_user_id or request_user_id != str(account_id):
                raise QuotaBackendUnavailable(
                    'usage RPC account does not match the authenticated request'
                )

        # The database grants these mutation RPCs only to service_role.
        try:
            client = get_service_supabase()
            if client is not None:
                return client
        except Exception as exc:
            raise QuotaBackendUnavailable(
                'service-role usage RPC client is unavailable'
            ) from exc
        raise QuotaBackendUnavailable(
            'usage RPC requires a service-role client'
        )

    # ---- 내부 매핑 헬퍼 ----------------------------------------------------

    def _load_usage_quota(self, client: Any, user_id: str) -> UsageQuota:
        """검증된 `get_usage_safe` RPC 응답을 `UsageQuota`로 변환.

        스키마: `usage_count` (남은 횟수), `max_usage` (총 한도).
        도메인은 `used_today` (이미 사용한 횟수)로 표현하므로 변환 필요:
            used_today = max_usage - usage_count
        레코드가 없으면 기본값 (`UsageQuota.create_default()`).
        """
        try:
            res = client.rpc(
                "get_usage_safe",
                {"p_user_id": user_id},
            ).execute()
            row = getattr(res, "data", None)
            if not isinstance(row, dict):
                raise RuntimeError("get_usage_safe returned malformed data")
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
        4. Billing BC 미연결 기본값 — CreditBalance(0)
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
                "Supabase secret/service_role 키 미설정 — find_by_id로 이메일 조회 "
                "불가 (user_id=%s)",
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
        api_keys = self._load_api_keys(client, user_id)
        roles = self._load_roles(user_id)

        return UserAccount(
            account_id=account_id,
            email=email,
            quota=quota,
            # Billing BC와 원장이 구현되기 전에는 잔액을 영속화했다고 가장하지
            # 않는다. 사용자 JWT로 직접 쓸 수 있는 임시 balance 테이블도 만들지 않는다.
            credits=CreditBalance(),
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
                "Supabase secret/service_role 키 미설정 — find_by_email로 조회 불가 "
                "(email=%s)",
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
        - `set_usage_quota_admin` RPC: usage_count (= daily_limit - used_today),
          max_usage. 사용자 JWT의 직접 테이블 쓰기는 허용하지 않음.

        반영하지 않는 항목 (다른 책임):
        - `auth.users.email` — Identity Provider 영역, 직접 수정 금지
        - `api_keys` — `IApiKeyVault` 책임 (평문 보유)
        - `roles` (admin) — 별도 관리자 도구로 수정
        - `credits` — Billing BC/원장이 아직 없어 저장하지 않음
        """
        client = self._get_admin_client()
        if client is None:
            logger.debug(
                "Supabase 비활성 — save no-op (account_id=%s)",
                account.account_id,
            )
            return

        user_id = str(account.account_id)

        # quota는 사용자가 Data API 테이블을 직접 덮어쓸 수 없도록
        # service-role 전용 검증 RPC로만 저장한다.
        try:
            quota = account.quota
            remaining = max(0, quota.daily_limit - quota.used_today)
            result = client.rpc(
                "set_usage_quota_admin",
                {
                    "p_user_id": user_id,
                    "p_usage_count": remaining,
                    "p_max_usage": quota.daily_limit,
                },
            ).execute()
            payload = getattr(result, "data", None)
            if not isinstance(payload, dict) or payload.get("success") is not True:
                raise RuntimeError(
                    f"set_usage_quota_admin returned malformed data: {payload!r}"
                )
        except Exception as exc:
            logger.warning(
                "quota 관리자 RPC 저장 실패 (user_id=%s, error=%s)", user_id, exc
            )

    def consume_quota_atomic(self, account_id: AccountId, amount: int = 1) -> int:
        """검증된 요청 주체의 사용량을 한 번의 RPC로 원자적 차감.

        Supabase RPC `decrement_usage_safe(p_user_id, p_amount)`를 호출하며,
        다음 응답을 처리한다.

        - `{"success": true, "new_count": N}` → N 반환
        - `{"success": false, "reason": "no_usage_left"}` → `QuotaExceeded`
        - 그 외 예외/실패(인프라 장애) → `QuotaBackendUnavailable`. 운영 환경에서
          차감 확인 없이 비용 작업을 반복 허용하지 않는 fail-closed 정책이다.

        신규 비용 작업은 이 레거시 API 대신 멱등 예약/환불 원장
        (`reserve_quota_atomic` / `refund_quota_reservation`)을 사용한다.
        """
        if (
            isinstance(amount, bool)
            or not isinstance(amount, int)
            or amount <= 0
        ):
            raise ValueError("amount must be a positive integer")

        client = self._get_usage_rpc_client(account_id)
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
                {"p_user_id": str(account_id), "p_amount": amount},
            ).execute()
            data = getattr(res, "data", None)

            if isinstance(data, dict):
                if data.get("success"):
                    return int(data.get("new_count", 0))
                if data.get("reason") == "no_usage_left":
                    raise QuotaExceeded(
                        f"daily quota exceeded for {account_id}"
                    )

            # 알 수 없는 응답을 실제 한도 초과와 혼동하면 차감 확인 없이 정상
            # 결과를 반환할 수 있다. 인프라 계약 위반으로 분류해 fail-closed한다.
            raise QuotaBackendUnavailable(
                f"decrement_usage_safe returned unexpected payload: {data!r}"
            )
        except (QuotaExceeded, QuotaBackendUnavailable):
            raise
        except Exception as exc:
            logger.error(
                "consume_quota_atomic RPC 실패 — 비용 요청을 안전하게 차감할 수 없음 "
                "(account_id=%s, error=%s)",
                account_id,
                exc,
                exc_info=True,
            )
            raise QuotaBackendUnavailable(
                f"usage accounting unavailable for {account_id}"
            ) from exc

    @staticmethod
    def _execute_idempotent_rpc(
        client: Any,
        function_name: str,
        params: dict[str, Any],
    ) -> Any:
        """응답 유실 가능성이 있는 멱등 RPC를 같은 인자로 한 번 재시도한다.

        POST RPC는 서버 커밋 뒤 응답만 유실될 수 있다. 예약/환불 RPC는 DB 원장의
        고유 키와 소유 토큰으로 재실행이 멱등하므로, 네트워크 예외에 한해서만 같은
        호출을 한 번 더 수행한다. 정상 응답이지만 계약 밖 payload인 경우에는 재시도
        하지 않고 호출자가 backend-unavailable로 분류한다.
        """
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                return client.rpc(function_name, params).execute()
            except Exception as exc:
                last_error = exc
                if attempt == 0:
                    logger.warning(
                        "%s 응답 확인 실패 — 동일 멱등 키로 1회 재시도 (error=%s)",
                        function_name,
                        exc,
                    )
                    continue
        assert last_error is not None  # 두 시도 모두 실패한 경우에만 도달
        raise last_error

    @classmethod
    def _compensate_ambiguous_reservation(
        cls,
        client: Any,
        *,
        account_id: AccountId,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token_hash: str,
    ) -> bool:
        """예약 응답을 확정할 수 없으면 같은 소유 토큰으로 보상 환불.

        예약이 실제로 없다는 명시 응답도 안전한 보상 완료다. 그 외 계약 밖
        응답이나 두 번의 네트워크 실패는 ``False``를 반환해 호출자가 합성
        예약을 영속 재시도 원장에 남기게 한다.
        """
        params = {
            "p_user_id": str(account_id),
            "p_idempotency_key": idempotency_key,
            "p_request_fingerprint": request_fingerprint,
            "p_owner_token_hash": owner_token_hash,
        }
        try:
            response = cls._execute_idempotent_rpc(
                client,
                "refund_usage_reservation_safe",
                params,
            )
            data = getattr(response, "data", None)
            if isinstance(data, dict):
                new_count = data.get("new_count")
                if (
                    data.get("success") is True
                    and isinstance(new_count, int)
                    and not isinstance(new_count, bool)
                    and new_count >= 0
                ):
                    return True
                if (
                    data.get("success") is False
                    and data.get("reason") == "reservation_not_found"
                ):
                    return True
            logger.error(
                "모호한 사용량 예약 보상 환불이 계약 밖 응답을 반환함 "
                "(account_id=%s, payload=%r)",
                account_id,
                data,
            )
            return False
        except Exception as exc:
            logger.error(
                "모호한 사용량 예약 보상 환불 응답 확인 실패 "
                "(account_id=%s, error=%s)",
                account_id,
                exc,
            )
            return False

    @staticmethod
    def _make_ambiguous_reservation(
        *,
        account_id: AccountId,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token_hash: str,
        amount: int,
    ) -> QuotaReservation:
        """DB ID를 모르는 예약을 안정적인 로컬 합성 ID로 표현한다."""
        synthetic_material = b'\x00'.join((
            str(account_id).encode('utf-8'),
            idempotency_key.encode('ascii'),
            request_fingerprint.encode('ascii'),
            owner_token_hash.encode('ascii'),
        ))
        synthetic_id = 'ambiguous:' + hashlib.sha256(synthetic_material).hexdigest()
        return QuotaReservation(
            reservation_id=synthetic_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            owner_token_hash=owner_token_hash,
            amount=amount,
            # 실제 값은 응답 유실로 알 수 없다. 이 값들은 환불 RPC 입력에
            # 쓰이지 않으며, 보수적인 표시값만 제공한다.
            remaining=0,
            max_usage=DEFAULT_DAILY_LIMIT,
            owned=True,
            replayed=True,
        )

    @classmethod
    def _raise_ambiguous_reservation(
        cls,
        *,
        account_id: AccountId,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token_hash: str,
        amount: int,
        cause: Exception | None = None,
    ) -> None:
        reservation = cls._make_ambiguous_reservation(
            account_id=account_id,
            idempotency_key=idempotency_key,
            request_fingerprint=request_fingerprint,
            owner_token_hash=owner_token_hash,
            amount=amount,
        )
        error = AmbiguousQuotaReservation(
            f"usage reservation outcome is ambiguous for {account_id}",
            reservation,
        )
        if cause is None:
            raise error
        raise error from cause

    def reserve_quota_atomic(
        self,
        account_id: AccountId,
        idempotency_key: str,
        request_fingerprint: str,
        owner_token_hash: str,
        amount: int = 1,
    ) -> QuotaReservation:
        """비용 작업 전에 사용량을 원자적·멱등하게 예약한다.

        DB 응답 유실 시 같은 키/소유 토큰으로 한 번 재시도한다. 첫 호출이 이미
        커밋됐으면 RPC가 기존 예약을 반환하므로 추가 차감되지 않는다.
        """
        if amount <= 0:
            raise ValueError("amount must be positive")

        client = self._get_usage_rpc_client(account_id)
        if client is None:
            return QuotaReservation(
                reservation_id="local-unlimited",
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                owner_token_hash=owner_token_hash,
                amount=amount,
                remaining=_UNLIMITED_DEV_QUOTA,
                max_usage=_UNLIMITED_DEV_QUOTA,
                owned=False,
                replayed=False,
            )

        params = {
            "p_user_id": str(account_id),
            "p_idempotency_key": idempotency_key,
            "p_request_fingerprint": request_fingerprint,
            "p_owner_token_hash": owner_token_hash,
            "p_amount": amount,
        }
        try:
            response = self._execute_idempotent_rpc(
                client,
                "reserve_usage_safe",
                params,
            )
            data = getattr(response, "data", None)

            if isinstance(data, dict):
                if data.get("success") is True:
                    reservation_id = data.get("reservation_id")
                    new_count = data.get("new_count")
                    max_usage = data.get("max_usage")
                    owned = data.get("owned")
                    replayed = data.get("replayed")
                    if (
                        isinstance(reservation_id, str)
                        and reservation_id
                        and isinstance(new_count, int)
                        and not isinstance(new_count, bool)
                        and isinstance(max_usage, int)
                        and not isinstance(max_usage, bool)
                        and isinstance(owned, bool)
                        and isinstance(replayed, bool)
                    ):
                        return QuotaReservation(
                            reservation_id=reservation_id,
                            idempotency_key=idempotency_key,
                            request_fingerprint=request_fingerprint,
                            owner_token_hash=owner_token_hash,
                            amount=amount,
                            remaining=new_count,
                            max_usage=max_usage,
                            owned=owned,
                            replayed=replayed,
                        )
                if data.get("reason") == "no_usage_left":
                    raise QuotaExceeded(
                        f"daily quota exceeded for {account_id}"
                    )
                if data.get("reason") == "idempotency_conflict":
                    raise QuotaReservationConflict(
                        "idempotency key was reused with a different request"
                    )
                if data.get("reason") == "idempotency_replay":
                    reservation_id = data.get("reservation_id")
                    new_count = data.get("new_count")
                    max_usage = data.get("max_usage")
                    if (
                        isinstance(reservation_id, str)
                        and reservation_id
                        and isinstance(new_count, int)
                        and not isinstance(new_count, bool)
                        and isinstance(max_usage, int)
                        and not isinstance(max_usage, bool)
                    ):
                        return QuotaReservation(
                            reservation_id=reservation_id,
                            idempotency_key=idempotency_key,
                            request_fingerprint=request_fingerprint,
                            owner_token_hash=owner_token_hash,
                            amount=amount,
                            remaining=new_count,
                            max_usage=max_usage,
                            owned=False,
                            replayed=True,
                        )

            # 예상 밖 payload는 성공/한도 초과로 추측하지 않는다.
            compensated = self._compensate_ambiguous_reservation(
                client,
                account_id=account_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                owner_token_hash=owner_token_hash,
            )
            if not compensated:
                self._raise_ambiguous_reservation(
                    account_id=account_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    owner_token_hash=owner_token_hash,
                    amount=amount,
                )
            raise QuotaBackendUnavailable(
                f"reserve_usage_safe returned unexpected payload: {data!r}"
            )
        except (QuotaExceeded, QuotaReservationConflict, QuotaBackendUnavailable):
            raise
        except Exception as exc:
            compensated = self._compensate_ambiguous_reservation(
                client,
                account_id=account_id,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                owner_token_hash=owner_token_hash,
            )
            if not compensated:
                self._raise_ambiguous_reservation(
                    account_id=account_id,
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    owner_token_hash=owner_token_hash,
                    amount=amount,
                    cause=exc,
                )
            logger.error(
                "reserve_usage_safe RPC 실패 (account_id=%s, error=%s)",
                account_id,
                exc,
                exc_info=True,
            )
            raise QuotaBackendUnavailable(
                f"usage reservation unavailable for {account_id}"
            ) from exc

    def refund_quota_reservation(
        self,
        account_id: AccountId,
        reservation: QuotaReservation,
    ) -> int:
        """현재 요청이 소유한 예약만 원자적·멱등하게 환불한다."""
        if not reservation.owned:
            # 같은 멱등 키를 별도 요청이 재생한 경우 기존 성공 요청의 예약을
            # 되돌리면 안 된다. DB 호출 자체를 생략해 소유 경계를 명확히 한다.
            return reservation.remaining

        client = self._get_usage_rpc_client(account_id)
        if client is None:
            return _UNLIMITED_DEV_QUOTA

        params = {
            "p_user_id": str(account_id),
            "p_idempotency_key": reservation.idempotency_key,
            "p_request_fingerprint": reservation.request_fingerprint,
            "p_owner_token_hash": reservation.owner_token_hash,
        }
        try:
            response = self._execute_idempotent_rpc(
                client,
                "refund_usage_reservation_safe",
                params,
            )
            data = getattr(response, "data", None)
            if isinstance(data, dict) and data.get("success") is True:
                new_count = data.get("new_count")
                if (
                    isinstance(new_count, int)
                    and not isinstance(new_count, bool)
                    and new_count >= 0
                ):
                    return new_count

            # 합성 ID는 예약 RPC 응답을 받지 못해 실제 DB ID를 모르는 작업에만
            # 사용한다. 같은 멱등 키/소유 토큰으로 조회했는데 행이 없으면 예약
            # 자체가 커밋되지 않은 것이므로 안전한 no-op이다. 실제 예약 ID를 아는
            # 일반 환불의 not-found는 원장 손상일 수 있어 계속 fail-closed한다.
            if (
                isinstance(data, dict)
                and data.get("success") is False
                and data.get("reason") == "reservation_not_found"
                and reservation.reservation_id.startswith("ambiguous:")
            ):
                return reservation.remaining

            raise QuotaBackendUnavailable(
                "refund_usage_reservation_safe returned unexpected payload: "
                f"{data!r}"
            )
        except QuotaBackendUnavailable:
            raise
        except Exception as exc:
            logger.error(
                "refund_usage_reservation_safe RPC 실패 (account_id=%s, error=%s)",
                account_id,
                exc,
                exc_info=True,
            )
            raise QuotaBackendUnavailable(
                f"usage refund unavailable for {account_id}"
            ) from exc

    def _read_remaining_quota(
        self, client: Any, account_id: AccountId
    ) -> Optional[int]:
        """ie_usage에서 현재 잔여 횟수(usage_count)를 읽어 반환한다 (차감하지 않음).

        장애 폴백 경로에서 '차감 생략' 정책을 충실히 구현하기 위한 읽기 전용 조회다.
        원자적 차감 RPC가 실패했을 때 사용자의 실제(미차감) 잔여 횟수를 그대로
        보고하는 데 쓰며, 읽기 자체가 실패하거나 행이 없으면 None을 반환한다.
        """
        try:
            res = (
                client.table("ie_usage")
                .select("usage_count")
                .eq("user_id", str(account_id))
                .limit(1)
                .execute()
            )
            rows = getattr(res, "data", None) or []
            if rows:
                return int(rows[0].get("usage_count", 0))
            return None
        except Exception:
            return None


__all__ = [
    "SupabaseAccountRepository",
]
