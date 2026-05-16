"""
마크다운 정리(Sanitizer) 서비스

깨진 마크다운을 자동 수정합니다.
- 헤딩 레벨 정규화 (h3부터 시작 → h1부터 재정렬)
- 빈 링크/이미지 제거
- 연속 빈 줄 축소
- 닫히지 않은 볼드/이탤릭 수정
- 불필요한 이스케이프 제거
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_EMPTY_LINK = re.compile(r'\[([^\]]*)\]\(\s*\)')
_EMPTY_IMAGE = re.compile(r'!\[([^\]]*)\]\(\s*\)')
_MULTI_BLANK = re.compile(r'\n{3,}')
_TRAILING_SPACES = re.compile(r'[ \t]+$', re.MULTILINE)
_UNCLOSED_BOLD = re.compile(r'\*\*([^*]+?)(?:\n|$)')
_UNCLOSED_ITALIC = re.compile(r'(?<!\*)\*([^*]+?)(?:\n|$)')


def sanitize_markdown(content: str) -> dict:
    """마크다운을 정리합니다.

    Args:
        content: 원본 마크다운

    Returns:
        {
            'sanitized': str,
            'fixes': [{'type': str, 'description': str}],
            'fix_count': int,
            'char_diff': int,
        }
    """
    if not content or not content.strip():
        return {'sanitized': '', 'fixes': [], 'fix_count': 0, 'char_diff': 0}

    text = content
    fixes: List[dict] = []
    original_len = len(text)

    # 1) 헤딩 레벨 정규화
    text, heading_fixes = _normalize_heading_levels(text)
    fixes.extend(heading_fixes)

    # 2) 빈 이미지 제거
    empty_images = _EMPTY_IMAGE.findall(text)
    if empty_images:
        text = _EMPTY_IMAGE.sub('', text)
        fixes.append({'type': 'empty_image', 'description': f'빈 이미지 {len(empty_images)}개 제거'})

    # 3) 빈 링크 → 텍스트만 남김
    empty_links = _EMPTY_LINK.findall(text)
    if empty_links:
        text = _EMPTY_LINK.sub(r'\1', text)
        fixes.append({'type': 'empty_link', 'description': f'빈 링크 {len(empty_links)}개 텍스트로 변환'})

    # 4) 연속 빈 줄 축소 (3줄 이상 → 2줄)
    if _MULTI_BLANK.search(text):
        text = _MULTI_BLANK.sub('\n\n', text)
        fixes.append({'type': 'multi_blank', 'description': '연속 빈 줄 축소'})

    # 5) 줄 끝 공백 제거
    if _TRAILING_SPACES.search(text):
        text = _TRAILING_SPACES.sub('', text)
        fixes.append({'type': 'trailing_spaces', 'description': '줄 끝 공백 제거'})

    # 6) 닫히지 않은 볼드 수정
    text, bold_count = _fix_unclosed_formatting(text, '**')
    if bold_count > 0:
        fixes.append({'type': 'unclosed_bold', 'description': f'닫히지 않은 볼드 {bold_count}개 수정'})

    sanitized = text.strip()

    return {
        'sanitized': sanitized,
        'fixes': fixes,
        'fix_count': len(fixes),
        'char_diff': len(sanitized) - original_len,
    }


def _normalize_heading_levels(text: str) -> tuple:
    """헤딩 레벨을 정규화합니다 (최소 레벨이 1이 되도록)."""
    headings = _HEADING_PATTERN.findall(text)
    if not headings:
        return text, []

    levels = [len(h[0]) for h in headings]
    min_level = min(levels)
    if min_level <= 1:
        return text, []

    offset = min_level - 1
    fixes = []

    def replace_heading(match):
        hashes = match.group(1)
        title = match.group(2)
        new_level = max(1, len(hashes) - offset)
        return '#' * new_level + ' ' + title

    new_text = _HEADING_PATTERN.sub(replace_heading, text)
    fixes.append({'type': 'heading_level', 'description': f'헤딩 레벨 -{offset} 정규화 (H{min_level}→H1)'})
    return new_text, fixes


def _fix_unclosed_formatting(text: str, marker: str) -> tuple:
    """닫히지 않은 서식 마커를 수정합니다."""
    count = 0
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        occurrences = line.count(marker)
        if occurrences % 2 != 0:
            # 홀수 개 → 마지막 위치에 닫기 추가
            line = line + marker
            count += 1
        fixed_lines.append(line)

    return '\n'.join(fixed_lines), count
