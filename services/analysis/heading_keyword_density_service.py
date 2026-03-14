"""
Heading Keyword Density 서비스

콘텐츠 헤딩(H1~H6)에서 키워드가 얼마나 잘 포함되어 있는지 분석합니다.
본문 상위 키워드가 헤딩에 반영된 비율, 헤딩 키워드 중복, 과도한 키워드 사용을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from collections import Counter

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 한국어 불용어
_KO_STOPWORDS = {
    '이', '그', '저', '것', '수', '등', '및', '또', '을', '를', '에', '의',
    '가', '은', '는', '로', '와', '과', '도', '한', '된', '하는', '있는',
    '위한', '대한', '통한', '따른', '대해', '위해', '합니다', '됩니다',
    '입니다', '있습니다', '없습니다',
}

# 영어 불용어
_EN_STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'and', 'or', 'but', 'if',
    'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as',
    'into', 'about', 'that', 'this', 'it', 'not', 'no', 'so', 'up',
    'out', 'than', 'how', 'what', 'when', 'where', 'who', 'which',
}


def _extract_headings(content: str) -> List[Dict]:
    """마크다운 헤딩을 추출합니다."""
    headings = []
    for match in _HEADING_RE.finditer(content):
        level = len(match.group(1))
        text = match.group(2).strip()
        headings.append({'level': level, 'text': text})
    return headings


def _tokenize(text: str) -> List[str]:
    """텍스트를 토큰으로 분리합니다 (불용어 제외)."""
    tokens = text.lower().split()
    result = []
    for t in tokens:
        # 특수문자 제거
        cleaned = re.sub(r'[^\w가-힣]', '', t)
        if (cleaned and len(cleaned) >= 2
                and cleaned not in _KO_STOPWORDS
                and cleaned not in _EN_STOPWORDS):
            result.append(cleaned)
    return result


def _get_body_keywords(content: str, top_n: int = 10) -> List[str]:
    """본문에서 상위 키워드를 추출합니다."""
    body = _HEADING_RE.sub('', content)
    tokens = _tokenize(body)
    counter = Counter(tokens)
    return [word for word, _ in counter.most_common(top_n)]


_EMPTY_RESULT = {
    'headings': [],
    'keyword_coverage': [],
    'summary': {
        'total_headings': 0, 'body_keywords_in_headings': 0,
        'coverage_ratio': 0.0, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _analyze_keyword_coverage(headings: List[Dict], body_keywords: List[str]) -> tuple:
    """헤딩과 본문 키워드의 커버리지를 분석합니다.

    Returns:
        (heading_data, keyword_coverage, covered, duplicated, coverage_ratio)
    """
    heading_data = []
    all_heading_tokens = set()
    heading_keyword_counter = Counter()

    for h in headings:
        tokens = _tokenize(h['text'])
        all_heading_tokens.update(tokens)
        heading_keyword_counter.update(tokens)
        heading_data.append({
            'level': h['level'],
            'text': h['text'] if len(h['text']) <= 50 else h['text'][:47] + '...',
            'keywords': tokens[:5],
            'keyword_count': len(tokens),
        })

    covered = [kw for kw in body_keywords if kw in all_heading_tokens]
    coverage_ratio = round(len(covered) / max(len(body_keywords), 1) * 100, 1)

    keyword_coverage = [
        {'keyword': kw, 'in_heading': kw in all_heading_tokens}
        for kw in body_keywords
    ]

    duplicated = {kw: c for kw, c in heading_keyword_counter.items() if c >= 3}

    return heading_data, keyword_coverage, covered, duplicated, coverage_ratio


def _compute_density_score(coverage_ratio: float, duplicated: dict) -> tuple:
    """커버리지 비율로 점수와 레벨을 계산합니다.

    Returns:
        (score, level)
    """
    if coverage_ratio >= 60:
        level = 'excellent'
    elif coverage_ratio >= 40:
        level = 'good'
    elif coverage_ratio >= 20:
        level = 'fair'
    else:
        level = 'poor'

    score = min(100.0, coverage_ratio * 1.5)
    if duplicated:
        score -= min(20.0, len(duplicated) * 5.0)

    return round(max(0.0, min(100.0, score)), 1), level


def analyze_heading_keyword_density(content: str) -> dict:
    """헤딩 키워드 밀도를 분석합니다.

    Returns:
        headings, keyword_coverage, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    headings = _extract_headings(content)
    if not headings:
        return {**_EMPTY_RESULT, 'score': 50.0,
                'suggestions': ['헤딩이 없습니다. H1~H6 헤딩을 추가하세요.']}

    body_keywords = _get_body_keywords(content)
    heading_data, keyword_coverage, covered, duplicated, coverage_ratio = (
        _analyze_keyword_coverage(headings, body_keywords)
    )
    score, level = _compute_density_score(coverage_ratio, duplicated)

    suggestions = _generate_suggestions(
        coverage_ratio, level, body_keywords, covered, duplicated, len(headings)
    )

    return {
        'headings': heading_data[:20],
        'keyword_coverage': keyword_coverage[:10],
        'summary': {
            'total_headings': len(headings),
            'body_keywords_in_headings': len(covered),
            'coverage_ratio': coverage_ratio,
            'duplicated_keywords': list(duplicated.keys())[:5],
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(ratio: float, level: str,
                           body_kws: List[str], covered: List[str],
                           duplicated: dict, heading_count: int) -> List[str]:
    suggestions = []
    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡', 'none': '없음',
    }
    suggestions.append(
        f'헤딩 키워드 커버리지 {ratio}% ({level_labels.get(level, level)}). '
        f'본문 상위 키워드 {len(body_kws)}개 중 {len(covered)}개가 헤딩에 포함.'
    )

    uncovered = [kw for kw in body_kws if kw not in covered]
    if uncovered:
        miss_list = ', '.join(uncovered[:3])
        suggestions.append(
            f'헤딩에 누락된 키워드: {miss_list}. '
            f'관련 섹션 헤딩에 포함하면 SEO에 유리합니다.'
        )

    if duplicated:
        dup_list = ', '.join(list(duplicated.keys())[:3])
        suggestions.append(
            f'헤딩에서 과다 반복 키워드: {dup_list}. '
            f'다양한 표현으로 바꾸세요.'
        )

    return suggestions
