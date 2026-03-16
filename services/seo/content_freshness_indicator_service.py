"""
Content Freshness Indicator 서비스

콘텐츠의 시의성(freshness)을 평가합니다.
날짜 표현, 시간 참조, 최신 용어 사용 여부를 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from datetime import datetime
from typing import List, Dict

logger = logging.getLogger(__name__)

# 날짜 패턴
_DATE_PATTERNS = [
    re.compile(r'20\d{2}년\s*\d{1,2}월'),            # 2024년 3월
    re.compile(r'20\d{2}\.\s*\d{1,2}'),               # 2024.3
    re.compile(r'20\d{2}-\d{2}'),                      # 2024-03
    re.compile(r'(?<!\d)20\d{2}(?!\d)'),                 # 2024
    re.compile(r'(?:January|February|March|April|May|June|July|August|'
               r'September|October|November|December)\s+20\d{2}', re.IGNORECASE),
]

# 시간 참조 패턴
_TIME_REFS = {
    'recent': [
        re.compile(r'(?:최근|요즘|현재|올해|이번|금년|지금)'),
        re.compile(r'\b(?:recently|currently|now|today|this year|latest)\b', re.IGNORECASE),
    ],
    'outdated': [
        re.compile(r'(?:과거에|예전에|옛날에|몇 년 전)'),
        re.compile(r'\b(?:years ago|long ago|previously|formerly|in the past)\b', re.IGNORECASE),
    ],
    'future': [
        re.compile(r'(?:앞으로|향후|내년|다음 해|미래에)'),
        re.compile(r'\b(?:next year|in the future|upcoming|forthcoming)\b', re.IGNORECASE),
    ],
}

# 최신 트렌드 키워드 (기술/마케팅)
_TREND_KEYWORDS = re.compile(
    r'(?:AI|GPT|LLM|생성형|챗봇|자동화|메타버스|블록체인|NFT|Web3|'
    r'클라우드|SaaS|마이크로서비스|DevOps|MLOps|ESG|지속가능|'
    r'ChatGPT|Gemini|Claude|Copilot|AGI)',
    re.IGNORECASE
)

# 구식 표현
_OUTDATED_TERMS = re.compile(
    r'(?:플로피|디스켓|CD-ROM|모뎀|다이얼업|ActiveX|'
    r'IE6|Internet Explorer|Flash Player|Silverlight)',
    re.IGNORECASE
)


def _extract_years(content: str) -> List[int]:
    """콘텐츠에서 연도를 추출합니다."""
    years = []
    for match in re.finditer(r'(?<!\d)(20\d{2})(?!\d)', content):
        years.append(int(match.group(1)))
    return years


_EMPTY_RESULT = {
    'date_references': [],
    'time_signals': {},
    'freshness_indicators': {},
    'summary': {'has_dates': False, 'newest_year': 0,
                'freshness_level': 'unknown'},
    'score': 50.0,
    'suggestions': [],
}


def _collect_freshness_signals(content: str) -> tuple:
    """콘텐츠에서 시의성 관련 신호를 수집합니다.

    Returns:
        (date_refs, newest_year, time_signals, trend_count, outdated_count, outdated_matches)
    """
    date_refs = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(content):
            date_refs.append(match.group())

    years = _extract_years(content)
    newest_year = max(years) if years else 0

    time_signals = {}
    for category, patterns in _TIME_REFS.items():
        count = sum(len(p.findall(content)) for p in patterns)
        if count > 0:
            time_signals[category] = count

    outdated_matches = _OUTDATED_TERMS.findall(content)
    return (date_refs, newest_year, time_signals,
            len(_TREND_KEYWORDS.findall(content)), len(outdated_matches), outdated_matches)


def check_content_freshness(content: str) -> dict:
    """콘텐츠 시의성을 평가합니다.

    Returns:
        date_references, time_signals, freshness_indicators,
        summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    try:
        current_year = datetime.now().year
        date_refs, newest_year, time_signals, trend_count, outdated_count, outdated_matches = \
            _collect_freshness_signals(content)

        level = _determine_level(newest_year, current_year, time_signals,
                                  trend_count, outdated_count)

        return {
            'date_references': list(set(date_refs))[:20],
            'time_signals': time_signals,
            'freshness_indicators': {
                'trend_keywords': trend_count,
                'outdated_terms': outdated_count,
                'recent_signals': time_signals.get('recent', 0),
                'outdated_signals': time_signals.get('outdated', 0),
            },
            'summary': {
                'has_dates': len(date_refs) > 0,
                'newest_year': newest_year,
                'freshness_level': level,
            },
            'score': _calculate_score(newest_year, current_year, time_signals,
                                       trend_count, outdated_count),
            'suggestions': _generate_suggestions(
                newest_year, current_year, date_refs, time_signals,
                trend_count, outdated_count, outdated_matches, level
            ),
        }
    except Exception as e:
        logger.error(f"콘텐츠 시의성 평가 처리 실패: {e}")
        return {**_EMPTY_RESULT, 'suggestions': ['분석 중 오류가 발생했습니다.']}


def _determine_level(newest: int, current: int, signals: Dict,
                      trends: int, outdated: int) -> str:
    if newest >= current:
        return 'fresh'
    elif newest >= current - 1:
        return 'recent'
    elif newest >= current - 3:
        return 'aging'
    elif newest > 0:
        return 'outdated'
    else:
        # 연도 없음: 시그널로 판단
        if signals.get('recent', 0) > signals.get('outdated', 0):
            return 'recent'
        if trends > outdated:
            return 'recent'
        return 'unknown'


def _calculate_score(newest: int, current: int, signals: Dict,
                      trends: int, outdated: int) -> float:
    score = 50.0  # 기본

    # 최신 연도 보너스
    if newest >= current:
        score += 30.0
    elif newest >= current - 1:
        score += 20.0
    elif newest >= current - 3:
        score += 5.0
    elif newest > 0:
        score -= 15.0

    # 최신 시그널 보너스
    recent = signals.get('recent', 0)
    score += min(15.0, recent * 3.0)

    # 트렌드 키워드 보너스
    score += min(10.0, trends * 2.0)

    # 구식 표현 페널티
    score -= outdated * 5.0

    # 과거 시그널 페널티
    old_signals = signals.get('outdated', 0)
    score -= old_signals * 3.0

    return round(max(0.0, min(100.0, score)), 1)


def _generate_suggestions(newest: int, current: int, refs: List,
                           signals: Dict, trends: int, outdated: int,
                           outdated_list: List, level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'fresh': '최신', 'recent': '비교적 최신', 'aging': '노후화 진행',
        'outdated': '구식', 'unknown': '시의성 불명',
    }
    suggestions.append(f'콘텐츠 시의성: {level_labels.get(level, level)}.')

    if not refs:
        suggestions.append('날짜 참조가 없습니다. 작성/수정일을 명시하면 신뢰도가 높아집니다.')

    if newest > 0 and newest < current - 2:
        suggestions.append(
            f'최신 연도 {newest}년: {current - newest}년 경과. '
            f'데이터와 통계를 업데이트하세요.'
        )

    if outdated > 0:
        terms = ', '.join(set(outdated_list[:3]))
        suggestions.append(f'구식 용어 감지: {terms}. 최신 대안으로 교체하세요.')

    return suggestions
