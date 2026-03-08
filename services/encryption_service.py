"""
데이터 암호화 서비스 (F9-22)
AES-256-GCM 대칭 암호화, Fernet 래퍼 제공
cryptography 패키지 필요: pip install cryptography
"""
import base64
import hashlib
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False
    logger.warning("cryptography 미설치 — 암호화 기능 비활성화 (pip install cryptography)")


def _get_encryption_key() -> bytes:
    """환경변수 ENCRYPTION_KEY에서 32바이트 키 추출 (없으면 자동 생성 경고)"""
    raw = os.getenv('ENCRYPTION_KEY', '')
    if raw:
        # PBKDF2로 32바이트 키 파생
        return hashlib.pbkdf2_hmac(
            'sha256',
            raw.encode(),
            b'insight-engine-salt',
            iterations=100000,
            dklen=32
        )
    logger.warning("ENCRYPTION_KEY 미설정 — 암호화가 안전하지 않습니다. 프로덕션에서 반드시 설정하세요.")
    # 폴백: 고정 키 (개발용 전용)
    return b'\x00' * 32


class EncryptionService:
    """AES-256-GCM 기반 대칭 암호화 서비스"""

    def __init__(self):
        if not _CRYPTO_AVAILABLE:
            logger.error("cryptography 패키지 미설치")
            self._available = False
            return

        self._key = _get_encryption_key()
        self._aesgcm = AESGCM(self._key)
        # Fernet 호환 키 (base64url-encoded 32bytes)
        fernet_key = base64.urlsafe_b64encode(self._key)
        self._fernet = Fernet(fernet_key)
        self._available = True

    def encrypt(self, plaintext: str) -> str:
        """
        텍스트 암호화 (AES-256-GCM)

        Args:
            plaintext: 암호화할 평문

        Returns:
            base64 인코딩된 암호문 (nonce + ciphertext)
        """
        if not self._available:
            raise RuntimeError("cryptography 패키지가 필요합니다")

        nonce = os.urandom(12)  # GCM 표준 12바이트 nonce
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        combined = nonce + ciphertext
        return base64.urlsafe_b64encode(combined).decode('ascii')

    def decrypt(self, encrypted: str) -> str:
        """
        암호문 복호화

        Args:
            encrypted: encrypt()의 반환값

        Returns:
            복호화된 평문

        Raises:
            ValueError: 잘못된 암호문 또는 변조 감지
        """
        if not self._available:
            raise RuntimeError("cryptography 패키지가 필요합니다")

        try:
            combined = base64.urlsafe_b64decode(encrypted.encode('ascii'))
            nonce = combined[:12]
            ciphertext = combined[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode('utf-8')
        except Exception as e:
            raise ValueError(f"복호화 실패 (변조되었거나 잘못된 키): {e}") from e

    def encrypt_fernet(self, plaintext: str) -> str:
        """Fernet 토큰 암호화 (timestamp 포함, TTL 검증 가능)"""
        if not self._available:
            raise RuntimeError("cryptography 패키지가 필요합니다")
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt_fernet(self, token: str, ttl: Optional[int] = None) -> str:
        """
        Fernet 토큰 복호화

        Args:
            token: encrypt_fernet()의 반환값
            ttl: 만료 시간 (초). None이면 TTL 무시.
        """
        if not self._available:
            raise RuntimeError("cryptography 패키지가 필요합니다")
        try:
            kwargs = {}
            if ttl:
                kwargs['ttl'] = ttl
            return self._fernet.decrypt(token.encode(), **kwargs).decode()
        except InvalidToken as e:
            raise ValueError(f"Fernet 복호화 실패 (만료 또는 변조): {e}") from e

    def hash_sensitive(self, value: str, salt: str = '') -> str:
        """
        민감 데이터 단방향 해시 (SHA-256 + salt)
        DB 저장 전 이메일, 전화번호 등의 해시에 사용
        """
        data = f"{salt}{value}".encode('utf-8')
        return hashlib.sha256(data).hexdigest()

    @property
    def available(self) -> bool:
        """암호화 기능 사용 가능 여부"""
        return self._available


# 싱글톤 인스턴스
_encryption_service: Optional['EncryptionService'] = None


def get_encryption_service() -> 'EncryptionService':
    """EncryptionService 싱글톤 인스턴스 반환"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    return _encryption_service
