"""
URL Health Checker 서비스

콘텐츠 내 URL의 형식, 프로토콜, 도메인 유효성을 검증합니다.
실제 HTTP 요청 없이 패턴 기반으로 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
from urllib.parse import urlparse

# URL 추출 패턴
_URL_RE = re.compile(
    r'(?:https?://[^\s\)<>\]"\']+|'
    r'www\.[^\s\)<>\]"\']+)',
    re.IGNORECASE
)

# 마크다운 링크
_MD_LINK_RE = re.compile(r'\[([^\]]*)\]\(([^)]+)\)')

# HTML 링크
_HTML_LINK_RE = re.compile(r'href=["\']([^"\']+)["\']', re.IGNORECASE)

# 문제 도메인 (예시/플레이스홀더)
_PLACEHOLDER_DOMAINS = {
    'example.com', 'example.org', 'example.net',
    'your-domain.com', 'yourdomain.com', 'domain.com',
    'placeholder.com', 'test.com', 'localhost',
}

# 의심스러운 파일 확장자
_SUSPICIOUS_EXT = re.compile(r'\.(exe|bat|cmd|msi|dll|scr|vbs|js)$', re.IGNORECASE)


def _extract_urls(content: str) -> List[Dict]:
    """콘텐츠에서 모든 URL을 추출합니다."""
    urls = []
    seen = set()

    # 마크다운 링크
    for match in _MD_LINK_RE.finditer(content):
        url = match.group(2).strip()
        if url not in seen and not url.startswith('#'):
            seen.add(url)
            urls.append({'url': url, 'context': 'markdown_link',
                         'text': match.group(1)})

    # HTML 링크
    for match in _HTML_LINK_RE.finditer(content):
        url = match.group(1).strip()
        if url not in seen and not url.startswith('#') and not url.startswith('mailto:'):
            seen.add(url)
            urls.append({'url': url, 'context': 'html_link', 'text': ''})

    # 일반 URL
    for match in _URL_RE.finditer(content):
        url = match.group().rstrip('.,;:!?)')
        if url not in seen:
            seen.add(url)
            urls.append({'url': url, 'context': 'inline', 'text': ''})

    return urls


def _check_url(url: str) -> Dict:
    """단일 URL의 건강 상태를 검사합니다."""
    issues = []

    # 프로토콜 체크
    if url.startswith('http://'):
        issues.append('HTTP (비보안). HTTPS로 변경 권장.')
    elif not url.startswith('https://') and not url.startswith('//'):
        if url.startswith('www.'):
            issues.append('프로토콜 누락. https://를 추가하세요.')
        # 상대 경로 등은 스킵

    # URL 파싱
    try:
        parsed = urlparse(url if '://' in url else f'https://{url}')
    except Exception:
        issues.append('URL 파싱 실패.')
        return {'url': url, 'issues': issues, 'status': 'error'}

    domain = parsed.hostname or ''

    # 플레이스홀더 도메인
    if domain in _PLACEHOLDER_DOMAINS:
        issues.append(f'플레이스홀더 도메인 ({domain}). 실제 URL로 교체하세요.')

    # 도메인 형식
    if domain and not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', domain):
        if domain != 'localhost':
            issues.append(f'도메인 형식 이상: {domain}.')

    # 의심스러운 확장자
    if _SUSPICIOUS_EXT.search(parsed.path):
        issues.append('의심스러운 파일 확장자. 보안 위험이 있을 수 있습니다.')

    # 쿼리 파라미터 과다
    if parsed.query and parsed.query.count('&') > 5:
        issues.append('쿼리 파라미터가 과다합니다. URL을 정리하세요.')

    # URL 길이
    if len(url) > 200:
        issues.append(f'URL 길이 {len(url)}자로 과도합니다.')

    status = 'error' if issues else 'ok'
    return {'url': url, 'issues': issues, 'status': status}


_EMPTY_RESULT = {
    'url_results': [],
    'summary': {'total_urls': 0, 'healthy': 0,
                'issues_found': 0, 'health_rate': 100.0},
    'score': 100.0,
    'suggestions': [],
}


def check_url_health(content: str) -> dict:
    """콘텐츠 내 URL 건강 상태를 검사합니다.

    Returns:
        url_results, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    extracted = _extract_urls(content)
    if not extracted:
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠에 URL이 없습니다.']}

    results, healthy, issues_count = _evaluate_urls(extracted)
    total = len(results)
    health_rate = round(healthy / total * 100, 1) if total > 0 else 100.0
    score = round(max(0.0, min(100.0, health_rate)), 1)

    return {
        'url_results': results[:30],
        'summary': {
            'total_urls': total, 'healthy': healthy,
            'issues_found': issues_count, 'health_rate': health_rate,
        },
        'score': score,
        'suggestions': _generate_suggestions(results, healthy, total, health_rate),
    }


def _evaluate_urls(extracted: List[Dict]) -> tuple:
    """추출된 URL 목록을 검사하여 (results, healthy, issues_count) 튜플을 반환합니다."""
    results = []
    healthy = 0
    issues_count = 0
    for item in extracted:
        check = _check_url(item['url'])
        check['context'] = item['context']
        results.append(check)
        if check['status'] == 'ok':
            healthy += 1
        else:
            issues_count += len(check['issues'])
    return results, healthy, issues_count


def _generate_suggestions(results: List[Dict], healthy: int,
                           total: int, rate: float) -> List[str]:
    suggestions = []

    if rate == 100.0:
        suggestions.append(f'모든 URL ({total}개)이 형식적으로 정상입니다.')
        return suggestions

    suggestions.append(f'URL {total}개 중 {total - healthy}개에 이슈가 있습니다 (정상률 {rate}%).')

    # 주요 이슈 요약
    http_count = sum(1 for r in results if any('HTTP' in i for i in r['issues']))
    placeholder_count = sum(1 for r in results if any('플레이스홀더' in i for i in r['issues']))

    if http_count > 0:
        suggestions.append(f'HTTP URL {http_count}개: HTTPS로 변경하세요.')
    if placeholder_count > 0:
        suggestions.append(f'플레이스홀더 도메인 {placeholder_count}개: 실제 URL로 교체하세요.')

    return suggestions
