"""Identity & Access BC의 Application Service.

다른 BC와 라우트 핸들러가 Identity 도메인에 접근할 때의 진입점.
포트(IAccountRepository, IApiKeyVault, IUsageGateway)에 의존하며
구체 어댑터는 DI로 주입.
"""
from dataclasses import dataclass
from typing import Optional, List
from src.contexts.identity.application.ports import (
    IAccountRepository, IApiKeyVault, IUsageGateway
)
from src.contexts.identity.domain.user_account import UserAccount, ApiKey
from src.contexts.identity.domain.exceptions import (
    AccountNotFound, QuotaExceeded, InvalidApiKey
)
from src.shared.domain.value_objects import AccountId


@dataclass
class AccountService:
    """Identity & Access Application Service.

    예시 사용:
        service = AccountService(
            accounts=SupabaseAccountRepository(),
            api_keys=SupabaseApiKeyVault(),
            usage=SupabaseUsageGateway(),
        )
        account = service.get_account(account_id)
        remaining = service.enforce_quota(account_id)
    """
    accounts: IAccountRepository
    api_keys: IApiKeyVault
    usage: IUsageGateway

    def get_account(self, account_id: AccountId) -> UserAccount:
        """ID로 어카운트 조회. 없으면 AccountNotFound."""
        account = self.accounts.find_by_id(account_id)
        if account is None:
            raise AccountNotFound(f"account_id={account_id}")
        return account

    def enforce_quota(self, account_id: AccountId, amount: int = 1) -> int:
        """사용량 한도 체크 + 차감. 남은 양 반환. QuotaExceeded 가능."""
        return self.usage.check_and_consume(account_id, amount)

    def add_api_key(
        self, account_id: AccountId, provider: str, plaintext_key: str, label: str = "default"
    ) -> ApiKey:
        """BYO API 키 추가. 평문은 Vault에만 저장, 마스킹된 ApiKey VO 반환."""
        return self.api_keys.store(account_id, provider, plaintext_key, label)

    def get_api_key_plaintext(
        self, account_id: AccountId, provider: str, label: str = "default"
    ) -> str:
        """LLM 호출 직전에만 평문 키 노출. 도메인 객체에 저장하지 말 것."""
        return self.api_keys.reveal(account_id, provider, label)

    def resolve_provider_key(
        self, account_id: AccountId, provider: str
    ) -> str:
        """BYO 우선, 없으면 공유 키(환경변수) 폴백.

        기존 services/data/api_key_service.py의 핵심 동작.
        """
        import os
        # 1차: BYO 시도
        try:
            return self.api_keys.reveal(account_id, provider, "default")
        except InvalidApiKey:
            pass
        # 2차: 환경변수 공유 키 폴백
        env_keys = {
            'gemini': 'GEMINI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
            'zhipu': 'ZHIPUAI_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'openrouter': 'OPENROUTER_API_KEY',
        }
        env_var = env_keys.get(provider.lower())
        if env_var and os.getenv(env_var):
            return os.getenv(env_var)
        raise InvalidApiKey(
            f"키 해결 실패 — BYO 없음, 환경변수 {env_var} 미설정 (provider={provider})"
        )

    def revoke_api_key(
        self, account_id: AccountId, provider: str, label: str = "default"
    ) -> None:
        """API 키 폐기 (비활성화)."""
        self.api_keys.revoke(account_id, provider, label)


__all__ = ["AccountService"]
