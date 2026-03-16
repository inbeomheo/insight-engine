"""
전문 용어 정의 커버리지 분석 서비스

콘텐츠 내 전문 용어/약어가 첫 등장 시
정의나 설명이 동반되어 있는지 검사합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 한국어 전문 용어 사전 (30개+)
_KOREAN_JARGON = {
    '머신러닝', '딥러닝', '블록체인', '클라우드', '프레임워크',
    '알고리즘', '인프라', '아키텍처', '마이크로서비스', '데이터베이스',
    '스케일링', '오케스트레이션', '컨테이너', '쿠버네티스', '미들웨어',
    '프로토콜', '가상화', '렌더링', '리팩토링', '디버깅',
    '트랜잭션', '파이프라인', '캐싱', '프로비저닝', '오토스케일링',
    '로드밸런싱', '서버리스', '데브옵스', '인덱싱', '토큰화',
    '직렬화', '역직렬화', '폴리필', '번들링', '스크래핑',
}

# 흔한 일반 약어 제외 목록 (전문 용어가 아닌 것들)
_COMMON_ABBREVIATIONS = {
    'TV', 'OK', 'AM', 'PM', 'KG', 'CM', 'MM', 'KM',
    'VS', 'DJ', 'MC', 'VR', 'AR', 'PC', 'ID', 'UN',
}

# 영문 약어 패턴 (대문자 2~6자, 한국어 경계 포함)
_ABBR_PATTERN = re.compile(r'(?<![A-Za-z])([A-Z]{2,6})(?![A-Za-z])')

# 카멜케이스/파스칼케이스 기술 용어 (최소 2단어 결합, 한국어 경계 포함)
_CAMEL_PATTERN = re.compile(r'(?<![A-Za-z])([A-Z][a-z]+(?:[A-Z][a-z]+)+)(?![A-Za-z])')

# 괄호 용어 패턴: "ABC(설명)" 또는 "ABC (설명)"
_PAREN_TERM_PATTERN = re.compile(r'([A-Z]{2,6})\s*\(([^)]+)\)')

# 정의 동반 패턴들
_DEFINITION_PATTERNS = [
    # 괄호 설명: "SEO(검색엔진최적화)" 또는 "SEO (검색엔진 최적화)"
    re.compile(r'{term}\s*\([^)]+\)'),
    # "~란" 패턴: "API란", "SEO란"
    re.compile(r'{term}[이]?란\b'),
    # "~는 ~를 말한다/의미한다"
    re.compile(r'{term}[은는]\s+.{{2,30}}(?:말한다|의미한다|뜻한다|가리킨다)'),
    # "~라 불리는" / "~라고 불리는"
    re.compile(r'{term}[이]?라(?:고)?\s*불리는'),
    # 콜론 설명: "SEO: 검색엔진 최적화"
    re.compile(r'{term}\s*:\s*\S+'),
    # 대시 설명: "SEO — 검색엔진 최적화" 또는 "SEO - 검색엔진 최적화"
    re.compile(r'{term}\s*[—–\-]\s*\S+'),
    # "~은/는 ~이다" 패턴
    re.compile(r'{term}[은는]\s+.{{2,30}}(?:이다|입니다)'),
    # "~의 약자" 패턴
    re.compile(r'{term}[은는의]?\s*.{{0,10}}약자'),
    # 영문 풀네임 후 괄호 약어: "Search Engine Optimization(SEO)"
    re.compile(r'[A-Za-z\s]{{5,50}}\(\s*{term}\s*\)'),
]


_EMPTY_RESULT = {
    'terms': [],
    'summary': {'total': 0, 'defined': 0, 'undefined': 0},
    'coverage_score': 100.0,
    'suggestions': [],
}


def _collect_terms(content: str) -> dict:
    """콘텐츠에서 전문 용어를 수집합니다 (중복 제거, 첫 등장 위치 기록).

    Returns:
        {term: {"type": str, "first_occurrence": int}}
    """
    found = {}

    for m in _PAREN_TERM_PATTERN.finditer(content):
        abbr = m.group(1)
        if abbr not in _COMMON_ABBREVIATIONS and abbr not in found:
            found[abbr] = {'type': 'abbreviation', 'first_occurrence': m.start()}

    for m in _ABBR_PATTERN.finditer(content):
        abbr = m.group(1)
        if abbr not in _COMMON_ABBREVIATIONS and abbr not in found:
            found[abbr] = {'type': 'abbreviation', 'first_occurrence': m.start()}

    for m in _CAMEL_PATTERN.finditer(content):
        term = m.group(1)
        if term not in found:
            found[term] = {'type': 'technical', 'first_occurrence': m.start()}

    for jargon in _KOREAN_JARGON:
        idx = content.find(jargon)
        if idx != -1 and jargon not in found:
            found[jargon] = {'type': 'korean_jargon', 'first_occurrence': idx}

    return found


def _check_all_definitions(found_terms: dict, content: str) -> list:
    """각 용어의 정의 동반 여부를 검사합니다."""
    results = []
    for term, info in found_terms.items():
        has_def, def_text = _check_definition(term, content, info['first_occurrence'])
        results.append({
            'term': term, 'type': info['type'],
            'first_occurrence': info['first_occurrence'],
            'has_definition': has_def, 'definition_text': def_text,
            'status': 'defined' if has_def else 'undefined',
        })
    results.sort(key=lambda x: x['first_occurrence'])
    return results


def analyze_jargon_coverage(content: str) -> dict:
    """콘텐츠 내 전문 용어의 정의 커버리지를 분석합니다.

    Returns:
        terms, summary, coverage_score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        found_terms = _collect_terms(content)
        if not found_terms:
            return {**_EMPTY_RESULT, 'suggestions': ['전문 용어가 감지되지 않았습니다.']}

        results = _check_all_definitions(found_terms, content)
        defined_count = sum(1 for r in results if r['has_definition'])
        total = len(results)
        coverage = (defined_count / total * 100) if total > 0 else 100.0

        return {
            'terms': results,
            'summary': {'total': total, 'defined': defined_count, 'undefined': total - defined_count},
            'coverage_score': round(coverage, 1),
            'suggestions': _generate_suggestions(results, coverage),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


# 용어별 정의 패턴 캐시 (루프 내 re.search 문자열 치환 반복 방지)
_definition_pattern_cache: dict = {}


def _get_definition_patterns(term: str) -> list:
    """용어별 컴파일된 정의 패턴을 반환합니다 (캐시 사용)."""
    if term in _definition_pattern_cache:
        return _definition_pattern_cache[term]

    escaped = re.escape(term)
    compiled = []
    for template in _DEFINITION_PATTERNS:
        pattern_str = template.pattern.replace('{term}', escaped)
        try:
            compiled.append(re.compile(pattern_str))
        except re.error:
            continue

    _definition_pattern_cache[term] = compiled
    return compiled


def _check_definition(term: str, content: str, first_pos: int) -> tuple:
    """용어의 첫 등장 위치 앞뒤 100자 윈도우에서 정의 패턴을 검색합니다.

    Returns:
        (has_definition: bool, definition_text: str)
    """
    window_start = max(0, first_pos - 100)
    window_end = min(len(content), first_pos + len(term) + 100)
    window = content[window_start:window_end]

    for pattern in _get_definition_patterns(term):
        match = pattern.search(window)
        if match:
            return True, match.group(0).strip()

    return False, ''


def _generate_suggestions(results: list, coverage: float) -> list:
    """분석 결과를 바탕으로 개선 제안을 생성합니다."""
    suggestions = []

    undefined = [r for r in results if not r['has_definition']]

    if not undefined:
        suggestions.append('모든 전문 용어에 정의가 포함되어 있습니다.')
        return suggestions

    if coverage < 50:
        suggestions.append(
            f'전문 용어 정의 커버리지가 {coverage}%로 낮습니다. '
            '독자 이해를 위해 용어 설명을 추가하세요.'
        )

    # 미정의 용어 안내 (최대 5개)
    undef_terms = [r['term'] for r in undefined[:5]]
    suggestions.append(
        f'다음 용어에 정의를 추가하세요: {", ".join(undef_terms)}'
    )

    # 유형별 팁
    abbr_undef = [r for r in undefined if r['type'] == 'abbreviation']
    if abbr_undef:
        suggestions.append(
            '약어는 첫 등장 시 괄호 안에 풀네임을 표기하세요. '
            '예: "SEO(검색엔진최적화)"'
        )

    korean_undef = [r for r in undefined if r['type'] == 'korean_jargon']
    if korean_undef:
        suggestions.append(
            '한국어 전문 용어는 "~란 ~을 의미한다" 형태로 정의를 추가하세요.'
        )

    return suggestions
