"""
제목(Heading) 계층 검증 서비스

마크다운 문서의 제목 구조(H1~H6)를 검증하여 SEO/접근성 관점에서
문제가 되는 패턴을 탐지합니다.

탐지 항목:
- H1 다수 사용 (권장: 1개)
- 레벨 점프 (예: H2 → H4)
- 빈 제목
- 과도하게 긴/짧은 제목
- 중복 제목
- 첫 제목이 H1이 아님
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# `# ` 형태(텍스트 없음)도 허용하여 빈 제목을 감지할 수 있게 함
_HEADING_PATTERN = re.compile(r'^(#{1,6})\s*(.*?)\s*$', re.MULTILINE)

# 설정 상수
MIN_TITLE_LENGTH = 3
MAX_TITLE_LENGTH = 80
DEFAULT_MAX_H1 = 1


def validate_heading_hierarchy(
    content: str,
    max_h1: int = DEFAULT_MAX_H1,
    min_title_length: int = MIN_TITLE_LENGTH,
    max_title_length: int = MAX_TITLE_LENGTH,
) -> dict:
    """마크다운 콘텐츠의 제목 계층을 검증합니다.

    Args:
        content: 마크다운 원문.
        max_h1: 허용 H1 최대 개수. 기본 1.
        min_title_length: 제목 최소 길이. 기본 3.
        max_title_length: 제목 최대 길이. 기본 80.

    Returns:
        {
            'valid': bool,
            'score': int,           # 0~100 (100 = 모든 검증 통과)
            'heading_count': int,
            'by_level': {'h1': n, 'h2': n, ...},
            'issues': [{'type': str, 'level': int, 'line': int,
                        'text': str, 'severity': 'error'|'warning'}],
            'outline': [{'level': int, 'text': str, 'line': int}],
        }
    """
    headings = _extract_headings(content)

    if not headings:
        return {
            'valid': True,
            'score': 100,
            'heading_count': 0,
            'by_level': {f'h{i}': 0 for i in range(1, 7)},
            'issues': [],
            'outline': [],
        }

    issues: List[dict] = []
    by_level = {f'h{i}': 0 for i in range(1, 7)}
    for h in headings:
        by_level[f'h{h["level"]}'] += 1

    # 1) H1 다수 검증
    if by_level['h1'] > max_h1:
        for h in headings:
            if h['level'] == 1:
                issues.append({
                    'type': 'multiple_h1',
                    'level': 1,
                    'line': h['line'],
                    'text': h['text'],
                    'severity': 'error',
                    'message': f"H1은 {max_h1}개만 허용됩니다. (현재 {by_level['h1']}개)",
                })

    # 2) 레벨 점프 검증 (H1 → H3 같은 점프)
    prev_level = 0
    for h in headings:
        if prev_level and h['level'] > prev_level + 1:
            issues.append({
                'type': 'level_jump',
                'level': h['level'],
                'line': h['line'],
                'text': h['text'],
                'severity': 'warning',
                'message': f'H{prev_level} 다음에 H{h["level"]}가 나와 레벨이 건너뛰어졌습니다.',
            })
        prev_level = h['level']

    # 3) 첫 제목이 H1이 아닌 경우
    if headings[0]['level'] != 1:
        issues.append({
            'type': 'missing_h1',
            'level': headings[0]['level'],
            'line': headings[0]['line'],
            'text': headings[0]['text'],
            'severity': 'warning',
            'message': f'문서가 H{headings[0]["level"]}로 시작합니다. H1로 시작하는 것이 권장됩니다.',
        })

    # 4) 빈 제목 / 길이 이상
    for h in headings:
        text_len = len(h['text'].strip())
        if text_len == 0:
            issues.append({
                'type': 'empty_heading',
                'level': h['level'],
                'line': h['line'],
                'text': '',
                'severity': 'error',
                'message': '빈 제목이 감지되었습니다.',
            })
        elif text_len < min_title_length:
            issues.append({
                'type': 'too_short',
                'level': h['level'],
                'line': h['line'],
                'text': h['text'],
                'severity': 'warning',
                'message': f'제목이 너무 짧습니다 ({text_len}자, 최소 {min_title_length}자).',
            })
        elif text_len > max_title_length:
            issues.append({
                'type': 'too_long',
                'level': h['level'],
                'line': h['line'],
                'text': h['text'],
                'severity': 'warning',
                'message': f'제목이 너무 깁니다 ({text_len}자, 최대 {max_title_length}자).',
            })

    # 5) 중복 제목
    seen = {}
    for h in headings:
        key = h['text'].strip().lower()
        if not key:
            continue
        if key in seen:
            issues.append({
                'type': 'duplicate',
                'level': h['level'],
                'line': h['line'],
                'text': h['text'],
                'severity': 'warning',
                'message': f'중복된 제목입니다 (최초 등장: {seen[key]}행).',
            })
        else:
            seen[key] = h['line']

    score = _calculate_score(issues)
    # 에러가 있으면 invalid, 경고만 있으면 valid
    valid = not any(i['severity'] == 'error' for i in issues)

    return {
        'valid': valid,
        'score': score,
        'heading_count': len(headings),
        'by_level': by_level,
        'issues': issues,
        'outline': [
            {'level': h['level'], 'text': h['text'], 'line': h['line']}
            for h in headings
        ],
    }


def _extract_headings(content: str) -> List[dict]:
    """콘텐츠에서 모든 제목을 추출합니다.

    코드 블록 안의 '#'은 제목이 아니므로 제외합니다.
    """
    if not content:
        return []

    # 코드 블록 영역 표시 (단순 상태 머신)
    lines = content.split('\n')
    in_code = False
    headings = []

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_code = not in_code
            continue
        if in_code:
            continue

        match = _HEADING_PATTERN.match(line)
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            headings.append({'level': level, 'text': text, 'line': idx})

    return headings


def _calculate_score(issues: List[dict]) -> int:
    """이슈 개수와 심각도에 따라 점수를 계산합니다."""
    if not issues:
        return 100

    penalty = 0
    for issue in issues:
        if issue['severity'] == 'error':
            penalty += 15
        else:  # warning
            penalty += 5

    return max(0, 100 - penalty)


def get_outline_markdown(content: str, indent_char: str = '  ') -> str:
    """콘텐츠의 제목 계층을 마크다운 목차로 변환합니다."""
    headings = _extract_headings(content)
    if not headings:
        return ''

    min_level = min(h['level'] for h in headings)
    lines = []
    for h in headings:
        indent = indent_char * (h['level'] - min_level)
        lines.append(f'{indent}- {h["text"]}')
    return '\n'.join(lines)
