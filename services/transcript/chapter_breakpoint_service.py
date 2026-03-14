"""
Chapter Breakpoint Detector 서비스

긴 콘텐츠에서 챕터/섹션 분할이 필요한 지점을 감지합니다.
주제 전환, 긴 연속 텍스트 등을 기준으로 분할점을 제안합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 마크다운 헤딩
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 주제 전환 신호 (한국어)
_TRANSITION_PATTERNS_KO = [
    re.compile(r'(?:한편|반면|그런데|그러나|하지만|다른\s*(?:한편|측면)|이와\s*(?:달리|반대로))'),
    re.compile(r'(?:다음으로|이제|이번에는|또한|나아가|더불어)'),
    re.compile(r'(?:지금까지|앞서|위에서)\s*(?:살펴본|다룬|설명한)'),
]

# 주제 전환 신호 (영어)
_TRANSITION_PATTERNS_EN = [
    re.compile(r'\b(?:However|Meanwhile|On the other hand|In contrast|Conversely)\b'),
    re.compile(r'\b(?:Moving on|Next|Furthermore|Additionally|Moreover)\b'),
    re.compile(r'\b(?:As mentioned|As discussed|As noted)\s+(?:above|earlier|before)\b', re.IGNORECASE),
]

# 섹션 길이 임계값 (자)
_LONG_SECTION_THRESHOLD = 800
_VERY_LONG_SECTION_THRESHOLD = 1500

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n\n+')


def _parse_sections(content: str) -> List[Dict]:
    """헤딩 기준으로 섹션을 파싱합니다."""
    lines = content.split('\n')
    sections = []
    current = {'heading': None, 'level': 0, 'lines': [], 'start_line': 0}

    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line.strip())
        if m:
            if current['lines'] or current['heading']:
                text = '\n'.join(current['lines']).strip()
                current['text'] = text
                current['char_count'] = len(text)
                sections.append(current)
            current = {
                'heading': m.group(2).strip(),
                'level': len(m.group(1)),
                'lines': [],
                'start_line': i,
            }
        else:
            current['lines'].append(line)

    # 마지막 섹션
    text = '\n'.join(current['lines']).strip()
    current['text'] = text
    current['char_count'] = len(text)
    sections.append(current)

    # 빈 섹션 제거
    return [s for s in sections if s['char_count'] > 0 or s['heading']]


def _count_transitions(text: str) -> int:
    """텍스트 내 주제 전환 수를 셉니다."""
    count = 0
    for pattern in _TRANSITION_PATTERNS_KO + _TRANSITION_PATTERNS_EN:
        count += len(pattern.findall(text))
    return count


_EMPTY_RESULT = {
    'breakpoints': [],
    'section_analysis': [],
    'summary': {'total_sections': 0, 'long_sections': 0,
                'suggested_breaks': 0, 'avg_section_length': 0},
    'score': 100.0,
    'suggestions': [],
}


def _analyze_sections_and_breakpoints(sections: List[Dict]) -> tuple:
    """섹션별 분석과 분할점을 감지합니다.

    Returns:
        (breakpoints, section_analysis, long_sections)
    """
    breakpoints = []
    section_analysis = []
    long_sections = 0

    for sec in sections:
        char_count = sec['char_count']
        transitions = _count_transitions(sec['text'])
        is_long = char_count >= _LONG_SECTION_THRESHOLD
        is_very_long = char_count >= _VERY_LONG_SECTION_THRESHOLD

        if is_long:
            long_sections += 1

        needs_break = False
        reason = ''

        if is_very_long:
            needs_break = True
            reason = f'매우 긴 섹션 ({char_count}자) — 분할 강력 권장'
        elif is_long and transitions >= 2:
            needs_break = True
            reason = f'긴 섹션 ({char_count}자) + 주제 전환 {transitions}회 — 분할 권장'
        elif transitions >= 3:
            needs_break = True
            reason = f'주제 전환 {transitions}회 — 하위 섹션 분할 권장'

        heading_text = sec['heading'] or '(서론/무제)'
        section_analysis.append({
            'heading': heading_text,
            'level': sec['level'],
            'char_count': char_count,
            'transition_count': transitions,
            'needs_break': needs_break,
        })

        if needs_break:
            breakpoints.append({
                'section': heading_text,
                'char_count': char_count,
                'transition_count': transitions,
                'reason': reason,
            })

    return breakpoints, section_analysis, long_sections


def _compute_breakpoint_score(suggested_breaks: int, total_sections: int) -> float:
    """분할 필요 비율로 점수를 계산합니다."""
    if total_sections > 0:
        break_ratio = suggested_breaks / total_sections
        return round(max(0.0, min(100.0, (1.0 - break_ratio) * 100.0)), 1)
    return 100.0


def detect_chapter_breakpoints(content: str) -> dict:
    """챕터 분할이 필요한 지점을 감지합니다.

    Args:
        content: 분석할 마크다운 콘텐츠

    Returns:
        breakpoints, section_analysis, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    sections = _parse_sections(content)
    if not sections:
        return dict(_EMPTY_RESULT)

    breakpoints, section_analysis, long_sections = (
        _analyze_sections_and_breakpoints(sections)
    )

    total_sections = len(sections)
    total_chars = sum(s['char_count'] for s in sections)
    avg_length = round(total_chars / total_sections) if total_sections > 0 else 0
    score = _compute_breakpoint_score(len(breakpoints), total_sections)

    suggestions = _generate_suggestions(
        breakpoints, long_sections, avg_length, total_sections
    )

    return {
        'breakpoints': breakpoints,
        'section_analysis': section_analysis,
        'summary': {
            'total_sections': total_sections,
            'long_sections': long_sections,
            'suggested_breaks': len(breakpoints),
            'avg_section_length': avg_length,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(
    breakpoints: List[Dict], long: int, avg: int, total: int
) -> List[str]:
    suggestions = []

    if not breakpoints:
        if total > 0:
            suggestions.append('섹션 길이가 적절합니다. 분할이 필요한 구간이 없습니다.')
        return suggestions

    names = ', '.join(f'"{b["section"]}"' for b in breakpoints[:3])
    suggestions.append(f'분할 권장 섹션 {len(breakpoints)}개: {names}.')

    if long > 0:
        suggestions.append(
            f'긴 섹션 {long}개 ({_LONG_SECTION_THRESHOLD}자 이상). '
            f'소제목(H3/H4)을 추가하여 가독성을 높이세요.'
        )

    if avg > _LONG_SECTION_THRESHOLD:
        suggestions.append(
            f'평균 섹션 길이 {avg}자로 다소 깁니다. '
            f'500-800자 단위로 분할하면 모바일 가독성이 향상됩니다.'
        )

    return suggestions
