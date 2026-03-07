"""
Actionability Gap Detector 서비스

콘텐츠에서 실행 가능한 조언/가이드가 부족한 구간을 감지합니다.
조언 문장 대비 구체적 실행 단계 비율을 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# ── 마크다운 헤딩 ──
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# ── 조언/권고 패턴 (한국어) ──
_ADVICE_PATTERNS_KO = [
    re.compile(r'해야\s*(한다|합니다)'),
    re.compile(r'하는\s*것이\s*좋'),
    re.compile(r'(?:이|가)\s*중요(하다|합니다)'),
    re.compile(r'(?:이|가)\s*필요(하다|합니다)'),
    re.compile(r'권장(한다|합니다)'),
    re.compile(r'추천(한다|합니다)'),
    re.compile(r'바람직'),
    re.compile(r'고려(해야|하세요|합시다)'),
    re.compile(r'확인(해야|하세요|합시다)'),
]

# ── 조언/권고 패턴 (영어) ──
_ADVICE_PATTERNS_EN = [
    re.compile(r'\bshould\b', re.IGNORECASE),
    re.compile(r'\bmust\b', re.IGNORECASE),
    re.compile(r'\bneed\s+to\b', re.IGNORECASE),
    re.compile(r'\bimportant\s+to\b', re.IGNORECASE),
    re.compile(r'\brecommend', re.IGNORECASE),
    re.compile(r'\bconsider\b', re.IGNORECASE),
    re.compile(r'\bmake\s+sure\b', re.IGNORECASE),
]

# ── 실행 가능한 단계 패턴 (한국어) ──
_ACTION_PATTERNS_KO = [
    re.compile(r'(?:첫째|둘째|셋째|넷째|다섯째)'),
    re.compile(r'(?:1단계|2단계|3단계|Step\s*\d)', re.IGNORECASE),
    re.compile(r'먼저\s'),
    re.compile(r'다음으로\s'),
    re.compile(r'마지막으로\s'),
    re.compile(r'(?:을|를)\s*실행'),
    re.compile(r'(?:을|를)\s*설치'),
    re.compile(r'(?:을|를)\s*입력'),
    re.compile(r'(?:을|를)\s*클릭'),
    re.compile(r'(?:을|를)\s*선택'),
    re.compile(r'(?:을|를)\s*추가'),
    re.compile(r'(?:을|를)\s*생성'),
    re.compile(r'(?:을|를)\s*설정'),
    re.compile(r'하세요'),
    re.compile(r'합시다'),
    re.compile(r'하십시오'),
]

# ── 실행 가능한 단계 패턴 (영어) ──
_ACTION_PATTERNS_EN = [
    re.compile(r'^(?:First|Second|Third|Next|Then|Finally)\b', re.IGNORECASE),
    re.compile(r'^Step\s+\d', re.IGNORECASE),
    re.compile(r'(?<![A-Za-z])(?:Run|Install|Click|Select|Open|Create|Add|Set|Configure|Download|Type|Enter)\b'),
    re.compile(r'\bgo\s+to\b', re.IGNORECASE),
    re.compile(r'\bnavigate\s+to\b', re.IGNORECASE),
]

# 문장 분리
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    cleaned = re.sub(r'^\s*[-*]\s+', '', cleaned, flags=re.MULTILINE)
    cleaned = re.sub(r'^\s*\d+\.\s+', '', cleaned, flags=re.MULTILINE)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 5]


def _is_advice(sentence: str) -> bool:
    for p in _ADVICE_PATTERNS_KO + _ADVICE_PATTERNS_EN:
        if p.search(sentence):
            return True
    return False


def _is_actionable(sentence: str) -> bool:
    for p in _ACTION_PATTERNS_KO + _ACTION_PATTERNS_EN:
        if p.search(sentence):
            return True
    return False


def _parse_sections(content: str) -> List[Dict]:
    lines = content.split('\n')
    sections = []
    current = {'section': '(서론)', 'lines': []}
    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if current['lines'] or current['section'] != '(서론)':
                sections.append(current)
            current = {'section': m.group(2).strip(), 'lines': []}
        else:
            current['lines'].append(line)
    sections.append(current)
    if sections and sections[0]['section'] == '(서론)' and not ''.join(sections[0]['lines']).strip():
        sections = sections[1:]
    return sections


def detect_actionability_gaps(content: str) -> dict:
    """콘텐츠에서 실행 가능한 조언이 부족한 구간을 감지합니다.

    Returns:
        section_analysis, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'section_analysis': [],
            'summary': {'total_advice': 0, 'total_actions': 0,
                        'actionability_rate': 0.0, 'gap_sections': 0},
            'score': 100.0,
            'suggestions': [],
        }

    sections = _parse_sections(content)
    if not sections:
        sections = [{'section': '(전체)', 'lines': content.split('\n')}]

    section_analysis = []
    total_advice = 0
    total_actions = 0
    gap_sections = 0

    for sec in sections:
        text = '\n'.join(sec['lines'])
        sentences = _split_sentences(text)
        advice_count = sum(1 for s in sentences if _is_advice(s))
        action_count = sum(1 for s in sentences if _is_actionable(s))
        has_gap = advice_count > 0 and action_count == 0

        total_advice += advice_count
        total_actions += action_count
        if has_gap:
            gap_sections += 1

        section_analysis.append({
            'section': sec['section'],
            'advice_count': advice_count,
            'action_count': action_count,
            'has_gap': has_gap,
        })

    rate = round((total_actions / total_advice * 100) if total_advice > 0 else 100.0, 1)
    score = round(min(100.0, rate), 1)

    suggestions = _generate_suggestions(section_analysis, gap_sections, rate)

    return {
        'section_analysis': section_analysis,
        'summary': {
            'total_advice': total_advice,
            'total_actions': total_actions,
            'actionability_rate': rate,
            'gap_sections': gap_sections,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(analysis: List[Dict], gaps: int, rate: float) -> List[str]:
    suggestions = []
    if gaps == 0:
        if any(a['advice_count'] > 0 for a in analysis):
            suggestions.append('모든 조언 섹션에 실행 가능한 단계가 포함되어 있습니다.')
        return suggestions

    gap_names = [a['section'] for a in analysis if a['has_gap']]
    names = ', '.join(f'"{n}"' for n in gap_names[:3])
    suggestions.append(
        f'실행 단계가 없는 조언 섹션 {gaps}개: {names}. '
        f'구체적인 실행 방법(~하세요, Step 1 등)을 추가하세요.'
    )

    if rate < 50:
        suggestions.append(f'실행 가능성 비율 {rate}%로 낮습니다. 조언마다 구체적 단계를 덧붙이세요.')
    return suggestions
