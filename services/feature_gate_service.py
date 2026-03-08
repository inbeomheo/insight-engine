"""
기능 제한 서비스 (F4-18)
플랜별 기능 접근 제어 데코레이터
"""
from functools import wraps
from typing import Callable
from flask import g, jsonify
from services.logging_config import ServiceLogger

logger = ServiceLogger('FeatureGateService')

# 플랜별 기능 매핑
PLAN_FEATURES: dict[str, set[str]] = {
    'free': {
        'generate', 'history', 'export_markdown',
    },
    'starter': {
        'generate', 'history', 'export_markdown', 'export_docx',
        'multi_style', 'custom_style', 'rag',
    },
    'pro': {
        'generate', 'history', 'export_markdown', 'export_docx', 'export_pdf',
        'multi_style', 'custom_style', 'rag', 'pipeline',
        'tts', 'image_gen', 'whitelabel', 'api_access',
    },
    'enterprise': {
        'generate', 'history', 'export_markdown', 'export_docx', 'export_pdf',
        'multi_style', 'custom_style', 'rag', 'pipeline',
        'tts', 'image_gen', 'whitelabel', 'api_access',
        'sso', 'audit_log', 'team_billing', 'custom_model',
    },
}


class FeatureGateService:
    """플랜별 기능 접근 제어"""

    def __init__(self, plan_features: dict[str, set[str]] | None = None):
        self._plan_features = plan_features or PLAN_FEATURES
        # user_id → plan_id 매핑 (프로덕션에서는 DB)
        self._user_plans: dict[str, str] = {}

    def set_user_plan(self, user_id: str, plan_id: str) -> None:
        """사용자 플랜 설정"""
        self._user_plans[user_id] = plan_id

    def get_user_plan(self, user_id: str) -> str:
        """사용자 플랜 조회 (기본: free)"""
        return self._user_plans.get(user_id, 'free')

    def can_access(self, user_id: str, feature: str) -> bool:
        """기능 접근 가능 여부"""
        plan = self.get_user_plan(user_id)
        features = self._plan_features.get(plan, set())
        return feature in features

    def get_available_features(self, user_id: str) -> list[str]:
        """사용자가 접근 가능한 기능 목록"""
        plan = self.get_user_plan(user_id)
        return sorted(self._plan_features.get(plan, set()))

    def get_plan_features(self, plan_id: str) -> list[str]:
        """플랜의 기능 목록"""
        return sorted(self._plan_features.get(plan_id, set()))


feature_gate_service = FeatureGateService()


def require_feature(feature: str) -> Callable:
    """기능 접근 제한 데코레이터

    Usage:
        @require_feature('tts')
        def tts_endpoint(): ...
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = getattr(g, 'user_id', None)
            if not user_id:
                return jsonify({'error': '인증이 필요합니다.'}), 401

            if not feature_gate_service.can_access(user_id, feature):
                plan = feature_gate_service.get_user_plan(user_id)
                return jsonify({
                    'error': f'현재 플랜({plan})에서는 이 기능을 사용할 수 없습니다.',
                    'required_feature': feature,
                    'current_plan': plan,
                }), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator
