"""
예산 인지형 멀티모델 게이트웨이 - 프로바이더별 예산 관리 + 자동 fallback

프로바이더별 일일/월간 예산 한도를 설정하고,
예산 초과 시 저렴한 모델로 자동 fallback하는 게이트웨이.
"""
import time
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class SpendRecord:
    """지출 기록"""
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost: float
    timestamp: float


@dataclass
class BudgetLimit:
    """예산 한도"""
    provider: str
    daily_limit: float   # USD
    monthly_limit: float  # USD


@dataclass
class BudgetReport:
    """예산 현황 보고서"""
    provider: str
    daily_spent: float
    daily_limit: float
    daily_remaining: float
    monthly_spent: float
    monthly_limit: float
    monthly_remaining: float


@dataclass
class ProviderChoice:
    """라우팅 결정 결과"""
    provider: str
    model: str
    reason: str  # 'primary', 'budget_fallback', 'quality_match'


# === 모듈 레벨 저장소 ===

_budget_limits: Dict[str, BudgetLimit] = {}
_spend_records: List[SpendRecord] = []

# 프로바이더별 기본 모델 + 가격 (config.SUPPORTED_PROVIDERS 기반, per M tokens)
_PROVIDER_MODELS: Dict[str, Dict] = {
    'gemini': {
        'model': 'gemini/gemini-3.1-flash-lite-preview',
        'price_input': 0.075,   # $ per 1M tokens
        'price_output': 0.30,
        'quality': 'high',
    },
    'deepseek': {
        'model': 'deepseek/deepseek-chat',
        'price_input': 0.27,
        'price_output': 1.10,
        'quality': 'high',
    },
    'zhipuai': {
        'model': 'zhipuai/GLM-4.5-Air',
        'price_input': 0.10,
        'price_output': 0.10,
        'quality': 'medium',
    },
    'ollama': {
        'model': 'ollama_chat/llama3.2',
        'price_input': 0.0,
        'price_output': 0.0,
        'quality': 'low',
    },
}

# 품질 등급 순서 (높은 순)
_QUALITY_ORDER = {'high': 2, 'medium': 1, 'low': 0}


def _get_day_start() -> float:
    """오늘 자정(UTC) 타임스탬프"""
    now = time.time()
    # 현재 시각의 날짜 시작 (초 단위)
    import calendar
    import datetime
    today = datetime.date.today()
    return calendar.timegm(today.timetuple())


def _get_month_start() -> float:
    """이번 달 1일 자정(UTC) 타임스탬프"""
    import calendar
    import datetime
    today = datetime.date.today()
    first_day = today.replace(day=1)
    return calendar.timegm(first_day.timetuple())


def _calc_spent(provider: str, since: float) -> float:
    """특정 시점 이후 프로바이더 지출 합계"""
    return sum(
        r.cost for r in _spend_records
        if r.provider == provider and r.timestamp >= since
    )


def set_budget_limits(provider: str, daily_limit: float, monthly_limit: float) -> BudgetLimit:
    """프로바이더별 예산 한도 설정

    Args:
        provider: 프로바이더 ID (예: 'gemini', 'deepseek')
        daily_limit: 일일 한도 (USD)
        monthly_limit: 월간 한도 (USD)

    Returns:
        설정된 BudgetLimit
    """
    limit = BudgetLimit(
        provider=provider,
        daily_limit=daily_limit,
        monthly_limit=monthly_limit,
    )
    _budget_limits[provider] = limit
    logger.info("예산 한도 설정: %s — 일일 $%.2f, 월간 $%.2f", provider, daily_limit, monthly_limit)
    return limit


def track_spend(
    provider: str,
    model: str,
    tokens_in: int,
    tokens_out: int,
    price_per_input: float = 0,
    price_per_output: float = 0,
) -> SpendRecord:
    """사용량 기록 및 비용 계산

    Args:
        provider: 프로바이더 ID
        model: 모델 ID
        tokens_in: 입력 토큰 수
        tokens_out: 출력 토큰 수
        price_per_input: 입력 토큰 가격 ($ per 1M tokens)
        price_per_output: 출력 토큰 가격 ($ per 1M tokens)

    Returns:
        생성된 SpendRecord
    """
    cost = (tokens_in * price_per_input + tokens_out * price_per_output) / 1_000_000
    record = SpendRecord(
        provider=provider,
        model=model,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost=cost,
        timestamp=time.time(),
    )
    _spend_records.append(record)
    logger.debug("지출 기록: %s/%s — $%.6f (in=%d, out=%d)", provider, model, cost, tokens_in, tokens_out)
    return record


def get_budget_status(provider: str = None) -> List[BudgetReport]:
    """잔여 예산 조회

    Args:
        provider: 특정 프로바이더만 조회. None이면 전체.

    Returns:
        BudgetReport 목록
    """
    day_start = _get_day_start()
    month_start = _get_month_start()

    providers = [provider] if provider else list(_budget_limits.keys())
    reports = []

    for p in providers:
        limit = _budget_limits.get(p)
        if not limit:
            continue

        daily_spent = _calc_spent(p, day_start)
        monthly_spent = _calc_spent(p, month_start)

        reports.append(BudgetReport(
            provider=p,
            daily_spent=round(daily_spent, 6),
            daily_limit=limit.daily_limit,
            daily_remaining=round(max(0, limit.daily_limit - daily_spent), 6),
            monthly_spent=round(monthly_spent, 6),
            monthly_limit=limit.monthly_limit,
            monthly_remaining=round(max(0, limit.monthly_limit - monthly_spent), 6),
        ))

    return reports


def get_total_spend(period: str = 'daily') -> float:
    """기간별 총 지출 합계

    Args:
        period: 'daily' 또는 'monthly'

    Returns:
        총 지출 (USD)
    """
    if period == 'daily':
        since = _get_day_start()
    elif period == 'monthly':
        since = _get_month_start()
    else:
        since = 0  # 전체 기간

    total = sum(r.cost for r in _spend_records if r.timestamp >= since)
    return round(total, 6)


def reset_daily_spend() -> None:
    """일일 지출 기록 초기화 (오늘 자정 이후 기록만 삭제)"""
    day_start = _get_day_start()
    # in-place 필터링으로 참조 유지
    _spend_records[:] = [r for r in _spend_records if r.timestamp < day_start]
    logger.info("일일 지출 기록 초기화 완료")


def get_cheapest_provider(min_quality: str = 'medium') -> Optional[str]:
    """최저가 프로바이더 조회

    Args:
        min_quality: 최소 품질 등급 ('low', 'medium', 'high')

    Returns:
        가장 저렴한 프로바이더 ID. 조건에 맞는 프로바이더가 없으면 None.
    """
    min_q = _QUALITY_ORDER.get(min_quality, 0)
    candidates = []

    for provider_id, info in _PROVIDER_MODELS.items():
        q = _QUALITY_ORDER.get(info['quality'], 0)
        if q >= min_q:
            # 출력 가격 기준 정렬 (보통 출력이 비용의 주요 부분)
            candidates.append((provider_id, info['price_output']))

    if not candidates:
        return None

    # 가격 오름차순 정렬
    candidates.sort(key=lambda x: x[1])
    return candidates[0][0]


def _is_budget_exceeded(provider: str) -> bool:
    """프로바이더 예산 초과 여부 확인"""
    limit = _budget_limits.get(provider)
    if not limit:
        return False  # 한도 미설정 = 무제한

    day_start = _get_day_start()
    month_start = _get_month_start()

    daily_spent = _calc_spent(provider, day_start)
    monthly_spent = _calc_spent(provider, month_start)

    return daily_spent >= limit.daily_limit or monthly_spent >= limit.monthly_limit


def route_request(
    prompt_tokens: int,
    preferred_provider: str = None,
    budget_config: dict = None,
) -> ProviderChoice:
    """비용/품질 기반 프로바이더 라우팅

    예산 초과 시 저렴한 프로바이더로 자동 fallback.

    Args:
        prompt_tokens: 예상 프롬프트 토큰 수
        preferred_provider: 선호 프로바이더 (None이면 gemini)
        budget_config: 즉석 예산 설정 {'daily_limit': float, 'monthly_limit': float}

    Returns:
        ProviderChoice (선택된 프로바이더/모델/이유)
    """
    provider = preferred_provider or 'gemini'

    # 즉석 예산 설정 적용
    if budget_config and provider:
        set_budget_limits(
            provider,
            daily_limit=budget_config.get('daily_limit', float('inf')),
            monthly_limit=budget_config.get('monthly_limit', float('inf')),
        )

    # 1) 선호 프로바이더가 예산 내이면 바로 반환
    if provider in _PROVIDER_MODELS and not _is_budget_exceeded(provider):
        info = _PROVIDER_MODELS[provider]
        return ProviderChoice(
            provider=provider,
            model=info['model'],
            reason='primary',
        )

    # 2) 예산 초과 → 저렴한 프로바이더로 fallback
    logger.warning("프로바이더 '%s' 예산 초과 — fallback 탐색", provider)

    # 가격 오름차순으로 예산 여유 있는 프로바이더 탐색
    fallback_candidates = sorted(
        _PROVIDER_MODELS.items(),
        key=lambda x: x[1]['price_output'],
    )

    for fb_provider, fb_info in fallback_candidates:
        if fb_provider == provider:
            continue  # 원래 프로바이더 건너뛰기
        if not _is_budget_exceeded(fb_provider):
            logger.info("Fallback 선택: %s (원래: %s)", fb_provider, provider)
            return ProviderChoice(
                provider=fb_provider,
                model=fb_info['model'],
                reason='budget_fallback',
            )

    # 3) 모든 프로바이더 예산 초과 → 가장 저렴한 프로바이더 강제 선택
    cheapest = get_cheapest_provider(min_quality='low')
    if cheapest:
        info = _PROVIDER_MODELS[cheapest]
        return ProviderChoice(
            provider=cheapest,
            model=info['model'],
            reason='budget_fallback',
        )

    # 4) 최후 폴백: 기본 gemini
    return ProviderChoice(
        provider='gemini',
        model=_PROVIDER_MODELS['gemini']['model'],
        reason='primary',
    )


def _reset_all() -> None:
    """테스트용: 모든 내부 상태 초기화 (in-place clear로 참조 유지)"""
    _budget_limits.clear()
    _spend_records.clear()
