"""
추천인/레퍼럴 서비스
추천 코드 생성, 추천 보상 지급
"""
import json
import os
import secrets
from datetime import datetime, timezone
from typing import Optional

from src.shared.infrastructure.supabase_client import is_supabase_enabled, get_supabase
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('ReferralService')

REFERRAL_REWARD_CREDITS = 5  # 추천 성공 시 양측에 지급할 크레딧

_LOCAL_REFERRALS_FILE = os.path.join(
    os.getenv('APP_DATA_DIR', 'data'), 'referrals.json'
)


def _load_local() -> dict:
    if os.path.exists(_LOCAL_REFERRALS_FILE):
        with open(_LOCAL_REFERRALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'codes': {}, 'history': []}


def _save_local(data: dict):
    os.makedirs(os.path.dirname(_LOCAL_REFERRALS_FILE), exist_ok=True)
    with open(_LOCAL_REFERRALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class ReferralService:
    """레퍼럴/추천인 관리"""

    @staticmethod
    def get_or_create_code(user_id: str) -> str:
        """사용자의 추천 코드를 반환 (없으면 생성)"""
        try:
            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    result = client.table('ie_referrals').select('code') \
                        .eq('user_id', user_id).maybe_single().execute()
                    if result.data:
                        return result.data['code']

                    # 새 코드 생성
                    code = secrets.token_urlsafe(8)
                    client.table('ie_referrals').insert({
                        'user_id': user_id,
                        'code': code,
                        'referral_count': 0,
                        'created_at': datetime.now(timezone.utc).isoformat(),
                    }).execute()
                    return code
                except Exception as e:
                    logger.error(f"추천 코드 조회/생성 실패: {e}")

            # 로컬 폴백
            data = _load_local()
            codes = data.get('codes', {})
            if user_id in codes:
                return codes[user_id]['code']

            code = secrets.token_urlsafe(8)
            codes[user_id] = {
                'code': code,
                'referral_count': 0,
                'created_at': datetime.now(timezone.utc).isoformat(),
            }
            data['codes'] = codes
            _save_local(data)
            return code
        except Exception as e:
            logger.error("get_or_create_code 실패: %s", e, exc_info=True)
            return ''

    @staticmethod
    def get_referral_info(user_id: str) -> dict:
        """추천 정보 조회 (코드, 추천 횟수, 적립 크레딧)"""
        try:
            code = ReferralService.get_or_create_code(user_id)

            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    result = client.table('ie_referrals').select('*') \
                        .eq('user_id', user_id).maybe_single().execute()
                    if result.data:
                        return {
                            'code': result.data['code'],
                            'referral_count': result.data.get('referral_count', 0),
                            'total_earned': result.data.get('referral_count', 0) * REFERRAL_REWARD_CREDITS,
                        }
                except Exception as e:
                    logger.error(f"추천 정보 조회 실패: {e}")

            data = _load_local()
            user_data = data.get('codes', {}).get(user_id, {})
            count = user_data.get('referral_count', 0)
            return {
                'code': code,
                'referral_count': count,
                'total_earned': count * REFERRAL_REWARD_CREDITS,
            }
        except Exception as e:
            logger.error("get_referral_info 실패: %s", e, exc_info=True)
            return {}

    @staticmethod
    def _find_referrer(referral_code: str) -> Optional[str]:
        """추천 코드로 추천인 ID를 검색합니다."""
        if is_supabase_enabled():
            try:
                client = get_supabase()
                result = client.table('ie_referrals').select('user_id') \
                    .eq('code', referral_code).maybe_single().execute()
                if result.data:
                    return result.data['user_id']
            except Exception as e:
                logger.error(f"추천 코드 조회 실패: {e}")
        else:
            data = _load_local()
            for uid, info in data.get('codes', {}).items():
                if info.get('code') == referral_code:
                    return uid
        return None

    @staticmethod
    def _increment_count(referrer_id: str) -> None:
        """추천 횟수를 1 증가시킵니다."""
        if is_supabase_enabled():
            try:
                client = get_supabase()
                client.rpc('increment_referral_count', {'p_user_id': referrer_id}).execute()
            except Exception:
                pass
        else:
            data = _load_local()
            codes = data.get('codes', {})
            if referrer_id in codes:
                codes[referrer_id]['referral_count'] = codes[referrer_id].get('referral_count', 0) + 1
                data['codes'] = codes
                _save_local(data)

    @staticmethod
    def apply_referral(new_user_id: str, referral_code: str) -> dict:
        """추천 코드 적용 — 양측에 크레딧 지급

        Args:
            new_user_id: 신규 사용자 ID
            referral_code: 추천 코드

        Returns:
            {'success': bool, 'referrer_id': str, 'credits_given': int}
        """
        try:
            from services.usage.credit_service import credit_service

            referrer_id = ReferralService._find_referrer(referral_code)
            if not referrer_id:
                return {'success': False, 'error': '유효하지 않은 추천 코드입니다.'}
            if referrer_id == new_user_id:
                return {'success': False, 'error': '본인의 추천 코드는 사용할 수 없습니다.'}

            credit_service.add_credits(referrer_id, REFERRAL_REWARD_CREDITS, reason='referral_reward')
            credit_service.add_credits(new_user_id, REFERRAL_REWARD_CREDITS, reason='referral_bonus')
            ReferralService._increment_count(referrer_id)

            logger.info(f"추천 적용: {new_user_id[:8]}... → 추천인 {referrer_id[:8]}... (+{REFERRAL_REWARD_CREDITS})")
            return {
                'success': True,
                'referrer_id': referrer_id,
                'credits_given': REFERRAL_REWARD_CREDITS,
            }
        except Exception as e:
            logger.error("apply_referral 실패: %s", e, exc_info=True)
            return {}


referral_service = ReferralService()
