"""
비교표 자동 생성 서비스

항목별 비교 데이터를 마크다운 테이블로 변환합니다.
"""
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def generate_comparison(items: List[Dict]) -> str:
    """항목 목록을 비교표 마크다운으로 변환합니다.

    Args:
        items: 비교 항목 목록. 각 항목은 동일한 키 구조를 가진 dict.
               예: [{"name": "A", "price": "10", "features": "..."}, ...]

    Returns:
        마크다운 테이블 문자열

    Raises:
        ValueError: items가 비어 있거나 형식 오류
    """
    if not items:
        raise ValueError('비교할 항목 목록이 비어 있습니다.')
    if len(items) < 2:
        raise ValueError('최소 2개 이상의 항목이 필요합니다.')

    all_keys = _collect_ordered_keys(items)
    if not all_keys:
        raise ValueError('비교 항목에 데이터가 없습니다.')

    name_key = 'name' if 'name' in all_keys else None
    value_keys = [k for k in all_keys if k != name_key]
    headers = _build_headers(items, name_key)

    return _render_table(headers, value_keys, items)


def _collect_ordered_keys(items: List[Dict]) -> List[str]:
    """모든 항목에서 키를 순서 유지하며 수집합니다."""
    all_keys = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('각 항목은 딕셔너리여야 합니다.')
        for key in item:
            if key not in seen:
                all_keys.append(key)
                seen.add(key)
    return all_keys


def _build_headers(items: List[Dict], name_key: str | None) -> List[str]:
    """테이블 헤더 행을 구성합니다."""
    if name_key:
        return ['기준'] + [item.get(name_key, f'항목 {i+1}') for i, item in enumerate(items)]
    return ['기준'] + [f'항목 {i+1}' for i in range(len(items))]


def _render_table(headers: List[str], value_keys: List[str], items: List[Dict]) -> str:
    """마크다운 테이블 문자열을 생성합니다."""
    lines = [
        '| ' + ' | '.join(headers) + ' |',
        '| ' + ' | '.join(['---'] * len(headers)) + ' |',
    ]
    for key in value_keys:
        row = [key] + [str(item.get(key, '-')) for item in items]
        lines.append('| ' + ' | '.join(row) + ' |')
    return '\n'.join(lines)
