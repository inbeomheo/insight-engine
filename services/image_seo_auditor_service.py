"""
Image SEO Auditor 서비스

마크다운 콘텐츠의 이미지 태그에서 alt 텍스트, 파일명, 캡션 등
SEO 관련 속성의 품질을 점검합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# 마크다운 이미지: ![alt](url "title")
_MD_IMAGE_RE = re.compile(
    r'!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)'
)

# HTML img 태그
_HTML_IMG_RE = re.compile(
    r'<img\s[^>]*?>', re.IGNORECASE | re.DOTALL
)
_SRC_RE = re.compile(r'src=["\']([^"\']+)["\']', re.IGNORECASE)
_ALT_RE = re.compile(r'alt=["\']([^"\']*)["\']', re.IGNORECASE)
_TITLE_RE = re.compile(r'title=["\']([^"\']*)["\']', re.IGNORECASE)

# 의미 없는 alt 텍스트
_GENERIC_ALT = {
    'image', 'img', 'photo', 'picture', 'screenshot', 'untitled',
    '이미지', '사진', '그림', '스크린샷', '캡처',
}

# 이미지 확장자
_IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp', '.avif'}

# 의미 없는 파일명 패턴 (UUID, 타임스탬프, 해시)
_MEANINGLESS_FILENAME = re.compile(
    r'^(?:[0-9a-f]{8,}|[0-9]{10,}|image\d*|img\d*|screenshot\d*|untitled\d*|download\d*)$',
    re.IGNORECASE
)


def _extract_filename(url: str) -> str:
    """URL에서 파일명(확장자 제외)을 추출합니다."""
    # 쿼리 파라미터 제거
    clean = url.split('?')[0].split('#')[0]
    # 마지막 경로 세그먼트
    parts = clean.rstrip('/').split('/')
    filename = parts[-1] if parts else ''
    # 확장자 제거
    dot = filename.rfind('.')
    if dot > 0:
        return filename[:dot]
    return filename


def _check_alt_quality(alt: str) -> Dict:
    """alt 텍스트 품질을 평가합니다."""
    if not alt or not alt.strip():
        return {'status': 'missing', 'issue': 'alt 텍스트 누락'}
    cleaned = alt.strip().lower()
    if cleaned in _GENERIC_ALT:
        return {'status': 'generic', 'issue': f'의미 없는 alt: "{alt}"'}
    if len(cleaned) < 5:
        return {'status': 'too_short', 'issue': f'alt 텍스트가 너무 짧음 ({len(alt)}자)'}
    if len(cleaned) > 125:
        return {'status': 'too_long', 'issue': f'alt 텍스트가 너무 긺 ({len(alt)}자, 권장 125자 이내)'}
    return {'status': 'good', 'issue': None}


def _check_filename_quality(url: str) -> Dict:
    """파일명 품질을 평가합니다."""
    filename = _extract_filename(url)
    if not filename:
        return {'status': 'unknown', 'issue': '파일명 추출 불가'}
    if _MEANINGLESS_FILENAME.match(filename):
        return {'status': 'meaningless', 'issue': f'의미 없는 파일명: "{filename}"'}
    if '_' in filename and '-' not in filename:
        return {'status': 'underscore', 'issue': f'파일명에 언더스코어 사용 (하이픈 권장): "{filename}"'}
    return {'status': 'good', 'issue': None}


def audit_image_seo(content: str) -> dict:
    """이미지 SEO 속성을 점검합니다.

    Args:
        content: 분석할 마크다운/HTML 콘텐츠

    Returns:
        images, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'images': [],
            'summary': {'total_images': 0, 'missing_alt': 0, 'generic_alt': 0,
                        'good_alt': 0, 'meaningless_filename': 0},
            'score': 100.0,
            'suggestions': [],
        }

    images = []

    # 마크다운 이미지
    for match in _MD_IMAGE_RE.finditer(content):
        alt = match.group(1)
        url = match.group(2)
        title = match.group(3) or ''
        alt_check = _check_alt_quality(alt)
        fname_check = _check_filename_quality(url)
        images.append({
            'src': url,
            'alt': alt,
            'title': title,
            'format': 'markdown',
            'alt_status': alt_check['status'],
            'alt_issue': alt_check['issue'],
            'filename_status': fname_check['status'],
            'filename_issue': fname_check['issue'],
        })

    # HTML img 태그
    for tag_match in _HTML_IMG_RE.finditer(content):
        tag = tag_match.group(0)
        src_m = _SRC_RE.search(tag)
        alt_m = _ALT_RE.search(tag)
        title_m = _TITLE_RE.search(tag)
        url = src_m.group(1) if src_m else ''
        alt = alt_m.group(1) if alt_m else ''
        title = title_m.group(1) if title_m else ''
        alt_check = _check_alt_quality(alt)
        fname_check = _check_filename_quality(url) if url else {'status': 'unknown', 'issue': None}
        images.append({
            'src': url,
            'alt': alt,
            'title': title,
            'format': 'html',
            'alt_status': alt_check['status'],
            'alt_issue': alt_check['issue'],
            'filename_status': fname_check['status'],
            'filename_issue': fname_check['issue'],
        })

    if not images:
        return {
            'images': [],
            'summary': {'total_images': 0, 'missing_alt': 0, 'generic_alt': 0,
                        'good_alt': 0, 'meaningless_filename': 0},
            'score': 100.0,
            'suggestions': ['이미지가 없습니다. 시각 자료를 추가하면 콘텐츠 품질이 향상됩니다.'],
        }

    # 집계
    missing_alt = sum(1 for img in images if img['alt_status'] == 'missing')
    generic_alt = sum(1 for img in images if img['alt_status'] == 'generic')
    short_alt = sum(1 for img in images if img['alt_status'] == 'too_short')
    long_alt = sum(1 for img in images if img['alt_status'] == 'too_long')
    good_alt = sum(1 for img in images if img['alt_status'] == 'good')
    meaningless_fn = sum(1 for img in images if img['filename_status'] == 'meaningless')

    total = len(images)
    issues = missing_alt + generic_alt + short_alt + long_alt + meaningless_fn
    score = round(max(0.0, (1.0 - issues / (total * 2)) * 100.0), 1)
    score = max(0.0, min(100.0, score))

    suggestions = _generate_suggestions(
        total, missing_alt, generic_alt, short_alt, long_alt, meaningless_fn
    )

    return {
        'images': images,
        'summary': {
            'total_images': total,
            'missing_alt': missing_alt,
            'generic_alt': generic_alt,
            'good_alt': good_alt,
            'meaningless_filename': meaningless_fn,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(
    total: int, missing: int, generic: int, short: int, long: int, meaningless: int
) -> List[str]:
    suggestions = []
    if missing > 0:
        suggestions.append(f'alt 텍스트 누락 {missing}개: 모든 이미지에 설명적 alt 텍스트를 추가하세요.')
    if generic > 0:
        suggestions.append(f'의미 없는 alt {generic}개: "이미지", "사진" 대신 구체적 설명을 사용하세요.')
    if short > 0:
        suggestions.append(f'alt 텍스트가 짧은 이미지 {short}개: 5자 이상의 설명을 권장합니다.')
    if long > 0:
        suggestions.append(f'alt 텍스트가 긴 이미지 {long}개: 125자 이내로 줄이세요.')
    if meaningless > 0:
        suggestions.append(f'의미 없는 파일명 {meaningless}개: SEO에 도움되는 설명적 파일명을 사용하세요.')
    if not suggestions:
        suggestions.append('모든 이미지의 SEO 속성이 양호합니다.')
    return suggestions
