"""
Title Tag Length Checker 서비스

콘텐츠의 제목(H1, meta title, 첫 헤딩)의 SEO 최적 길이를 점검합니다.
Google 검색 결과 표시 기준 (30-60자/영문, 15-30자/한글)으로 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_TITLE_TAG_RE = re.compile(r'<title>([^<]+)</title>', re.IGNORECASE)
_META_TITLE_RE = re.compile(
    r'<meta\s+(?:property=["\']og:title["\']|name=["\']title["\'])\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE
)
_FRONTMATTER_TITLE_RE = re.compile(
    r'^---\s*\n.*?title:\s*["\']?(.+?)["\']?\s*\n.*?---',
    re.DOTALL
)

# 한국어 비율 체크
_KO_CHAR_RE = re.compile(r'[가-힣]')


def _extract_title(content: str) -> str:
    """콘텐츠에서 제목을 추출합니다."""
    # HTML <title>
    m = _TITLE_TAG_RE.search(content)
    if m:
        return m.group(1).strip()

    # OG title / meta title
    m = _META_TITLE_RE.search(content)
    if m:
        return m.group(1).strip()

    # 프론트매터 title
    m = _FRONTMATTER_TITLE_RE.search(content)
    if m:
        return m.group(1).strip()

    # 첫 번째 H1
    for match in _HEADING_RE.finditer(content):
        if len(match.group(1)) == 1:  # H1
            return match.group(2).strip()

    # H1 없으면 첫 헤딩
    m = _HEADING_RE.search(content)
    if m:
        return m.group(2).strip()

    return ''


def _is_korean_dominant(text: str) -> bool:
    """한국어가 지배적인지 확인합니다."""
    ko_chars = len(_KO_CHAR_RE.findall(text))
    return ko_chars > len(text) * 0.3


def check_title_tag_length(content: str) -> dict:
    """제목 태그 길이를 점검합니다.

    Returns:
        title, checks, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'title': '',
            'checks': {},
            'summary': {'length': 0, 'language': '', 'quality_level': 'none'},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    title = _extract_title(content)
    if not title:
        return {
            'title': '',
            'checks': {},
            'summary': {'length': 0, 'language': '', 'quality_level': 'none'},
            'score': 20.0,
            'suggestions': ['제목이 없습니다. H1 또는 title 태그를 추가하세요.'],
        }

    length = len(title)
    is_korean = _is_korean_dominant(title)
    language = 'ko' if is_korean else 'en'

    # 최적 길이 범위
    if is_korean:
        optimal_min, optimal_max = 15, 30
        pixel_limit = 30  # 바이트가 아닌 글자수 기준 근사
    else:
        optimal_min, optimal_max = 30, 60
        pixel_limit = 60

    # 체크 항목
    length_optimal = optimal_min <= length <= optimal_max
    not_too_short = length >= (10 if is_korean else 15)
    not_too_long = length <= (40 if is_korean else 70)
    has_keyword_position = _check_keyword_front(title)
    no_pipe_abuse = title.count('|') <= 1 and title.count('-') <= 2
    proper_capitalization = not title.isupper() if not is_korean else True

    checks = {
        'optimal_length': length_optimal,
        'not_too_short': not_too_short,
        'not_too_long': not_too_long,
        'keyword_front_loaded': has_keyword_position,
        'no_separator_abuse': no_pipe_abuse,
        'proper_case': proper_capitalization,
    }

    passed = sum(1 for v in checks.values() if v)
    score = round(min(100.0, passed / len(checks) * 100), 1)

    if score >= 80:
        quality = 'excellent'
    elif score >= 50:
        quality = 'good'
    elif score >= 30:
        quality = 'fair'
    else:
        quality = 'poor'

    suggestions = _generate_suggestions(
        title, length, is_korean, optimal_min, optimal_max, checks
    )

    return {
        'title': title,
        'checks': checks,
        'summary': {
            'length': length,
            'language': language,
            'quality_level': quality,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _check_keyword_front(title: str) -> bool:
    """핵심 키워드가 제목 앞부분(40%)에 있는지 추정합니다."""
    # 핵심 단어 = 가장 긴 단어 (명사 추정)
    words = re.findall(r'[가-힣]{2,}|[A-Za-z]{4,}', title)
    if not words:
        return True  # 판별 불가 → 통과

    longest = max(words, key=len)
    pos = title.find(longest)
    return pos <= len(title) * 0.4


def _generate_suggestions(title: str, length: int, is_ko: bool,
                           opt_min: int, opt_max: int,
                           checks: Dict) -> List[str]:
    suggestions = []
    lang = '한국어' if is_ko else '영어'

    if checks['optimal_length']:
        suggestions.append(f'제목 {length}자 ({lang}): 최적 범위 ({opt_min}-{opt_max}자).')
    elif length < opt_min:
        suggestions.append(
            f'제목 {length}자로 짧습니다 ({lang} 권장: {opt_min}-{opt_max}자). '
            f'설명적 키워드를 추가하세요.'
        )
    elif length > opt_max:
        suggestions.append(
            f'제목 {length}자로 깁니다 ({lang} 권장: {opt_min}-{opt_max}자). '
            f'검색 결과에서 잘릴 수 있습니다.'
        )

    if not checks['keyword_front_loaded']:
        suggestions.append('핵심 키워드를 제목 앞부분에 배치하면 CTR이 향상됩니다.')

    if not checks['no_separator_abuse']:
        suggestions.append('구분자(|, -)를 과도하게 사용하면 가독성이 떨어집니다.')

    return suggestions
