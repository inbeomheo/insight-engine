"""
크레딧 기반 과금 서비스
잔액 조회, 충전, 차감, 잔액 확인
"""
import json
import os
import threading
from datetime import datetime, timezone

from services.supabase_service import is_supabase_enabled, get_supabase
from services.logging_config import ServiceLogger

logger = ServiceLogger('CreditService')

# 잔액 조회/차감 원자성 보장용 Lock
_credit_lock = threading.Lock()

# 로컬 폴백용 JSON 파일 경로
_LOCAL_CREDITS_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'credits.json'
)


def _ensure_data_dir():
    """data/ 디렉토리가 없으면 생성"""
    d = os.path.dirname(_LOCAL_CREDITS_FILE)
    os.makedirs(d, exist_ok=True)


def _load_local_credits() -> dict:
    """로컬 JSON에서 크레딧 데이터 로드"""
    _ensure_data_dir()
    if os.path.exists(_LOCAL_CREDITS_FILE):
        with open(_LOCAL_CREDITS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_local_credits(data: dict):
    """로컬 JSON에 크레딧 데이터 저장"""
    _ensure_data_dir()
    with open(_LOCAL_CREDITS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _persist_credit_change(
    user_id: str, new_balance: int, plan: str,
    log_amount: int, log_type: str, reason: str, action_label: str,
) -> dict:
    """Supabase 또는 로컬에 크레딧 변경을 저장합니다."""
    if is_supabase_enabled():
        try:
            client = get_supabase()
            now = datetime.now(timezone.utc).isoformat()
            client.table('ie_credits').upsert({
                'user_id': user_id, 'balance': new_balance,
                'plan': plan, 'updated_at': now,
            }).execute()
            client.table('ie_credit_logs').insert({
                'user_id': user_id, 'amount': log_amount,
                'type': log_type, 'reason': reason, 'created_at': now,
            }).execute()
            return {'success': True, 'balance': new_balance}
        except Exception as e:
            logger.error(f"크레딧 {action_label} 실패: {e}")
            return {'success': False, 'error': str(e)}

    data = _load_local_credits()
    user_data = data.get(user_id, {'balance': 10, 'plan': 'free'})
    user_data['balance'] = new_balance
    user_data['updated_at'] = datetime.now(timezone.utc).isoformat()
    data[user_id] = user_data
    _save_local_credits(data)
    return {'success': True, 'balance': new_balance}


class CreditService:
    """크레딧 잔액 관리"""

    @staticmethod
    def get_balance(user_id: str) -> dict:
        """
        사용자 크레딧 잔액 조회

        Returns:
            {'balance': int, 'plan': str, 'updated_at': str}
        """
        if is_supabase_enabled():
            try:
                client = get_supabase()
                result = client.table('ie_credits').select('*') \
                    .eq('user_id', user_id).maybe_single().execute()
                if result.data:
                    return {
                        'balance': result.data.get('balance', 0),
                        'plan': result.data.get('plan', 'free'),
                        'updated_at': result.data.get('updated_at', ''),
                    }
            except Exception as e:
                logger.error(f"크레딧 조회 실패: {e}")

        # 로컬 폴백
        data = _load_local_credits()
        user_data = data.get(user_id, {})
        return {
            'balance': user_data.get('balance', 10),
            'plan': user_data.get('plan', 'free'),
            'updated_at': user_data.get('updated_at', ''),
        }

    @staticmethod
    def add_credits(user_id: str, amount: int, reason: str = '') -> dict:
        """
        크레딧 충전

        Args:
            user_id: 사용자 ID
            amount: 충전할 크레딧 수 (양수)
            reason: 충전 사유

        Returns:
            {'success': bool, 'balance': int}
        """
        if amount <= 0:
            return {'success': False, 'error': '충전 금액은 양수여야 합니다.'}

        with _credit_lock:
            current = CreditService.get_balance(user_id)
            new_balance = current['balance'] + amount
            return _persist_credit_change(user_id, new_balance, current['plan'], amount, 'add', reason, '충전')

    @staticmethod
    def deduct_credits(user_id: str, amount: int = 1, reason: str = '') -> dict:
        """
        크레딧 차감

        Returns:
            {'success': bool, 'balance': int}
        """
        if amount <= 0:
            return {'success': False, 'error': '차감 금액은 양수여야 합니다.'}

        with _credit_lock:
            current = CreditService.get_balance(user_id)
            if current['balance'] < amount:
                return {'success': False, 'error': '크레딧이 부족합니다.', 'balance': current['balance']}

            new_balance = current['balance'] - amount
            return _persist_credit_change(user_id, new_balance, current['plan'], -amount, 'deduct', reason, '차감')

    @staticmethod
    def check_sufficient(user_id: str, amount: int = 1) -> bool:
        """크레딧이 충분한지 확인"""
        balance = CreditService.get_balance(user_id)
        return balance['balance'] >= amount


credit_service = CreditService()
