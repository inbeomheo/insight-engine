"""
무료 체험 서비스
7일 무료 체험 시작/만료 체크
"""
import json
import os
from datetime import datetime, timedelta, timezone

from services.supabase_service import is_supabase_enabled, get_supabase
from services.logging_config import ServiceLogger

logger = ServiceLogger('TrialService')

TRIAL_DURATION_DAYS = 7

_LOCAL_TRIALS_FILE = os.path.join(
    os.path.dirname(__file__), '..', '..', 'data', 'trials.json'
)


def _load_local_trials() -> dict:
    if os.path.exists(_LOCAL_TRIALS_FILE):
        with open(_LOCAL_TRIALS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_local_trials(data: dict):
    os.makedirs(os.path.dirname(_LOCAL_TRIALS_FILE), exist_ok=True)
    with open(_LOCAL_TRIALS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class TrialService:
    """무료 체험 관리"""

    @staticmethod
    def start_trial(user_id: str) -> dict:
        """
        7일 무료 체험 시작

        Returns:
            {'success': bool, 'trial_end': str, 'already_used': bool}
        """
        # 이미 체험 사용 여부 확인
        existing = TrialService.get_trial(user_id)
        if existing.get('started'):
            return {'success': False, 'already_used': True, 'trial_end': existing.get('trial_end', '')}

        now = datetime.now(timezone.utc)
        trial_end = (now + timedelta(days=TRIAL_DURATION_DAYS)).isoformat()

        trial_data = {
            'user_id': user_id,
            'started': True,
            'trial_start': now.isoformat(),
            'trial_end': trial_end,
            'plan': 'pro',  # 체험 기간 동안 Pro 기능 사용
        }

        if is_supabase_enabled():
            try:
                client = get_supabase()
                client.table('ie_trials').upsert(trial_data).execute()
                # 체험 기간 동안 Pro 플랜 크레딧 부여
                client.table('ie_credits').upsert({
                    'user_id': user_id,
                    'plan': 'pro',
                    'updated_at': now.isoformat(),
                }).execute()
                return {'success': True, 'trial_end': trial_end}
            except Exception as e:
                logger.error(f"체험 시작 실패: {e}")
                return {'success': False, 'error': str(e)}

        # 로컬 폴백
        data = _load_local_trials()
        data[user_id] = trial_data
        _save_local_trials(data)
        return {'success': True, 'trial_end': trial_end}

    @staticmethod
    def get_trial(user_id: str) -> dict:
        """체험 정보 조회"""
        if is_supabase_enabled():
            try:
                client = get_supabase()
                result = client.table('ie_trials').select('*') \
                    .eq('user_id', user_id).maybe_single().execute()
                if result.data:
                    return result.data
            except Exception as e:
                logger.error(f"체험 조회 실패: {e}")

        data = _load_local_trials()
        return data.get(user_id, {'started': False})

    @staticmethod
    def is_trial_active(user_id: str) -> bool:
        """체험 기간이 유효한지 확인"""
        trial = TrialService.get_trial(user_id)
        if not trial.get('started'):
            return False

        trial_end = trial.get('trial_end', '')
        if not trial_end:
            return False

        try:
            end_dt = datetime.fromisoformat(trial_end)
            return datetime.now(timezone.utc) < end_dt
        except (ValueError, TypeError):
            return False

    @staticmethod
    def get_remaining_days(user_id: str) -> int:
        """남은 체험 일수"""
        trial = TrialService.get_trial(user_id)
        if not trial.get('started'):
            return 0

        trial_end = trial.get('trial_end', '')
        try:
            end_dt = datetime.fromisoformat(trial_end)
            remaining = (end_dt - datetime.now(timezone.utc)).days
            return max(0, remaining)
        except (ValueError, TypeError):
            return 0


trial_service = TrialService()
