"""
Meta Description Quality Checker 서비스

콘텐츠에서 메타 디스크립션(또는 첫 문단 요약)의 품질을 점검합니다.
길이, 키워드 포함, 행동 유도 표현 등을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 메타 디스크립션 패턴 (HTML)
_META_DESC_RE = re.compile(
    r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']',
    re.IGNORECASE
)

# 마크다운 프론트매터 description
_FRONTMATTER_DESC_RE = re.compile(
    r'^---\s*\n.*?description:\s*["\']?(.+?)["\']?\s*\n.*?---',
    re.DOTALL
)

# CTA 키워드
_CTA_WORDS = re.compile(
    r'(?:알아보|확인하|시작하|배우|발견|찾아보|도전|Learn|Discover|Find|Get|Start|Try)',
    re.IGNORECASE
)

# 숫자/구체성
_SPECIFICITY = re.compile(r'\d+')


def _extract_description(content: str) -> str:
    """메타 디스크립션 또는 첫 문단을 추출합니다."""
    # HTML meta description
    m = _META_DESC_RE.search(content)
    if m:
        return m.group(1).strip()

    # 프론트매터 description
    m = _FRONTMATTER_DESC_RE.search(content)
    if m:
        return m.group(1).strip()

    # 첫 비-헤딩 문단
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and len(stripped) >= 10:
            # 첫 문장만
            sentences = re.split(r'[.!?]\s', stripped)
            if sentences:
                first = sentences[0].strip()
                if len(first) >= 10:
                    return first + ('.' if not first.endswith('.') else '')
            return stripped
    return ''


def check_meta_description_quality(content: str) -> dict:
    """메타 디스크립션 품질을 점검합니다.

    Returns:
        description, checks, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'description': '',
            'checks': {},
            'summary': {'length': 0, 'quality_level': 'none'},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    desc = _extract_description(content)
    if not desc:
        return {
            'description': '',
            'checks': {},
            'summary': {'length': 0, 'quality_level': 'none'},
            'score': 0.0,
            'suggestions': ['메타 디스크립션이나 도입 문단을 추가하세요.'],
        }

    length = len(desc)

    # 길이 체크 (권장: 120-160자)
    length_ok = 120 <= length <= 160
    length_short = length < 80
    length_long = length > 200

    # CTA 포함
    has_cta = bool(_CTA_WORDS.search(desc))

    # 구체적 숫자 포함
    has_numbers = bool(_SPECIFICITY.search(desc))

    # 마침표로 끝남
    ends_properly = desc.rstrip().endswith(('.', '!', '?', '다', '요'))

    # 중복 단어 체크
    words = re.findall(r'[가-힣]{2,}|[A-Za-z]{3,}', desc.lower())
    unique_ratio = len(set(words)) / len(words) if words else 1.0
    no_repetition = unique_ratio >= 0.7

    checks = {
        'optimal_length': length_ok,
        'has_cta': has_cta,
        'has_specificity': has_numbers,
        'ends_properly': ends_properly,
        'no_repetition': no_repetition,
    }

    passed = sum(1 for v in checks.values() if v)
    score = round(min(100.0, passed * 20.0), 1)

    # 길이 보너스/페널티
    if length_short:
        score = max(0.0, score - 15.0)
    elif length_long:
        score = max(0.0, score - 10.0)

    score = round(max(0.0, min(100.0, score)), 1)

    if score >= 80:
        quality = 'excellent'
    elif score >= 50:
        quality = 'good'
    elif score >= 20:
        quality = 'fair'
    else:
        quality = 'poor'

    suggestions = _generate_suggestions(checks, length, length_ok, length_short, length_long)

    return {
        'description': desc if len(desc) <= 200 else desc[:197] + '...',
        'checks': checks,
        'summary': {'length': length, 'quality_level': quality},
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(checks: Dict, length: int, ok: bool, short: bool, long: bool) -> List[str]:
    suggestions = []
    if short:
        suggestions.append(f'디스크립션 {length}자로 너무 짧습니다 (권장: 120-160자).')
    elif long:
        suggestions.append(f'디스크립션 {length}자로 너무 깁니다 (권장: 120-160자). 검색 결과에서 잘릴 수 있습니다.')
    elif ok:
        suggestions.append(f'디스크립션 길이 {length}자로 적정합니다.')

    if not checks.get('has_cta'):
        suggestions.append('행동 유도 표현(알아보세요, Learn more 등)을 추가하면 CTR이 향상됩니다.')
    if not checks.get('has_specificity'):
        suggestions.append('구체적 숫자(5가지 방법, 10분 가이드 등)를 포함하면 클릭율이 높아집니다.')
    return suggestions
