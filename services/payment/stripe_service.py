"""
Stripe 결제 서비스
Checkout Session 생성, Webhook 처리
"""
import os
from typing import Optional

from services.core.logging_config import ServiceLogger

logger = ServiceLogger('StripeService')

# Stripe 키 (환경변수에서 로드)
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', '')
STRIPE_SUCCESS_URL = os.getenv('STRIPE_SUCCESS_URL', 'http://localhost:3000/billing?success=true')
STRIPE_CANCEL_URL = os.getenv('STRIPE_CANCEL_URL', 'http://localhost:3000/billing?canceled=true')


def _get_stripe():
    """stripe 모듈 lazy import (설치 안 되었을 때 graceful)"""
    try:
        import stripe
        stripe.api_key = STRIPE_SECRET_KEY
        return stripe
    except ImportError:
        logger.warning("stripe 패키지가 설치되지 않았습니다: pip install stripe")
        return None


class StripeService:
    """Stripe 결제 처리"""

    @staticmethod
    def is_enabled() -> bool:
        """Stripe가 설정되었는지 확인"""
        try:
            return bool(STRIPE_SECRET_KEY)
        except Exception as e:
            logger.error("is_enabled 실패: %s", e, exc_info=True)
            return False

    @staticmethod
    def create_checkout_session(
        user_id: str,
        price_id: str,
        mode: str = 'subscription',
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> dict:
        """
        Stripe Checkout Session 생성

        Args:
            user_id: 사용자 ID
            price_id: Stripe Price ID
            mode: 'subscription' 또는 'payment'
            success_url: 결제 성공 후 리다이렉트 URL
            cancel_url: 결제 취소 후 리다이렉트 URL

        Returns:
            {'session_id': str, 'url': str} 또는 {'error': str}
        """
        stripe = _get_stripe()
        if not stripe:
            return {'error': 'Stripe가 설정되지 않았습니다.'}

        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{'price': price_id, 'quantity': 1}],
                mode=mode,
                success_url=success_url or STRIPE_SUCCESS_URL,
                cancel_url=cancel_url or STRIPE_CANCEL_URL,
                client_reference_id=user_id,
                metadata={'user_id': user_id},
            )
            return {'session_id': session.id, 'url': session.url}
        except Exception as e:
            logger.error(f"Checkout 세션 생성 실패: {e}")
            return {'error': f'결제 세션 생성 실패: {str(e)}'}

    @staticmethod
    def handle_webhook(payload: bytes, sig_header: str) -> dict:
        """
        Stripe Webhook 이벤트 처리

        Args:
            payload: 요청 body (raw bytes)
            sig_header: Stripe-Signature 헤더

        Returns:
            {'success': bool, 'event_type': str}
        """
        stripe = _get_stripe()
        if not stripe:
            return {'success': False, 'error': 'Stripe 미설정'}

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            logger.warning("Webhook 서명 검증 실패")
            return {'success': False, 'error': '서명 검증 실패'}
        except Exception as e:
            logger.error(f"Webhook 파싱 실패: {e}")
            return {'success': False, 'error': str(e)}

        event_type = event['type']
        data = event['data']['object']

        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(data)
        elif event_type == 'customer.subscription.updated':
            _handle_subscription_updated(data)
        elif event_type == 'customer.subscription.deleted':
            _handle_subscription_deleted(data)

        return {'success': True, 'event_type': event_type}


def _handle_checkout_completed(session: dict):
    """결제 완료 처리 — 크레딧 충전 또는 구독 활성화"""
    user_id = session.get('client_reference_id') or session.get('metadata', {}).get('user_id')
    if not user_id:
        logger.warning("Checkout 완료 이벤트에 user_id 없음")
        return

    mode = session.get('mode')
    if mode == 'payment':
        # 일회성 결제 → 크레딧 충전
        from services.usage.credit_service import credit_service
        amount = session.get('metadata', {}).get('credits', 100)
        credit_service.add_credits(user_id, int(amount), reason='stripe_payment')
        logger.info(f"크레딧 충전 완료: {user_id[:8]}... +{amount}")
    elif mode == 'subscription':
        # 구독 → 플랜 업그레이드
        from services.payment.subscription_service import subscription_service
        subscription_id = session.get('subscription')
        subscription_service.activate(user_id, subscription_id)
        logger.info(f"구독 활성화: {user_id[:8]}...")


def _handle_subscription_updated(subscription: dict):
    """구독 업데이트 처리"""
    logger.info(f"구독 업데이트: {subscription.get('id')}")


def _handle_subscription_deleted(subscription: dict):
    """구독 취소 처리"""
    from services.payment.subscription_service import subscription_service
    metadata = subscription.get('metadata', {})
    user_id = metadata.get('user_id')
    if user_id:
        subscription_service.cancel(user_id)
        logger.info(f"구독 취소: {user_id[:8]}...")


stripe_service = StripeService()
