"""
Community Evidence Coverage Analyzer 서비스

Reddit, 포럼, 리뷰, Q&A 같은 사용자 발화 기반 근거가
포함됐는지 점검하여 커뮤니티 맥락 신호를 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# 커뮤니티 소스 타입별 패턴
_COMMUNITY_SOURCES = {
    'reddit': {
        'label': 'Reddit',
        'patterns': [
            re.compile(r'(?:reddit|r/\w+|레딧|서브레딧|subreddit)', re.IGNORECASE),
        ],
    },
    'forum': {
        'label': '포럼/커뮤니티',
        'patterns': [
            re.compile(r'(?:포럼|커뮤니티|게시판|카페|디시인사이드|클리앙|뽐뿌)', re.IGNORECASE),
            re.compile(r'\b(?:forum|community|board|discussion)\b', re.IGNORECASE),
        ],
    },
    'review': {
        'label': '사용자 리뷰',
        'patterns': [
            re.compile(r'(?:사용자\s*(?:리뷰|후기|평가)|구매\s*(?:후기|리뷰)|실사용\s*(?:후기|리뷰))', re.IGNORECASE),
            re.compile(r'\b(?:user\s*review|customer\s*review|buyer\s*review|testimonial)\b', re.IGNORECASE),
        ],
    },
    'qna': {
        'label': 'Q&A 사이트',
        'patterns': [
            re.compile(r'(?:Stack\s*Overflow|Quora|지식인|ask\.)', re.IGNORECASE),
            re.compile(r'\b(?:Q&A|question\s*and\s*answer|stackoverflow)\b', re.IGNORECASE),
        ],
    },
    'social': {
        'label': '소셜 미디어',
        'patterns': [
            re.compile(r'(?:트위터|X\s*에서|인스타그램|페이스북|틱톡|유튜브\s*댓글)', re.IGNORECASE),
            re.compile(r'\b(?:Twitter|X\.com|Instagram|Facebook|TikTok|YouTube\s*comment)\b', re.IGNORECASE),
        ],
    },
}

# 커뮤니티 인용 패턴 (사용자 발화 인용)
_COMMUNITY_CITATION = [
    re.compile(r'(?:사용자들?\s*(?:에\s*따르면|의\s*의견|반응|피드백))', re.IGNORECASE),
    re.compile(r'(?:실제\s*(?:사용자|유저|구매자).*?(?:말|평|의견|후기))', re.IGNORECASE),
    re.compile(r'(?:댓글|반응|피드백|의견).*?(?:에\s*따르면|에서|을\s*보면)', re.IGNORECASE),
    re.compile(r'\b(?:users?\s+(?:report|say|mention|note)|according\s+to\s+(?:users?|reviews?))\b', re.IGNORECASE),
    re.compile(r'\b(?:community\s+(?:feedback|response|reaction)|real[- ]world\s+(?:feedback|experience))\b', re.IGNORECASE),
]

# 커뮤니티 URL 패턴
_COMMUNITY_URLS = [
    re.compile(r'https?://(?:www\.)?reddit\.com', re.IGNORECASE),
    re.compile(r'https?://(?:www\.)?stackoverflow\.com', re.IGNORECASE),
    re.compile(r'https?://(?:www\.)?quora\.com', re.IGNORECASE),
    re.compile(r'https?://(?:cafe|blog)\.naver\.com', re.IGNORECASE),
]


def _count_matches(content: str, patterns: list) -> int:
    return sum(len(p.findall(content)) for p in patterns)


def _has_pattern(content: str, patterns: list) -> bool:
    return any(p.search(content) for p in patterns)


_EMPTY_RESULT = {
    'score': 50.0,
    'summary': {
        'sources_found': [], 'sources_missing': list(_COMMUNITY_SOURCES.keys()),
        'citation_count': 0, 'community_url_count': 0,
        'coverage_ratio': 0.0, 'level': 'none',
    },
    'community_signals': [],
    'suggestions': [],
}


def _scan_sources(content: str) -> tuple:
    """커뮤니티 소스 타입별 존재 여부를 스캔합니다.

    Returns:
        (sources_found, sources_missing, signals)
    """
    sources_found = []
    sources_missing = []
    signals = []

    for src_name, src_info in _COMMUNITY_SOURCES.items():
        if _has_pattern(content, src_info['patterns']):
            sources_found.append(src_name)
            signals.append({'type': src_name, 'label': src_info['label']})
        else:
            sources_missing.append(src_name)

    return sources_found, sources_missing, signals


def _compute_evidence_score(total_signals: int, citation_count: int) -> tuple:
    """커뮤니티 근거 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if total_signals >= 5:
        level = 'rich'
    elif total_signals >= 3:
        level = 'good'
    elif total_signals >= 1:
        level = 'minimal'
    else:
        level = 'none'

    if total_signals == 0:
        score = 30.0
    else:
        score = min(95.0, 30.0 + total_signals * 13.0)

    if citation_count >= 2 and score < 100:
        score = min(100.0, score + 10.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_community_evidence(content: str) -> dict:
    """커뮤니티 근거 포함 여부를 분석합니다.

    Returns:
        score, summary, community_signals, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)
    try:

        sources_found, sources_missing, signals = _scan_sources(content)
        citation_count = _count_matches(content, _COMMUNITY_CITATION)
        url_count = _count_matches(content, _COMMUNITY_URLS)
        coverage = round(len(sources_found) / max(len(_COMMUNITY_SOURCES), 1) * 100, 1)
        total_signals = len(sources_found) + citation_count + url_count
        score, level = _compute_evidence_score(total_signals, citation_count)

        return {
            'score': score,
            'summary': {
                'sources_found': sources_found,
                'sources_missing': sources_missing,
                'citation_count': citation_count,
                'community_url_count': url_count,
                'coverage_ratio': coverage,
                'level': level,
            },
            'community_signals': signals,
            'suggestions': _generate_suggestions(
                sources_found, sources_missing, citation_count,
                url_count, coverage, level
            ),
        }
    except Exception as e:
        logger.error(f"커뮤니티 근거 분석 처리 실패: {e}")
        return dict(_EMPTY_RESULT)
def _generate_suggestions(found: List[str], missing: List[str],
                           citations: int, urls: int,
                           coverage: float, level: str) -> List[str]:
    suggestions = []

    level_labels = {
        'rich': '풍부', 'good': '양호',
        'minimal': '최소', 'none': '없음',
    }
    labels = {k: v['label'] for k, v in _COMMUNITY_SOURCES.items()}

    found_text = ', '.join(labels.get(f, f) for f in found) if found else '없음'
    suggestions.append(
        f'커뮤니티 근거: {level_labels.get(level, level)}. '
        f'감지된 소스: {found_text}.'
    )

    if level in ('none', 'minimal'):
        suggestions.append(
            'Reddit, 포럼, 사용자 리뷰 등 커뮤니티 근거를 추가하면 '
            '콘텐츠 신뢰도와 AI 인용 가능성이 높아집니다.'
        )

    if citations == 0 and found:
        suggestions.append(
            '"사용자들에 따르면", "실제 사용자 피드백" 같은 '
            '인용 표현을 사용하세요.'
        )

    for m in missing[:2]:
        suggestions.append(
            f'{labels.get(m, m)} 소스를 추가하면 다양성이 높아집니다.'
        )

    return suggestions
