"""Identity & Access BC가 외부 인프라에 요구하는 포트 (ACL 인터페이스).

이 인터페이스들은 도메인-주도 설계의 **Anti-Corruption Layer**로,
다른 BC와 인프라 어댑터가 Identity 도메인에 접근할 때 통과해야 하는 경계다.

Phase 2 핵심 목표
-----------------
지금까지 50여 곳에서 `services/data/supabase_service`를 직접 import하던 코드를,
이 인터페이스 뒤로 캡슐화하여 Identity의 단일 진입점을 만든다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from src.contexts.identity.domain.user_account import ApiKey, UserAccount
from src.shared.domain.value_objects import AccountId


class IAccountRepository(ABC):
    """Identity Aggregate를 저장소에서 로드/저장하는 ACL.

    Phase 2의 핵심 — 모든 BC는 `services/data/supabase_service`를 직결하지 않고
    이 인터페이스를 통해 어카운트에 접근해야 한다.

    구현체: `infrastructure/supabase_account_repository.py::SupabaseAccountRepository`
    """

    @abstractmethod
    def find_by_id(self, account_id: AccountId) -> Optional[UserAccount]:
        """주어진 `AccountId`로 UserAccount를 조회. 없으면 None."""

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[UserAccount]:
        """이메일로 UserAccount를 조회. 없으면 None."""

    @abstractmethod
    def save(self, account: UserAccount) -> None:
        """UserAccount의 변경 사항을 저장소에 반영 (upsert)."""

    @abstractmethod
    def consume_quota_atomic(self, account_id: AccountId, amount: int = 1) -> int:
        """사용량을 원자적으로 차감하고 남은 양을 반환.

        Supabase RPC `decrement_usage_safe`와 동치.
        한도 초과 시 `QuotaExceeded` raise.
        """


class IApiKeyVault(ABC):
    """API 키 평문은 도메인 객체에 두지 않고 Vault에서만 관리한다.

    구현체: 차후 PR에서 Supabase + Fernet 암호화 기반 어댑터 추가 예정.
    현재는 `services/data/supabase_service`의 `encrypt_api_key`/`decrypt_api_key`를
    재사용한다.
    """

    @abstractmethod
    def store(
        self,
        account_id: AccountId,
        provider: str,
        plaintext_key: str,
        label: str,
    ) -> ApiKey:
        """평문 키를 안전하게 저장하고, 마스킹된 메타데이터(`ApiKey`)를 반환."""

    @abstractmethod
    def reveal(self, account_id: AccountId, provider: str, label: str) -> str:
        """평문 키 노출. 마지막 사용 시간(audit log) 기록.

        호출자는 반환된 평문을 메모리에만 보관하고 절대 로그/응답에 노출 금지.
        """

    @abstractmethod
    def revoke(self, account_id: AccountId, provider: str, label: str) -> None:
        """지정된 (provider, label) 키를 무효화 (soft delete 또는 삭제)."""


class IUsageGateway(ABC):
    """Quota 차감을 미들웨어 데코레이터에서 호출하는 진입점.

    `IAccountRepository.consume_quota_atomic`과 유사하지만, 비즈니스 흐름에
    더 적합한 시그니처를 제공한다 (예: refund 추가).
    """

    @abstractmethod
    def check_and_consume(self, account_id: AccountId, amount: int = 1) -> int:
        """가용 여부 검사 + 원자적 차감 + 남은 양 반환.

        한도 초과 시 `QuotaExceeded` raise.
        """

    @abstractmethod
    def refund(self, account_id: AccountId, amount: int = 1) -> None:
        """생성 실패 시 환불.

        현재 미구현 — 마스터 플랜의 "트랜잭션 부재 문제" 해소 단초.
        """


__all__ = [
    "IAccountRepository",
    "IApiKeyVault",
    "IUsageGateway",
]
