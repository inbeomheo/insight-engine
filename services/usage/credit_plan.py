"""
크레딧 플랜 정의
Free / Pro / Team 플랜별 크레딧 한도와 기능
"""
from typing import Any

# 플랜 정의
CREDIT_PLANS: dict[str, dict[str, Any]] = {
    'free': {
        'name': 'Free',
        'credits_per_day': 10,
        'price_monthly': 0,
        'price_yearly': 0,
        'features': [
            '일일 10회 생성',
            '기본 스타일 5종',
            '최대 1개 워크스페이스',
        ],
    },
    'pro': {
        'name': 'Pro',
        'credits_per_day': 100,
        'price_monthly': 9900,   # 원화 (KRW)
        'price_yearly': 99000,
        'features': [
            '일일 100회 생성',
            '전체 스타일 14종',
            '최대 5개 워크스페이스',
            '우선 처리',
            'API 키 발급',
        ],
    },
    'team': {
        'name': 'Team',
        'credits_per_day': 500,
        'price_monthly': 29900,
        'price_yearly': 299000,
        'features': [
            '일일 500회 생성',
            '전체 스타일 14종',
            '무제한 워크스페이스',
            '우선 처리',
            'API 키 발급',
            '팀 멤버 관리',
            '관리자 대시보드',
        ],
    },
}


def get_plan_credits(plan_name: str) -> int:
    """플랜별 일일 크레딧 수 반환"""
    plan = CREDIT_PLANS.get(plan_name, CREDIT_PLANS['free'])
    return plan['credits_per_day']


def get_plan_features(plan_name: str) -> list[str]:
    """플랜별 기능 목록 반환"""
    plan = CREDIT_PLANS.get(plan_name, CREDIT_PLANS['free'])
    return plan['features']


def get_plan_price(plan_name: str, period: str = 'monthly') -> int:
    """플랜 가격 반환 (KRW)"""
    plan = CREDIT_PLANS.get(plan_name, CREDIT_PLANS['free'])
    key = f'price_{period}'
    return plan.get(key, 0)


def get_all_plans() -> dict:
    """모든 플랜 정보 반환 (UI용)"""
    return CREDIT_PLANS
