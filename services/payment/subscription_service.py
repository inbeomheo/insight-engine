"""
구독 플랜 관리 서비스
Stripe Subscription API 래퍼
"""
import json
import os
from datetime import datetime, timezone

from services.supabase_service import is_supabase_enabled, get_supabase
from services.logging_config import ServiceLogger

logger = ServiceLogger('SubscriptionService')

_LOCAL_SUBS_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'subscriptions.json'
)


def _load_local_subs() -> dict:
    """로컬 구독 데이터 로드"""
    if os.path.exists(_LOCAL_SUBS_FILE):
        with open(_LOCAL_SUBS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_local_subs(data: dict):
    """로컬 구독 데이터 저장"""
    os.makedirs(os.path.dirname(_LOCAL_SUBS_FILE), exist_ok=True)
    with open(_LOCAL_SUBS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class SubscriptionService:
    """구독 관리"""

    @staticmethod
    def get_subscription(user_id: str) -> dict:
        """
        사용자 구독 정보 조회

        Returns:
            {'plan': str, 'status': str, 'stripe_subscription_id': str, ...}
        """
        if is_supabase_enabled():
            try:
                client = get_supabase()
                result = client.table('ie_subscriptions').select('*') \
                    .eq('user_id', user_id).maybe_single().execute()
                if result.data:
                    return result.data
            except Exception as e:
                logger.error(f"구독 조회 실패: {e}")

        # 로컬 폴백
        data = _load_local_subs()
        return data.get(user_id, {
            'plan': 'free',
            'status': 'active',
            'stripe_subscription_id': None,
        })

    @staticmethod
    def activate(user_id: str, stripe_subscription_id: str, plan: str = 'pro') -> dict:
        """구독 활성화"""
        now = datetime.now(timezone.utc).isoformat()
        sub_data = {
            'user_id': user_id,
            'plan': plan,
            'status': 'active',
            'stripe_subscription_id': stripe_subscription_id,
            'activated_at': now,
            'updated_at': now,
        }

        if is_supabase_enabled():
            try:
                client = get_supabase()
                client.table('ie_subscriptions').upsert(sub_data).execute()
                # 크레딧 플랜도 업데이트
                client.table('ie_credits').upsert({
                    'user_id': user_id,
                    'plan': plan,
                    'updated_at': now,
                }).execute()
                return {'success': True, 'plan': plan}
            except Exception as e:
                logger.error(f"구독 활성화 실패: {e}")
                return {'success': False, 'error': str(e)}

        # 로컬 폴백
        data = _load_local_subs()
        data[user_id] = sub_data
        _save_local_subs(data)
        return {'success': True, 'plan': plan}

    @staticmethod
    def upgrade(user_id: str, new_plan: str) -> dict:
        """플랜 업그레이드"""
        current = SubscriptionService.get_subscription(user_id)
        stripe_sub_id = current.get('stripe_subscription_id')

        if stripe_sub_id:
            # Stripe 구독 업데이트
            try:
                from services.payment.stripe_service import _get_stripe
                stripe = _get_stripe()
                if stripe:
                    # 실제로는 price_id 변경 필요 — 여기서는 메타데이터만 업데이트
                    stripe.Subscription.modify(
                        stripe_sub_id,
                        metadata={'plan': new_plan, 'user_id': user_id},
                    )
            except Exception as e:
                logger.error(f"Stripe 구독 업그레이드 실패: {e}")
                return {'success': False, 'error': str(e)}

        return SubscriptionService.activate(user_id, stripe_sub_id or '', new_plan)

    @staticmethod
    def downgrade(user_id: str, new_plan: str) -> dict:
        """플랜 다운그레이드"""
        return SubscriptionService.upgrade(user_id, new_plan)

    @staticmethod
    def cancel(user_id: str) -> dict:
        """구독 취소 → free 플랜으로 전환"""
        now = datetime.now(timezone.utc).isoformat()

        if is_supabase_enabled():
            try:
                client = get_supabase()
                client.table('ie_subscriptions').upsert({
                    'user_id': user_id,
                    'plan': 'free',
                    'status': 'canceled',
                    'canceled_at': now,
                    'updated_at': now,
                }).execute()
                client.table('ie_credits').upsert({
                    'user_id': user_id,
                    'plan': 'free',
                    'updated_at': now,
                }).execute()
                return {'success': True}
            except Exception as e:
                logger.error(f"구독 취소 실패: {e}")
                return {'success': False, 'error': str(e)}

        # 로컬 폴백
        data = _load_local_subs()
        data[user_id] = {
            'plan': 'free', 'status': 'canceled',
            'canceled_at': now, 'updated_at': now,
        }
        _save_local_subs(data)
        return {'success': True}


subscription_service = SubscriptionService()
