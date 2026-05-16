"""
이미지 대체 텍스트(alt) 감사 서비스

접근성(WCAG 1.1.1)과 SEO 관점에서 콘텐츠의 이미지가
적절한 alt 텍스트를 가지고 있는지 검사합니다.

감지 항목:
- 누락된 alt (`![](...)`)
- 너무 짧은 alt (2자 이하)
- 너무 긴 alt (125자 초과, 스크린 리더 권장치 기준)
- 파일명 그대로 사용 (`alt="image.jpg"`)
- 중복 alt 텍스트
- 금지어 사용 ("image of", "picture of" 등 리던던트 표현)
- 장식용(`alt=""`) 임을 명시한 케이스는 통과
"""
import logging
import re
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# 마크다운 이미지: ![alt](url "title")
_MD_IMAGE_PATTERN = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<url>[^\s)]+)(?:\s+"[^"]*")?\)')
# HTML img 태그
_HTML_IMG_PATTERN = re.compile(r'<img\s+[^>]*>', re.IGNORECASE)
_HTML_ALT_ATTR = re.compile(r"""alt\s*=\s*["']([^"']*)["']""", re.IGNORECASE)
_HTML_SRC_ATTR = re.compile(r"""src\s*=\s*["']([^"']+)["']""", re.IGNORECASE)

# 파일명 패턴 (alt 텍스트가 파일명에 불과한지 검사)
_FILENAME_PATTERN = re.compile(r'^[\w\-]+\.(png|jpe?g|gif|webp|svg|bmp|tiff?|heic)$', re.IGNORECASE)

MIN_ALT_LENGTH = 3
MAX_ALT_LENGTH = 125

# 리던던트 표현 (alt에는 "image of ..." 같은 접두 불필요)
REDUNDANT_PREFIXES = (
    'image of', 'picture of', 'photo of', 'graphic of',
    '이미지', '사진', '그림', 'image:', 'photo:',
)


def audit_image_alt_texts(content: str) -> dict:
    """콘텐츠의 이미지들을 검사해 접근성·SEO 관점 이슈를 보고합니다.

    Returns:
        {
            'total': int,
            'issues': [{'type': str, 'severity': 'error'|'warning',
                        'url': str, 'alt': str, 'index': int, 'message': str}],
            'decorative_count': int,   # 의도적으로 비워둔 alt="" 개수
            'issue_count': int,
            'score': int,              # 0~100
        }
    """
    if not content:
        return _empty_result()

    images = _extract_images(content)
    if not images:
        return _empty_result()

    issues: List[dict] = []
    alt_seen: dict = {}
    decorative_count = 0

    for idx, (alt, url, is_decorative_intent) in enumerate(images):
        alt_stripped = alt.strip()

        # alt="" 이면서 URL이 있는 경우 — 장식용으로 간주
        if alt == '' and not is_decorative_intent:
            # 마크다운 이미지에서 alt가 비어 있음 — 접근성 경고
            issues.append({
                'type': 'missing_alt',
                'severity': 'error',
                'url': url,
                'alt': '',
                'index': idx,
                'message': '이미지에 alt 텍스트가 없습니다. 장식용이면 alt="decorative"로 명시하세요.',
            })
            continue

        if is_decorative_intent:
            decorative_count += 1
            continue

        if len(alt_stripped) < MIN_ALT_LENGTH:
            issues.append({
                'type': 'too_short',
                'severity': 'warning',
                'url': url,
                'alt': alt,
                'index': idx,
                'message': f'alt 텍스트가 너무 짧습니다 ({len(alt_stripped)}자).',
            })

        if len(alt_stripped) > MAX_ALT_LENGTH:
            issues.append({
                'type': 'too_long',
                'severity': 'warning',
                'url': url,
                'alt': alt,
                'index': idx,
                'message': f'alt 텍스트가 너무 깁니다 ({len(alt_stripped)}자, 권장 {MAX_ALT_LENGTH}자 이하).',
            })

        if _FILENAME_PATTERN.match(alt_stripped):
            issues.append({
                'type': 'filename_as_alt',
                'severity': 'error',
                'url': url,
                'alt': alt,
                'index': idx,
                'message': 'alt 텍스트가 파일명처럼 보입니다. 내용을 설명하는 문장으로 바꾸세요.',
            })

        lower = alt_stripped.lower()
        for prefix in REDUNDANT_PREFIXES:
            if lower.startswith(prefix):
                issues.append({
                    'type': 'redundant_prefix',
                    'severity': 'warning',
                    'url': url,
                    'alt': alt,
                    'index': idx,
                    'message': f'"{prefix}" 같은 불필요한 접두어를 제거하세요.',
                })
                break

        # 중복 감지
        if alt_stripped and alt_stripped in alt_seen:
            issues.append({
                'type': 'duplicate_alt',
                'severity': 'warning',
                'url': url,
                'alt': alt,
                'index': idx,
                'message': f'{alt_seen[alt_stripped] + 1}번째 이미지와 alt 텍스트가 동일합니다.',
            })
        if alt_stripped:
            alt_seen[alt_stripped] = idx

    score = _calculate_score(len(images), issues)
    return {
        'total': len(images),
        'issues': issues,
        'decorative_count': decorative_count,
        'issue_count': len(issues),
        'score': score,
    }


def suggest_alt_from_url(url: str) -> str:
    """이미지 URL에서 최소한의 alt 텍스트 후보를 생성합니다.

    파일명에서 확장자를 제거하고 하이픈/언더스코어를 공백으로 치환합니다.
    생성된 문자열은 임시 초안일 뿐, 사람이 반드시 편집해야 합니다.
    """
    if not url:
        return ''
    # URL 경로의 마지막 세그먼트
    segment = url.split('?')[0].split('#')[0].rstrip('/').split('/')[-1]
    # 확장자 제거
    name = re.sub(r'\.(png|jpe?g|gif|webp|svg|bmp|tiff?|heic)$', '', segment, flags=re.IGNORECASE)
    # 구분자 → 공백
    name = re.sub(r'[_\-]+', ' ', name)
    # 숫자 시퀀스 정리 (IMG_0123 같은 경우 숫자 분리)
    name = re.sub(r'\d{4,}', '', name).strip()
    return name


def _extract_images(content: str) -> List[Tuple[str, str, bool]]:
    """콘텐츠의 모든 이미지 (alt, url, is_decorative_intent) 튜플 리스트."""
    results: List[Tuple[str, str, bool]] = []

    for match in _MD_IMAGE_PATTERN.finditer(content):
        alt = match.group('alt')
        url = match.group('url')
        # 마크다운 이미지는 `decorative` 표식이 없음 → 빈 alt는 '누락'으로 판정
        results.append((alt, url, False))

    for match in _HTML_IMG_PATTERN.finditer(content):
        img_html = match.group(0)
        alt_match = _HTML_ALT_ATTR.search(img_html)
        src_match = _HTML_SRC_ATTR.search(img_html)
        if not src_match:
            continue
        url = src_match.group(1)
        if alt_match:
            alt = alt_match.group(1)
            # alt="" + aria-hidden="true" 또는 alt="decorative" → 의도적 장식
            lower_html = img_html.lower()
            is_decorative = (
                alt.strip().lower() == 'decorative'
                or 'aria-hidden="true"' in lower_html
                or "aria-hidden='true'" in lower_html
                or (alt == '' and 'role="presentation"' in lower_html)
            )
            results.append((alt, url, is_decorative))
        else:
            results.append(('', url, False))

    return results


def _calculate_score(total: int, issues: List[dict]) -> int:
    """이슈 비율과 심각도에 따라 점수를 계산합니다."""
    if total == 0:
        return 100
    penalty = 0.0
    for issue in issues:
        penalty += 8 if issue['severity'] == 'error' else 3
    # 전체 이미지 수 대비 상대 영향
    normalized = penalty / total
    score = int(round(max(0.0, min(100.0, 100 - normalized * 10))))
    return score


def _empty_result() -> dict:
    return {
        'total': 0,
        'issues': [],
        'decorative_count': 0,
        'issue_count': 0,
        'score': 100,
    }
