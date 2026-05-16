"""
콘텐츠 스니펫(발췌문) 생성 서비스

SNS 미리보기, 메타 디스크립션, 공유 카드용
짧은 발췌문을 규칙 기반으로 생성합니다.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_BOLD_PATTERN = re.compile(r'\*\*(.+?)\*\*')
_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_IMAGE_PATTERN = re.compile(r'!\[.*?\]\(.*?\)')
_LIST_PREFIX = re.compile(r'^\s*[-*•]\s+|^\s*\d+[.)]\s+')

# 플랫폼별 스니펫 길이
SNIPPET_PRESETS = {
    'meta': {'max_chars': 160, 'label': '메타 디스크립션'},
    'twitter': {'max_chars': 250, 'label': '트위터 미리보기'},
    'og': {'max_chars': 200, 'label': 'OG 디스크립션'},
    'search': {'max_chars': 300, 'label': '검색 결과 미리보기'},
    'short': {'max_chars': 100, 'label': '짧은 요약'},
}


def _clean_markdown(text: str) -> str:
    """마크다운 서식을 제거하고 순수 텍스트만 남깁니다."""
    cleaned = _HEADING_PATTERN.sub('', text)
    cleaned = _IMAGE_PATTERN.sub('', cleaned)
    cleaned = _LINK_PATTERN.sub(r'\1', cleaned)
    cleaned = _BOLD_PATTERN.sub(r'\1', cleaned)
    cleaned = re.sub(r'`{1,3}[^`]*`{1,3}', '', cleaned)
    cleaned = _LIST_PREFIX.sub('', cleaned)
    cleaned = re.sub(r'\n{2,}', '\n', cleaned)
    return cleaned.strip()


def _split_sentences(text: str) -> List[str]:
    """문장 분리."""
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 5]


def _truncate_at_sentence(text: str, max_chars: int) -> str:
    """문장 경계에서 자릅니다."""
    if len(text) <= max_chars:
        return text

    sentences = _split_sentences(text)
    result = ''
    for sent in sentences:
        candidate = (result + ' ' + sent).strip() if result else sent
        if len(candidate) <= max_chars:
            result = candidate
        else:
            break

    if not result:
        # 문장 분리 실패 시 단어 경계에서 자름
        truncated = text[:max_chars]
        last_space = truncated.rfind(' ')
        if last_space > max_chars * 0.5:
            truncated = truncated[:last_space]
        result = truncated.rstrip('.,!? ') + '...'

    return result


def generate_snippet(content: str, preset: str = 'meta',
                     max_chars: int = 0) -> dict:
    """콘텐츠에서 스니펫을 생성합니다.

    Args:
        content: 원본 콘텐츠 (마크다운)
        preset: 프리셋 이름 (meta/twitter/og/search/short)
        max_chars: 커스텀 최대 길이 (0이면 프리셋 기본값)

    Returns:
        {
            'snippet': str,
            'char_count': int,
            'max_chars': int,
            'preset': str,
            'truncated': bool,
        }
    """
    if not content or not content.strip():
        return _empty_result(preset, max_chars)

    # 프리셋 또는 커스텀 길이
    preset_config = SNIPPET_PRESETS.get(preset, SNIPPET_PRESETS['meta'])
    limit = max_chars if max_chars > 0 else preset_config['max_chars']

    # 마크다운 정리
    clean = _clean_markdown(content)
    if not clean:
        return _empty_result(preset, limit)

    # 스니펫 생성 (도입부 우선)
    snippet = _truncate_at_sentence(clean, limit)
    truncated = len(clean) > limit

    return {
        'snippet': snippet,
        'char_count': len(snippet),
        'max_chars': limit,
        'preset': preset,
        'truncated': truncated,
    }


def generate_multi_snippets(content: str) -> dict:
    """모든 프리셋에 대한 스니펫을 한번에 생성합니다.

    Returns:
        {
            'snippets': {preset_id: {snippet, char_count, ...}},
            'total': int,
        }
    """
    if not content or not content.strip():
        return {'snippets': {}, 'total': 0}

    snippets = {}
    for preset_id in SNIPPET_PRESETS:
        snippets[preset_id] = generate_snippet(content, preset=preset_id)

    return {
        'snippets': snippets,
        'total': len(snippets),
    }


def get_snippet_presets() -> list:
    """사용 가능한 프리셋 목록을 반환합니다."""
    return [
        {'id': pid, 'label': config['label'], 'max_chars': config['max_chars']}
        for pid, config in SNIPPET_PRESETS.items()
    ]


def _empty_result(preset: str, max_chars: int) -> dict:
    return {
        'snippet': '',
        'char_count': 0,
        'max_chars': max_chars or SNIPPET_PRESETS.get(preset, {}).get('max_chars', 160),
        'preset': preset,
        'truncated': False,
    }
