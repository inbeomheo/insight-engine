"""
앵커 텍스트 품질 감사 서비스

콘텐츠 내 링크의 앵커 텍스트 품질을 검사하여
SEO 및 접근성 개선 제안을 생성합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 모호한 앵커 텍스트 (bad)
_BAD_ANCHORS = {
    '여기', '클릭', '이곳', '여기를 클릭하세요', '여기를 클릭',
    '클릭하세요', '이곳을 클릭', '눌러주세요', '누르세요',
    'click here', 'here', 'link', 'this', 'click', 'click this',
}

# 일반적 앵커 텍스트 (generic)
_GENERIC_ANCHORS = {
    '자세히 보기', '더보기', '더 보기', '자세히', '바로가기', '바로 가기',
    '확인하기', '보러가기', '보러 가기', '알아보기', '알아 보기',
    'read more', 'learn more', 'see more', 'more info', 'details',
    'more details', 'find out more', 'view more', 'go', 'see here',
}

# URL 패턴 (naked_url 판별용)
_URL_PATTERN = re.compile(r'^https?://', re.IGNORECASE)

# 마크다운 링크: [텍스트](URL)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

# HTML 링크: <a href="URL">텍스트</a>
_HTML_LINK_RE = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.IGNORECASE | re.DOTALL)


def audit_anchor_texts(content: str) -> dict:
    """콘텐츠 내 링크의 앵커 텍스트 품질을 감사합니다.

    Args:
        content: 분석할 콘텐츠 (마크다운 또는 HTML)

    Returns:
        {
            "links": [{"anchor": str, "url": str, "quality": str, "suggestion": str}],
            "summary": {"total": int, "good": int, "generic": int, "bad": int, "naked_url": int},
            "anchor_quality_score": float,  # 0-100
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'links': [],
            'summary': {'total': 0, 'good': 0, 'generic': 0, 'bad': 0, 'naked_url': 0},
            'anchor_quality_score': 100.0,
            'suggestions': [],
        }

    # 링크 추출
    raw_links = _extract_links(content)

    if not raw_links:
        return {
            'links': [],
            'summary': {'total': 0, 'good': 0, 'generic': 0, 'bad': 0, 'naked_url': 0},
            'anchor_quality_score': 100.0,
            'suggestions': [],
        }

    # 각 링크 품질 판정
    links = []
    for anchor, url in raw_links:
        quality = _classify_anchor(anchor)
        suggestion = _make_suggestion(anchor, url, quality)
        links.append({
            'anchor': anchor,
            'url': url,
            'quality': quality,
            'suggestion': suggestion,
        })

    # 요약 집계
    summary = {'total': len(links), 'good': 0, 'generic': 0, 'bad': 0, 'naked_url': 0}
    for link in links:
        summary[link['quality']] += 1

    # 품질 점수 계산 (good=100, generic=50, bad=0, naked_url=0)
    score = _calculate_score(summary)

    # 개선 제안 생성
    suggestions = _generate_suggestions(summary, links)

    return {
        'links': links,
        'summary': summary,
        'anchor_quality_score': score,
        'suggestions': suggestions,
    }


def _extract_links(content: str) -> list:
    """마크다운 및 HTML 링크를 추출합니다.

    Returns:
        [(anchor, url), ...]
    """
    links = []

    # 마크다운 링크 추출
    for match in _MD_LINK_RE.finditer(content):
        anchor = match.group(1).strip()
        url = match.group(2).strip()
        if anchor and url:
            links.append((anchor, url))

    # HTML 링크 추출
    for match in _HTML_LINK_RE.finditer(content):
        url = match.group(1).strip()
        anchor = match.group(2).strip()
        # HTML 태그 제거 (중첩 태그 처리)
        anchor = re.sub(r'<[^>]+>', '', anchor).strip()
        if anchor and url:
            links.append((anchor, url))

    return links


def _classify_anchor(anchor: str) -> str:
    """앵커 텍스트 품질을 분류합니다.

    Returns:
        'bad', 'generic', 'good', 'naked_url' 중 하나
    """
    normalized = anchor.strip().lower()

    # naked_url: 앵커가 URL 자체인 경우
    if _URL_PATTERN.match(normalized):
        return 'naked_url'

    # bad: 모호한 앵커
    if normalized in _BAD_ANCHORS:
        return 'bad'

    # generic: 일반적 앵커
    if normalized in _GENERIC_ANCHORS:
        return 'generic'

    # 너무 짧은 앵커 (3자 미만)는 bad
    if len(normalized) < 3:
        return 'bad'

    return 'good'


def _make_suggestion(anchor: str, url: str, quality: str) -> str:
    """품질에 따른 개선 제안을 생성합니다."""
    if quality == 'good':
        return ''

    if quality == 'naked_url':
        return f'URL 대신 링크 대상의 내용을 설명하는 구체적 텍스트를 사용하세요.'

    if quality == 'bad':
        return f'"{anchor}" 대신 링크 대상의 주제를 설명하는 구체적 앵커 텍스트를 사용하세요.'

    if quality == 'generic':
        return f'"{anchor}" 대신 링크 내용을 구체적으로 설명하는 앵커 텍스트를 사용하세요.'

    return ''


def _calculate_score(summary: dict) -> float:
    """앵커 텍스트 품질 점수를 계산합니다 (0-100)."""
    total = summary['total']
    if total == 0:
        return 100.0

    # good=100점, generic=50점, bad/naked_url=0점
    weighted = (summary['good'] * 100) + (summary['generic'] * 50)
    score = weighted / total

    return round(score, 1)


def _generate_suggestions(summary: dict, links: list) -> list:
    """전체적인 개선 제안을 생성합니다."""
    suggestions = []

    if summary['bad'] > 0:
        suggestions.append(
            f'모호한 앵커 텍스트가 {summary["bad"]}개 발견되었습니다. '
            f'"여기", "클릭" 등 대신 링크 대상을 설명하는 구체적 텍스트를 사용하세요.'
        )

    if summary['naked_url'] > 0:
        suggestions.append(
            f'URL이 그대로 노출된 링크가 {summary["naked_url"]}개 있습니다. '
            f'URL 대신 설명적인 앵커 텍스트로 교체하세요.'
        )

    if summary['generic'] > 0:
        suggestions.append(
            f'일반적인 앵커 텍스트가 {summary["generic"]}개 있습니다. '
            f'"자세히 보기" 등을 더 구체적인 설명으로 바꾸면 SEO와 접근성이 향상됩니다.'
        )

    if summary['total'] > 0 and summary['good'] == summary['total']:
        suggestions.append('모든 앵커 텍스트가 구체적이고 설명적입니다. 좋은 품질입니다.')

    return suggestions
