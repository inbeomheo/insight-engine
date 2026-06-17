"""IApiKeyVault의 Supabase + Fernet 구현 어댑터.

기존 services/data/api_key_service.py와 services/data/supabase_service.py의
암호화 헬퍼를 lazy import하여 재사용. Phase 2 마이그레이션 완료 후
기존 api_key_service는 deprecation shim으로 남기고 단계적으로 본 어댑터로 대체 예정.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from src.contexts.identity.application.ports import IApiKeyVault
from src.contexts.identity.domain.user_account import ApiKey
from src.contexts.identity.domain.exceptions import InvalidApiKey
from src.shared.domain.value_objects import AccountId

logger = logging.getLogger(__name__)


class SupabaseApiKeyVault(IApiKeyVault):
    """Supabase ie_user_api_keys 테이블 + Fernet 암호화 기반 API 키 저장소.

    평문 키는 절대 도메인 객체에 들어가지 않음 — 마스킹된 ApiKey VO만 노출.
    평문이 필요한 시점(LLM 호출)에만 reveal() 호출.
    """

    def _get_client(self):
        from src.shared.infrastructure.supabase_client import (
            get_supabase, is_supabase_enabled,
        )
        if not is_supabase_enabled():
            return None
        return get_supabase()

    def _encrypt(self, plaintext: str) -> str:
        from src.shared.infrastructure.supabase_client import encrypt_api_key
        return encrypt_api_key(plaintext)

    def _decrypt(self, encrypted: str) -> str:
        from src.shared.infrastructure.supabase_client import decrypt_api_key
        return decrypt_api_key(encrypted)

    @staticmethod
    def _mask(plaintext: str) -> str:
        """평문 키의 마지막 4자를 제외하고 *로 마스킹.

        보안: 도메인 객체에 노출되는 ApiKey는 반드시 마스킹된 값.
        """
        if not plaintext or len(plaintext) < 8:
            return "*" * 8
        return "*" * (len(plaintext) - 4) + plaintext[-4:]

    def store(
        self,
        account_id: AccountId,
        provider: str,
        plaintext_key: str,
        label: str
    ) -> ApiKey:
        """평문 키를 암호화 저장하고 마스킹된 ApiKey VO 반환."""
        if not plaintext_key or len(plaintext_key) < 8:
            raise InvalidApiKey(f"키 길이가 너무 짧음 (provider={provider})")

        client = self._get_client()
        if client is None:
            # 개발 모드: 저장하지 않고 마스킹된 객체만 반환
            logger.warning(
                "SupabaseApiKeyVault.store: Supabase 비활성, 메모리 마스킹만 (account=%s, provider=%s)",
                account_id, provider
            )
            return ApiKey(
                provider=provider,
                masked_key=self._mask(plaintext_key),
                label=label,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )

        try:
            encrypted = self._encrypt(plaintext_key)
            # on_conflict 지정 — (user_id, provider, label) 유니크 인덱스 기준으로
            # 동일 키 재저장 시 충돌 에러 대신 기존 행을 갱신(키 회전)한다.
            res = client.table('ie_user_api_keys').upsert({
                'user_id': str(account_id),
                'provider': provider,
                'label': label,
                'encrypted_key': encrypted,
                'is_active': True,
            }, on_conflict='user_id,provider,label').execute()
            return ApiKey(
                provider=provider,
                masked_key=self._mask(plaintext_key),
                label=label,
                is_active=True,
                created_at=datetime.now(timezone.utc),
            )
        except Exception as e:
            logger.error("SupabaseApiKeyVault.store 실패: %s", e)
            raise InvalidApiKey(f"키 저장 실패 (provider={provider}): {e}")

    def reveal(self, account_id: AccountId, provider: str, label: str) -> str:
        """평문 키 복호화 + 마지막 사용 시간 갱신.

        Returns:
            평문 API 키 문자열.
        Raises:
            InvalidApiKey: 키가 없거나 비활성이거나 복호화 실패.
        """
        client = self._get_client()
        if client is None:
            # 개발 모드: 환경변수 폴백
            import os
            env_keys = {
                'gemini': 'GEMINI_API_KEY',
                'deepseek': 'DEEPSEEK_API_KEY',
                'zhipu': 'ZHIPUAI_API_KEY',
                'openai': 'OPENAI_API_KEY',
                'anthropic': 'ANTHROPIC_API_KEY',
                'openrouter': 'OPENROUTER_API_KEY',
            }
            env_key = env_keys.get(provider.lower())
            if env_key and os.getenv(env_key):
                return os.getenv(env_key)
            raise InvalidApiKey(f"환경변수 fallback도 없음: provider={provider}")

        try:
            res = client.table('ie_user_api_keys').select('encrypted_key, is_active').eq(
                'user_id', str(account_id)
            ).eq('provider', provider).eq('label', label).limit(1).execute()
            rows = res.data or []
            if not rows or not rows[0].get('is_active'):
                raise InvalidApiKey(f"활성 키 없음: provider={provider}, label={label}")
            decrypted = self._decrypt(rows[0]['encrypted_key'])
            # TODO: last_used_at 갱신 (Phase 2 다음 PR)
            return decrypted
        except InvalidApiKey:
            raise
        except Exception as e:
            logger.error("SupabaseApiKeyVault.reveal 실패: %s", e)
            raise InvalidApiKey(f"키 복호화 실패: {e}")

    def revoke(self, account_id: AccountId, provider: str, label: str) -> None:
        """API 키 비활성화 (is_active=False)."""
        client = self._get_client()
        if client is None:
            logger.warning("SupabaseApiKeyVault.revoke: Supabase 비활성, no-op")
            return
        try:
            client.table('ie_user_api_keys').update({'is_active': False}).eq(
                'user_id', str(account_id)
            ).eq('provider', provider).eq('label', label).execute()
        except Exception as e:
            logger.error("SupabaseApiKeyVault.revoke 실패: %s", e)
            raise InvalidApiKey(f"키 폐기 실패: {e}")


__all__ = ["SupabaseApiKeyVault"]
