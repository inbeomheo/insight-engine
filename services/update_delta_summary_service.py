"""
Update Delta Summary Checker 서비스

문서가 최신인지뿐 아니라 "이번에 무엇이 바뀌었는지"를 명시하는
업데이트 요약 블록이 있는지 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List

# 업데이트/수정 날짜 신호
_UPDATE_DATE_PATTERNS = [
    re.compile(r'(?:업데이트|수정|갱신|최종\s*수정)\s*(?:일|날짜|:)?\s*(?:20\d{2})', re.IGNORECASE),
    re.compile(r'(?:20\d{2}[\.\-/]\d{1,2}[\.\-/]\d{1,2})\s*(?:업데이트|수정|갱신)', re.IGNORECASE),
    re.compile(r'\b(?:updated?|modified|revised|last\s+(?:updated?|modified))\s*(?::?\s*(?:20\d{2}|on))', re.IGNORECASE),
]

# 변경 사항 요약 패턴
_DELTA_PATTERNS = [
    re.compile(r'(?:변경\s*(?:사항|내용|점|로그)|수정\s*(?:사항|내용|점))', re.IGNORECASE),
    re.compile(r'(?:(?:이번|최근|최신)\s*(?:업데이트|변경|수정).*?(?:내용|사항|점))', re.IGNORECASE),
    re.compile(r'(?:(?:추가|삭제|변경|수정|개선)\s*(?:됨|되었|했|함))', re.IGNORECASE),
    re.compile(r'\b(?:changelog|what\'s?\s*(?:new|changed)|release\s*notes?|update\s*(?:log|notes?|summary))\b', re.IGNORECASE),
    re.compile(r'\b(?:(?:added|removed|changed|fixed|updated|improved)\s*:)', re.IGNORECASE),
]

# 변경 헤딩 패턴
_DELTA_HEADING_PATTERNS = [
    re.compile(r'(?:변경\s*(?:사항|내역|로그)|업데이트\s*(?:내역|로그|노트))', re.IGNORECASE),
    re.compile(r'(?:수정\s*이력|히스토리|릴리스\s*노트)', re.IGNORECASE),
    re.compile(r'\b(?:changelog|update\s*(?:log|history|notes?)|what\'s?\s*(?:new|changed)|revision\s*history)\b', re.IGNORECASE),
]

# 버전 표기
_VERSION_PATTERNS = [
    re.compile(r'(?:v(?:ersion)?\s*\d+\.\d+)', re.IGNORECASE),
    re.compile(r'(?:버전\s*\d+\.\d+)', re.IGNORECASE),
]

_HEADING_RE = re.compile(r'^#{1,3}\s+(.+)$', re.MULTILINE)


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


def check_update_delta_summary(content: str) -> dict:
    """업데이트 변경 요약 블록 존재 여부를 점검합니다.

    Returns:
        score, summary, update_signals, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 50.0,
            'summary': {
                'has_update_date': False,
                'has_delta_summary': False,
                'has_delta_heading': False,
                'has_version': False,
                'update_signals': 0,
                'level': 'none',
            },
            'update_signals': [],
            'suggestions': [],
        }

    # 업데이트 날짜
    has_update_date = _has_pattern(content, _UPDATE_DATE_PATTERNS)

    # 변경 사항 요약
    delta_count = _count_matches(content, _DELTA_PATTERNS)
    has_delta = delta_count >= 2

    # 변경 헤딩
    headings = _HEADING_RE.findall(content)
    has_delta_heading = any(
        _has_pattern(h, _DELTA_HEADING_PATTERNS) for h in headings
    )

    # 버전 표기
    has_version = _has_pattern(content, _VERSION_PATTERNS)

    # 신호 수
    signals = []
    if has_update_date:
        signals.append('update_date')
    if has_delta:
        signals.append('delta_summary')
    if has_delta_heading:
        signals.append('delta_heading')
    if has_version:
        signals.append('version')

    total_signals = len(signals)

    # 레벨 판정
    if total_signals >= 3:
        level = 'comprehensive'
    elif total_signals >= 2:
        level = 'good'
    elif total_signals >= 1:
        level = 'partial'
    else:
        level = 'missing'

    # 연속 점수 — total_signals(0~4) 기반
    if total_signals == 0:
        word_count = len(content.split())
        score = 60.0 if word_count < 200 else 30.0
    else:
        score = 30.0 + (total_signals / 4.0 * 65.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        has_update_date, has_delta, has_delta_heading,
        has_version, level, signals
    )

    return {
        'score': score,
        'summary': {
            'has_update_date': has_update_date,
            'has_delta_summary': has_delta,
            'has_delta_heading': has_delta_heading,
            'has_version': has_version,
            'update_signals': total_signals,
            'level': level,
        },
        'update_signals': signals,
        'suggestions': suggestions,
    }


def _generate_suggestions(has_date: bool, has_delta: bool,
                           has_heading: bool, has_version: bool,
                           level: str, signals: List[str]) -> List[str]:
    suggestions = []

    level_labels = {
        'comprehensive': '포괄적', 'good': '양호',
        'partial': '부분적', 'missing': '없음',
    }
    suggestions.append(
        f'업데이트 표시: {level_labels.get(level, level)} '
        f'({len(signals)}/4 항목).'
    )

    if not has_date:
        suggestions.append(
            '"최종 수정: 2024.06.15" 형태의 업데이트 날짜를 추가하세요.'
        )

    if not has_delta:
        suggestions.append(
            '"이번 업데이트 변경 사항: 추가됨/수정됨/삭제됨" 요약을 추가하세요.'
        )

    if not has_heading:
        suggestions.append(
            '"변경 사항" 또는 "Changelog" 전용 섹션을 만드세요.'
        )

    if not has_version and has_date:
        suggestions.append(
            '버전 번호(v2.1 등)를 함께 표기하면 이력 추적이 쉬워집니다.'
        )

    return suggestions
