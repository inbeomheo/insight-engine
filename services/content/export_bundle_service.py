"""
콘텐츠 내보내기 번들 서비스

콘텐츠 + 메타데이터를 JSON 패키지로 묶어 내보냅니다.
백업, 아카이브, 이관에 사용.
"""
import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import List

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r'[\w가-힣]+')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)

BUNDLE_VERSION = '1.0'


def create_bundle(contents: List[dict], bundle_name: str = '',
                  include_stats: bool = True) -> dict:
    """콘텐츠 컬렉션을 내보내기 번들로 패키징합니다.

    Args:
        contents: [{'title': str, 'content': str, 'style': str(opt), 'tags': list(opt), 'url': str(opt)}]
        bundle_name: 번들 이름 (빈 문자열이면 자동 생성)
        include_stats: 통계 포함 여부

    Returns:
        {
            'bundle': dict (직렬화 가능한 번들 객체),
            'bundle_json': str (JSON 문자열),
            'item_count': int,
            'total_chars': int,
            'checksum': str,
        }
    """
    if not contents:
        return _empty_result()

    now = datetime.now(tz=timezone.utc).isoformat()
    name = bundle_name or f'export_{datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")}'

    items = []
    total_chars = 0

    for idx, item in enumerate(contents):
        content = str(item.get('content', '') or '')
        title = str(item.get('title', f'콘텐츠 {idx + 1}') or '')
        total_chars += len(content)

        entry = {
            'id': idx + 1,
            'title': title,
            'content': content,
            'style': item.get('style', ''),
            'tags': item.get('tags', []),
            'url': item.get('url', ''),
        }

        if include_stats:
            entry['stats'] = {
                'char_count': len(content),
                'word_count': len(_WORD_PATTERN.findall(content)),
                'heading_count': len(_HEADING_PATTERN.findall(content)),
            }

        items.append(entry)

    bundle = {
        'version': BUNDLE_VERSION,
        'name': name,
        'created_at': now,
        'item_count': len(items),
        'items': items,
    }

    if include_stats:
        bundle['total_stats'] = {
            'total_chars': total_chars,
            'total_words': sum(i['stats']['word_count'] for i in items),
            'avg_chars': round(total_chars / len(items)) if items else 0,
        }

    bundle_json = json.dumps(bundle, ensure_ascii=False, indent=2)
    checksum = hashlib.sha256(bundle_json.encode('utf-8')).hexdigest()[:16]

    return {
        'bundle': bundle,
        'bundle_json': bundle_json,
        'item_count': len(items),
        'total_chars': total_chars,
        'checksum': checksum,
    }


def validate_bundle(bundle_json: str) -> dict:
    """번들 JSON의 유효성을 검증합니다.

    Returns:
        {
            'valid': bool,
            'errors': [str],
            'version': str,
            'item_count': int,
        }
    """
    errors = []

    try:
        bundle = json.loads(bundle_json)
    except (json.JSONDecodeError, TypeError) as e:
        return {'valid': False, 'errors': [f'JSON 파싱 오류: {e}'], 'version': '', 'item_count': 0}

    if not isinstance(bundle, dict):
        return {'valid': False, 'errors': ['번들이 딕셔너리가 아닙니다'], 'version': '', 'item_count': 0}

    version = bundle.get('version', '')
    if not version:
        errors.append('version 필드가 없습니다')

    items = bundle.get('items', [])
    if not isinstance(items, list):
        errors.append('items가 배열이 아닙니다')
        items = []

    for i, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f'items[{i}]가 딕셔너리가 아닙니다')
            continue
        if 'content' not in item:
            errors.append(f'items[{i}]에 content 필드가 없습니다')

    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'version': version,
        'item_count': len(items),
    }


def _empty_result() -> dict:
    empty_bundle = {
        'version': BUNDLE_VERSION,
        'name': '',
        'created_at': datetime.now(tz=timezone.utc).isoformat(),
        'item_count': 0,
        'items': [],
    }
    return {
        'bundle': empty_bundle,
        'bundle_json': json.dumps(empty_bundle, ensure_ascii=False),
        'item_count': 0,
        'total_chars': 0,
        'checksum': '',
    }
