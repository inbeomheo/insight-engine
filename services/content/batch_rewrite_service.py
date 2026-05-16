"""
일괄 플랫폼 리라이트 서비스

콘텐츠를 여러 플랫폼 형식으로 동시에 변환합니다.
기존 rewrite_service를 내부적으로 활용하되,
ThreadPoolExecutor로 병렬 처리합니다.
"""
import concurrent.futures
import logging
import time

from services.content.rewrite_service import rewrite_for_platform, get_platform_limits
from config import PLATFORM_PRESETS

logger = logging.getLogger(__name__)

MAX_PLATFORMS = 6
MAX_WORKERS = 3
TIMEOUT_SECONDS = 60

# 플랫폼 그룹 프리셋
PLATFORM_GROUPS = {
    'social': ['twitter', 'instagram', 'threads'],
    'professional': ['linkedin'],
    'all': list(PLATFORM_PRESETS.keys()),
}


def get_available_platforms() -> list:
    """지원 플랫폼 목록을 반환합니다."""
    return [
        {
            'id': pid,
            'label': pid.capitalize(),
            'max_chars': preset['max_chars'],
            'tone': preset['tone'],
            'icon_emoji': preset.get('icon_emoji', '📝'),
        }
        for pid, preset in PLATFORM_PRESETS.items()
    ]


def get_platform_groups() -> dict:
    """플랫폼 그룹 프리셋을 반환합니다."""
    return {
        group: {
            'platforms': platforms,
            'count': len(platforms),
        }
        for group, platforms in PLATFORM_GROUPS.items()
    }


def _rewrite_single(content: str, platform: str, model: str) -> dict:
    """단일 플랫폼 리라이트 (에러 래핑)."""
    try:
        result = rewrite_for_platform(content, platform, model)
        result['status'] = 'error' if 'error' in result else 'success'
        return result
    except Exception as e:
        logger.error(f"배치 리라이트 실패 ({platform}): {e}")
        return {
            'platform': platform,
            'status': 'error',
            'error': f'{platform} 변환 중 오류 발생',
        }


def batch_rewrite(content: str, platforms: list, model: str) -> dict:
    """콘텐츠를 여러 플랫폼으로 동시 변환합니다.

    Args:
        content: 원본 콘텐츠
        platforms: 변환할 플랫폼 ID 목록 (예: ['twitter', 'linkedin'])
                   또는 그룹명 (예: ['social'])
        model: AI 모델 ID

    Returns:
        {
            'results': [{'platform': str, 'text': str, ...}, ...],
            'success_count': int,
            'error_count': int,
            'total': int,
            'elapsed_ms': int,
        }
    """
    if not content or not content.strip():
        return {'error': '콘텐츠가 비어 있습니다.'}

    if not platforms:
        return {'error': '플랫폼을 최소 1개 이상 지정해주세요.'}

    # 그룹명 → 개별 플랫폼 확장
    expanded = _expand_platforms(platforms)
    if not expanded:
        return {'error': f'유효한 플랫폼이 없습니다. 지원: {list(PLATFORM_PRESETS.keys())}'}

    # 최대 플랫폼 수 제한
    if len(expanded) > MAX_PLATFORMS:
        expanded = expanded[:MAX_PLATFORMS]

    start = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_platform = {
            executor.submit(_rewrite_single, content, p, model): p
            for p in expanded
        }
        for future in concurrent.futures.as_completed(future_to_platform, timeout=TIMEOUT_SECONDS):
            results.append(future.result())

    # 플랫폼 순서대로 정렬
    platform_order = {p: i for i, p in enumerate(expanded)}
    results.sort(key=lambda r: platform_order.get(r.get('platform', ''), 999))

    success_count = sum(1 for r in results if r.get('status') == 'success')
    elapsed_ms = int((time.time() - start) * 1000)

    return {
        'results': results,
        'success_count': success_count,
        'error_count': len(results) - success_count,
        'total': len(results),
        'elapsed_ms': elapsed_ms,
    }


def _expand_platforms(platforms: list) -> list:
    """그룹명이 포함된 경우 개별 플랫폼으로 확장합니다."""
    expanded = []
    seen = set()
    for p in platforms:
        p_lower = p.lower().strip()
        if p_lower in PLATFORM_GROUPS:
            for sub in PLATFORM_GROUPS[p_lower]:
                if sub not in seen:
                    expanded.append(sub)
                    seen.add(sub)
        elif p_lower in PLATFORM_PRESETS:
            if p_lower not in seen:
                expanded.append(p_lower)
                seen.add(p_lower)
    return expanded
