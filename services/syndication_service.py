"""
콘텐츠 신디케이션 서비스

하나의 콘텐츠를 여러 플랫폼(Twitter, LinkedIn, Instagram, Blog 등)에
맞게 자동 변환합니다. 글자 수 제한, 해시태그, 포맷 등을 플랫폼별로 적용합니다.
"""
import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class SyndicationResult:
    """플랫폼별 변환 결과"""
    platform: str
    adapted_content: str
    character_count: int
    status: str  # 'ok', 'truncated', 'error'


# 플랫폼별 제한 및 규칙
_PLATFORM_CONFIG = {
    'twitter': {
        'max_chars': 280,
        'hashtag_limit': 3,
        'strip_markdown': True,
        'add_thread_hint': True,
    },
    'linkedin': {
        'max_chars': 3000,
        'hashtag_limit': 5,
        'strip_markdown': True,
        'add_thread_hint': False,
    },
    'instagram': {
        'max_chars': 2200,
        'hashtag_limit': 30,
        'strip_markdown': True,
        'add_thread_hint': False,
    },
    'threads': {
        'max_chars': 500,
        'hashtag_limit': 5,
        'strip_markdown': True,
        'add_thread_hint': False,
    },
    'blog': {
        'max_chars': 50000,
        'hashtag_limit': 10,
        'strip_markdown': False,
        'add_thread_hint': False,
    },
    'newsletter': {
        'max_chars': 10000,
        'hashtag_limit': 0,
        'strip_markdown': True,
        'add_thread_hint': False,
    },
}


def _strip_markdown(text: str) -> str:
    """마크다운 서식을 제거합니다."""
    # 헤더 → 일반 텍스트
    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)
    # 볼드/이탤릭
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    # 링크 → 텍스트(URL)
    text = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'\1 (\2)', text)
    # 코드 블록 제거
    text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
    text = re.sub(r'`(.+?)`', r'\1', text)
    # 리스트 마커
    text = re.sub(r'^[-*]\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()


def _extract_keywords(content: str, limit: int) -> list:
    """콘텐츠에서 키워드를 추출하여 해시태그로 반환합니다."""
    if limit <= 0:
        return []
    # 간단한 키워드 추출: 자주 나오는 2자 이상 단어
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', content)
    from collections import Counter
    # 불용어 제거
    stopwords = {'그리고', '하지만', '그래서', '때문에', '있는', '없는', '하는', '되는',
                 'the', 'and', 'for', 'that', 'this', 'with', 'from', 'are', 'was'}
    filtered = [w for w in words if w.lower() not in stopwords]
    counter = Counter(filtered)
    top = [word for word, _ in counter.most_common(limit)]
    return [f'#{w}' for w in top]


def _truncate_with_ellipsis(text: str, max_chars: int) -> tuple:
    """글자 수 제한에 맞게 자르고 상태를 반환합니다."""
    if len(text) <= max_chars:
        return text, 'ok'
    # 단어 경계에서 자르기
    truncated = text[:max_chars - 3]
    last_space = truncated.rfind(' ')
    last_newline = truncated.rfind('\n')
    cut_point = max(last_space, last_newline)
    if cut_point > max_chars // 2:
        truncated = truncated[:cut_point]
    return truncated.rstrip() + '...', 'truncated'


def _adapt_for_platform(content: str, platform: str, config: dict) -> SyndicationResult:
    """단일 플랫폼에 맞게 콘텐츠를 변환합니다."""
    adapted = content

    # 마크다운 제거
    if config.get('strip_markdown'):
        adapted = _strip_markdown(adapted)

    # 해시태그 추가
    hashtag_limit = config.get('hashtag_limit', 0)
    hashtags = _extract_keywords(content, hashtag_limit)

    # 글자 수 제한 (해시태그 공간 확보)
    max_chars = config['max_chars']
    hashtag_text = ' '.join(hashtags)
    available_chars = max_chars - len(hashtag_text) - (2 if hashtags else 0)

    adapted, status = _truncate_with_ellipsis(adapted, max(available_chars, 50))

    # 해시태그 추가
    if hashtags:
        adapted = adapted + '\n\n' + hashtag_text

    # 트위터 스레드 힌트
    if config.get('add_thread_hint') and len(content) > max_chars:
        adapted = adapted.rstrip()
        if not adapted.endswith('...'):
            adapted += '...'
        adapted += '\n\n🧵 (1/n)'
        status = 'truncated'

    return SyndicationResult(
        platform=platform,
        adapted_content=adapted.strip(),
        character_count=len(adapted.strip()),
        status=status,
    )


def syndicate_content(content: str, platforms: list) -> list:
    """콘텐츠를 여러 플랫폼에 맞게 변환합니다.

    Args:
        content: 원본 콘텐츠 (마크다운 또는 플레인 텍스트)
        platforms: 대상 플랫폼 리스트 (예: ['twitter', 'linkedin', 'blog'])

    Returns:
        SyndicationResult 리스트
    """
    if not content:
        return [
            SyndicationResult(
                platform=p,
                adapted_content='',
                character_count=0,
                status='error',
            )
            for p in (platforms or [])
        ]

    results = []
    for platform in (platforms or []):
        platform_lower = platform.strip().lower()
        config = _PLATFORM_CONFIG.get(platform_lower)
        if not config:
            results.append(SyndicationResult(
                platform=platform,
                adapted_content=content,
                character_count=len(content),
                status='error',
            ))
            logger.warning(f"미지원 플랫폼: {platform}")
            continue

        result = _adapt_for_platform(content, platform_lower, config)
        results.append(result)

    return results
