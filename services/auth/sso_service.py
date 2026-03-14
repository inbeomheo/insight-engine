"""
SSO 서비스 (F4-24)
SAML/OIDC 기반 싱글 사인온
"""
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('SSOService')


class SSOService:
    """SAML/OIDC SSO 관리"""

    def __init__(self):
        # workspace_id → SSO 설정
        self._configs: dict[str, dict] = {}
        # session tokens
        self._sessions: dict[str, dict] = {}

    def configure_sso(
        self,
        workspace_id: str,
        provider: str,
        config: dict,
    ) -> dict:
        """SSO 프로바이더 설정

        Args:
            workspace_id: 워크스페이스 ID
            provider: 'saml' 또는 'oidc'
            config: {
                entity_id, sso_url, certificate (SAML)
                client_id, client_secret, issuer_url (OIDC)
            }
        """
        if provider not in ('saml', 'oidc'):
            return {'error': "provider는 'saml' 또는 'oidc'만 허용됩니다."}

        required = {'saml': ['entity_id', 'sso_url'], 'oidc': ['client_id', 'issuer_url']}
        missing = [k for k in required[provider] if k not in config]
        if missing:
            return {'error': f'필수 설정 누락: {", ".join(missing)}'}

        self._configs[workspace_id] = {
            'provider': provider,
            'config': config,
            'enabled': True,
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        logger.info(f"SSO 설정: {workspace_id} ({provider})")
        return self._configs[workspace_id]

    def get_config(self, workspace_id: str) -> dict | None:
        """SSO 설정 조회"""
        return self._configs.get(workspace_id)

    def is_enabled(self, workspace_id: str) -> bool:
        """SSO 활성화 여부"""
        config = self._configs.get(workspace_id)
        return bool(config and config.get('enabled'))

    def initiate_login(self, workspace_id: str) -> dict:
        """SSO 로그인 시작 (리다이렉트 URL 생성)"""
        config = self._configs.get(workspace_id)
        if not config or not config.get('enabled'):
            return {'error': 'SSO가 설정되지 않았습니다.'}

        state = uuid.uuid4().hex
        provider_config = config['config']

        if config['provider'] == 'saml':
            redirect_url = provider_config.get('sso_url', '')
        else:
            issuer = provider_config.get('issuer_url', '')
            client_id = provider_config.get('client_id', '')
            redirect_url = f'{issuer}/authorize?client_id={client_id}&state={state}'

        return {'redirect_url': redirect_url, 'state': state}

    def validate_callback(self, workspace_id: str, token_data: dict) -> dict:
        """SSO 콜백 검증 + 세션 생성"""
        config = self._configs.get(workspace_id)
        if not config:
            return {'error': 'SSO 설정을 찾을 수 없습니다.'}

        # 실제로는 SAML assertion / OIDC token 검증
        email = token_data.get('email', '')
        if not email:
            return {'error': '이메일 정보가 없습니다.'}

        session_id = uuid.uuid4().hex
        self._sessions[session_id] = {
            'email': email,
            'workspace_id': workspace_id,
            'provider': config['provider'],
            'created_at': datetime.now(timezone.utc).isoformat(),
        }

        return {'session_id': session_id, 'email': email}

    def disable_sso(self, workspace_id: str) -> dict:
        """SSO 비활성화"""
        config = self._configs.get(workspace_id)
        if not config:
            return {'error': '설정을 찾을 수 없습니다.'}
        config['enabled'] = False
        return config


sso_service = SSOService()
