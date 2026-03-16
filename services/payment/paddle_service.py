"""
Paddle 결제 서비스 (F4-16)
Paddle API 연동 (웹훅 검증 + 구독 관리)
"""
import hashlib
import hmac
import os
from services.core.logging_config import ServiceLogger
import logging

logger = ServiceLogger('PaddleService')

PADDLE_API_KEY = os.getenv('PADDLE_API_KEY', '')
PADDLE_WEBHOOK_SECRET = os.getenv('PADDLE_WEBHOOK_SECRET', '')
PADDLE_SANDBOX = os.getenv('PADDLE_SANDBOX', 'true').lower() == 'true'


class PaddleService:
    """Paddle 결제 연동"""

    def __init__(self):
        self._subscriptions: dict[str, dict] = {}

    @property
    def is_configured(self) -> bool:
        """Paddle API 키 설정 여부"""
        try:
            return bool(PADDLE_API_KEY)
        except Exception as e:
            logger.error("is_configured 실패: %s", e, exc_info=True)
            return False

    def verify_webhook(self, payload: bytes, signature: str) -> bool:
        """웹훅 서명 검증"""
        try:
            if not PADDLE_WEBHOOK_SECRET:
                logger.warning("Paddle 웹훅 시크릿 미설정")
                return False

            expected = hmac.new(
                PADDLE_WEBHOOK_SECRET.encode(),
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
            handlers = {
                'subscription.created': self._on_subscription_created,
                'subscription.updated': self._on_subscription_updated,
                'subscription.canceled': self._on_subscription_canceled,
            }

            handler = handlers.get(event_type)
            if not handler:
                logger.debug(f"미처리 웹훅 이벤트: {event_type}")
                return {'status': 'ignored', 'event_type': event_type}

            return handler(data)
        except Exception as e:
            logger.error("handle_webhook 실패: %s", e, exc_info=True)
            return {}

    def _on_subscription_created(self, data: dict) -> dict:
        sub_id = data.get('subscription_id', '')
        self._subscriptions[sub_id] = {
            'id': sub_id,
            'customer_id': data.get('customer_id', ''),
            'plan_id': data.get('plan_id', ''),
            'status': 'active',
        }
        logger.info(f"Paddle 구독 생성: {sub_id}")
        return {'status': 'created', 'subscription_id': sub_id}

    def _on_subscription_updated(self, data: dict) -> dict:
        sub_id = data.get('subscription_id', '')
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id]['plan_id'] = data.get('plan_id', '')
        return {'status': 'updated', 'subscription_id': sub_id}

    def _on_subscription_canceled(self, data: dict) -> dict:
        sub_id = data.get('subscription_id', '')
        if sub_id in self._subscriptions:
            self._subscriptions[sub_id]['status'] = 'canceled'
        logger.info(f"Paddle 구독 취소: {sub_id}")
        return {'status': 'canceled', 'subscription_id': sub_id}

    def get_subscription(self, subscription_id: str) -> dict | None:
        """구독 정보 단건 조회"""
        try:
            return self._subscriptions.get(subscription_id)
        except Exception as e:
            logger.error("get_subscription 실패: %s", e, exc_info=True)
            return {}


paddle_service = PaddleService()
