"""
자동 목차(TOC) 생성 서비스

마크다운 헤딩(#, ##, ###)을 파싱하여 목차 마크다운을 생성합니다.
앵커 링크 포함.
"""
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _slugify(text: str) -> str:
    """헤딩 텍스트를 앵커 ID로 변환합니다."""
    # 특수문자 제거, 공백 → 하이픈
    slug = re.sub(r'[^\w\s가-힣-]', '', text)
    slug = re.sub(r'\s+', '-', slug.strip())
    return slug.lower()


def _parse_headings(markdown: str) -> List[Tuple[int, str]]:
    """마크다운에서 헤딩을 파싱합니다.

    Returns:
        [(level, text), ...] 형태의 리스트. level은 1~6.
    """
    headings = []
    for line in markdown.split('\n'):
        match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            # 마크다운 인라인 서식 제거 (**bold**, *italic*, `code`)
            text = re.sub(r'[*`~]', '', text).strip()
            if text:
                headings.append((level, text))
    return headings


def generate_toc(markdown: str, max_depth: int = 3) -> str:
    """마크다운 콘텐츠에서 목차를 생성합니다.

    Args:
        markdown: 마크다운 텍스트
        max_depth: 포함할 최대 헤딩 깊이 (기본 3, 즉 ###까지)

    Returns:
        목차 마크다운 문자열. 헤딩이 없으면 빈 문자열.
    """
    if not markdown or not markdown.strip():
        return ''

    headings = _parse_headings(markdown)
    if not headings:
        return ''

    # max_depth 이하만 포함
    filtered = [(level, text) for level, text in headings if level <= max_depth]
    if not filtered:
        return ''

    # 최소 레벨 기준으로 들여쓰기 계산
    min_level = min(level for level, _ in filtered)

    lines = ['## 목차\n']
    slug_counts = {}  # 중복 앵커 처리

    for level, text in filtered:
        indent = '  ' * (level - min_level)
        slug = _slugify(text)

        # 중복 앵커 처리
        if slug in slug_counts:
            slug_counts[slug] += 1
            slug = f'{slug}-{slug_counts[slug]}'
        else:
            slug_counts[slug] = 0

        lines.append(f'{indent}- [{text}](#{slug})')

    return '\n'.join(lines)
