"""
OAuth 2.0 공급자 서비스 (F7-25)

Insight Engine을 OAuth 2.0 Authorization Server로 동작하게 하는 서비스.
서드파티 앱이 Insight Engine API에 안전하게 접근할 수 있도록 토큰을 발급합니다.

지원 Grant Type:
- authorization_code: 표준 OAuth2 코드 교환
- client_credentials: 서버-서버 인증

주의: 실제 운영 시 RSA 키 서명, PKCE, 토큰 저장소를 반드시 구현해야 합니다.
"""
import hashlib
import logging
import secrets
import time
from typing import Optional

logger = logging.getLogger(__name__)

# 인메모리 스토어 (운영 시 Redis/DB로 교체)
_auth_codes: dict[str, dict] = {}      # code → {client_id, user_id, scope, expires_at, code_challenge}
_access_tokens: dict[str, dict] = {}   # token → {client_id, user_id, scope, expires_at}
_clients: dict[str, dict] = {}         # client_id → {secret_hash, name, redirect_uris, scopes}


class OAuthProviderService:
    """OAuth 2.0 Authorization Server 서비스"""

    TOKEN_EXPIRY = 3600        # 1시간
    CODE_EXPIRY = 300          # 5분

    def register_client(
        self,
        client_name: str,
        redirect_uris: list[str],
        scopes: list[str],
    ) -> dict:
        """OAuth 2.0 클라이언트 등록

        Returns:
            {"client_id": str, "client_secret": str}
        """
        client_id = secrets.token_urlsafe(16)
        client_secret = secrets.token_urlsafe(32)

        _clients[client_id] = {
            'name': client_name,
            'secret_hash': hashlib.sha256(client_secret.encode()).hexdigest(),
            'redirect_uris': redirect_uris,
            'scopes': scopes,
        }
        logger.info(f"OAuth 클라이언트 등록: {client_id} ({client_name})")
        return {'client_id': client_id, 'client_secret': client_secret}

    def create_authorization_code(
        self,
        client_id: str,
        user_id: str,
        scope: str,
        redirect_uri: str,
        code_challenge: Optional[str] = None,
        code_challenge_method: str = 'S256',
    ) -> Optional[str]:
        """인가 코드 발급

        Returns:
            code 문자열 또는 None (클라이언트 미등록/redirect_uri 불일치)
        """
        client = _clients.get(client_id)
        if not client:
            logger.warning(f"OAuth: 미등록 클라이언트 — {client_id}")
            return None

        if redirect_uri not in client['redirect_uris']:
            logger.warning(f"OAuth: redirect_uri 불일치 — {redirect_uri}")
            return None

        code = secrets.token_urlsafe(24)
        _auth_codes[code] = {
            'client_id': client_id,
            'user_id': user_id,
            'scope': scope,
            'redirect_uri': redirect_uri,
            'expires_at': time.time() + self.CODE_EXPIRY,
            'code_challenge': code_challenge,
            'code_challenge_method': code_challenge_method,
        }
        return code

    def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        code_verifier: Optional[str] = None,
    ) -> dict:
        """인가 코드 → 액세스 토큰 교환

        Returns:
            {"access_token": str, "token_type": "Bearer", "expires_in": int, "scope": str}
            또는 {"error": str, "error_description": str}
        """
        code_data = _auth_codes.pop(code, None)

        if not code_data:
            return {'error': 'invalid_grant', 'error_description': '유효하지 않은 인가 코드'}

        if time.time() > code_data['expires_at']:
            return {'error': 'invalid_grant', 'error_description': '인가 코드가 만료되었습니다.'}

        if code_data['client_id'] != client_id:
            return {'error': 'invalid_client', 'error_description': '클라이언트 ID 불일치'}

        if code_data['redirect_uri'] != redirect_uri:
            return {'error': 'invalid_grant', 'error_description': 'redirect_uri 불일치'}

        # 클라이언트 시크릿 또는 PKCE 검증
        client = _clients.get(client_id)
        if not client:
            return {'error': 'invalid_client', 'error_description': '클라이언트 미등록'}

        code_challenge = code_data.get('code_challenge')
        if code_challenge:
            # PKCE 검증
            if not code_verifier:
                return {'error': 'invalid_grant', 'error_description': 'code_verifier가 필요합니다.'}
            method = code_data.get('code_challenge_method', 'S256')
            if method == 'S256':
                import base64
                computed = base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode()).digest()
                ).rstrip(b'=').decode()
                if computed != code_challenge:
                    return {'error': 'invalid_grant', 'error_description': 'code_verifier 불일치'}
        else:
            # 클라이언트 시크릿 검증
            secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
            if secret_hash != client.get('secret_hash', ''):
                return {'error': 'invalid_client', 'error_description': '클라이언트 시크릿 불일치'}

        return self._issue_token(
            client_id=client_id,
            user_id=code_data['user_id'],
            scope=code_data['scope'],
        )

    def client_credentials_token(self, client_id: str, client_secret: str, scope: str) -> dict:
        """Client Credentials Grant

        서버-서버 통신용 (사용자 없이 앱 자체 인증)
        """
        client = _clients.get(client_id)
        if not client:
            return {'error': 'invalid_client', 'error_description': '클라이언트 미등록'}

        secret_hash = hashlib.sha256(client_secret.encode()).hexdigest()
        if secret_hash != client.get('secret_hash', ''):
            return {'error': 'invalid_client', 'error_description': '클라이언트 시크릿 불일치'}

        return self._issue_token(client_id=client_id, user_id=None, scope=scope)

    def _issue_token(self, client_id: str, user_id: Optional[str], scope: str) -> dict:
        """액세스 토큰 발급"""
        token = secrets.token_urlsafe(40)
        _access_tokens[token] = {
            'client_id': client_id,
            'user_id': user_id,
            'scope': scope,
            'expires_at': time.time() + self.TOKEN_EXPIRY,
        }
        logger.info(f"OAuth 토큰 발급: client={client_id}, user={user_id}, scope={scope}")
        return {
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': self.TOKEN_EXPIRY,
            'scope': scope,
        }

    def validate_token(self, token: str) -> Optional[dict]:
        """액세스 토큰 유효성 검증

        Returns:
            토큰 정보 dict 또는 None (유효하지 않음)
        """
        token_data = _access_tokens.get(token)
        if not token_data:
            return None
        if time.time() > token_data['expires_at']:
            del _access_tokens[token]
            return None
        return token_data

    def revoke_token(self, token: str) -> bool:
        """토큰 폐기"""
        if token in _access_tokens:
            del _access_tokens[token]
            return True
        return False

    def list_clients(self) -> list[dict]:
        """등록된 클라이언트 목록 (시크릿 제외)"""
        return [
            {
                'client_id': cid,
                'name': c['name'],
                'redirect_uris': c['redirect_uris'],
                'scopes': c['scopes'],
            }
            for cid, c in _clients.items()
        ]

    def get_active_token_count(self) -> int:
        """유효한 토큰 수"""
        now = time.time()
        return sum(1 for t in _access_tokens.values() if t['expires_at'] > now)


oauth_provider_service = OAuthProviderService()
