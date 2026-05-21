"""Identity & Access 유스케이스 (어플리케이션 서비스) 골격.

각 유스케이스는 도메인 객체 + 포트(ACL)를 조합한 비즈니스 흐름을 표현한다.
컨트롤러/라우트는 유스케이스만 호출하고, 도메인 객체를 직접 다루지 않는다.

현재는 골격만 정의 (시그니처 + 일부 위임). 본격 구현은 Phase 2-d/e/f에서 진행.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.contexts.identity.application.ports import (
    IAccountRepository,
    IApiKeyVault,
    IUsageGateway,
)
from src.shared.domain.value_objects import AccountId


@dataclass
class EnforceQuotaUseCase:
    """기존 `@require_usage` 데코레이터의 도메인 로직 추출.

    호출 흐름:
      1. accounts.find_by_id(account_id) — 어카운트 존재 확인
      2. usage.check_and_consume(account_id, amount) — 원자적 차감
      3. 남은 사용량 반환 (호출자가 응답 헤더에 포함 가능)
    """

    accounts: IAccountRepository
    usage: IUsageGateway

    def execute(self, account_id: AccountId, amount: int = 1) -> int:
        """남은 사용량 반환. `QuotaExceeded` 가능."""
        return self.usage.check_and_consume(account_id, amount)


@dataclass
class ResolveApiKeyUseCase:
    """BYO 키 + 공유 키 통합 해결 — 기존 `api_key_service` 책임.

    호출 흐름:
      1. accounts.find_by_id(account_id) → 어카운트의 BYO 키 목록 확인
      2. 활성 BYO 키가 있으면 vault.reveal()로 평문 반환
      3. 없으면 공유 키 폴백 (구현 시 `os.environ`/config 조회)
    """

    accounts: IAccountRepository
    vault: IApiKeyVault

    def execute(self, account_id: AccountId, provider: str) -> str:
        """평문 API 키 반환 (BYO 우선, 없으면 공유 키 폴백).

        Phase 2 다음 단계에서 구현. 호출자는 `NotImplementedError`를 받게 되므로
        실제 마이그레이션 전까지 사용 금지.
        """
        raise NotImplementedError("Phase 2 다음 단계에서 구현")


__all__ = [
    "EnforceQuotaUseCase",
    "ResolveApiKeyUseCase",
]
