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
from src.contexts.identity.domain.exceptions import InvalidApiKey
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

    def execute(self, account_id: AccountId, provider: str, label: str = "default") -> str:
        """평문 API 키 반환 (BYO 우선, 없으면 환경변수 폴백). InvalidApiKey 가능."""
        import os
        try:
            return self.vault.reveal(account_id, provider, label)
        except InvalidApiKey:
            pass
        env_var = {
            'gemini': 'GEMINI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'zhipu': 'ZHIPUAI_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
        }.get(provider.lower())
        if env_var and os.getenv(env_var):
            return os.getenv(env_var)
        raise InvalidApiKey(f"키 해결 실패: provider={provider}")


__all__ = [
    "EnforceQuotaUseCase",
    "ResolveApiKeyUseCase",
]
