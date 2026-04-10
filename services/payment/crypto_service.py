"""
암호화폐 결제 서비스 (F4-17)
Coinbase Commerce API 연동
"""
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timezone
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('CryptoService')

COINBASE_API_KEY = os.getenv('COINBASE_COMMERCE_API_KEY', '')
COINBASE_WEBHOOK_SECRET = os.getenv('COINBASE_WEBHOOK_SECRET', '')


class CryptoService:
    """Coinbase Commerce 결제 연동"""

    def __init__(self):
        self._charges: dict[str, dict] = {}

    @property
    def is_configured(self) -> bool:
        """Coinbase Commerce API 키 설정 여부"""
        try:
            return bool(COINBASE_API_KEY)
        except Exception as e:
            logger.error("is_configured 실패: %s", e, exc_info=True)
            return False

    def create_charge(self, user_id: str, amount: float, currency: str = 'USD', description: str = '') -> dict:
        """결제 요청 생성"""
        if not self.is_configured:
            return {'error': 'Coinbase Commerce가 설정되지 않았습니다.'}

        try:
            charge_id = f'CRYPTO-{uuid.uuid4().hex[:8].upper()}'
            charge = {
                'id': charge_id,
                'user_id': user_id,
                'amount': amount,
                'currency': currency,
                'description': description,
                'status': 'pending',
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            self._charges[charge_id] = charge
            logger.info(f"암호화폐 결제 생성: {charge_id} ({amount} {currency})")
            return charge
        except Exception as e:
            logger.error("create_charge 실패: %s", e, exc_info=True)
            return {}

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """웹훅 서명 검증"""
        if not COINBASE_WEBHOOK_SECRET:
            return False
        try:
            expected = hmac.new(
                COINBASE_WEBHOOK_SECRET.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error("verify_webhook 실패: %s", e, exc_info=True)
            return False

    def handle_webhook(self, event_type: str, data: dict) -> dict:
        """웹훅 이벤트 처리"""
        try:
            charge_id = data.get('id', '')

            if event_type == 'charge:confirmed':
                if charge_id in self._charges:
                    self._charges[charge_id]['status'] = 'confirmed'
                logger.info(f"암호화폐 결제 확인: {charge_id}")
                return {'status': 'confirmed', 'charge_id': charge_id}

            if event_type == 'charge:failed':
                if charge_id in self._charges:
                    self._charges[charge_id]['status'] = 'failed'
                return {'status': 'failed', 'charge_id': charge_id}

            return {'status': 'ignored', 'event_type': event_type}
        except Exception as e:
            logger.error("handle_webhook 실패: %s", e, exc_info=True)
            return {}

    def get_charge(self, charge_id: str) -> dict | None:
        """결제 요청 단건 조회"""
        try:
            return self._charges.get(charge_id)
        except Exception as e:
            logger.error("get_charge 실패: %s", e, exc_info=True)
            return {}


crypto_service = CryptoService()
