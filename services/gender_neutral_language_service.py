"""
Gender-Neutral Language Checker 서비스

콘텐츠에서 성별 편향 표현을 감지하고 포용적 대안을 제안합니다.
한국어/영어의 성별 고정관념 표현, 불필요한 성별 구분을 검사합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 성별 편향 표현 (패턴, 감지 텍스트, 대안)
_KO_GENDERED = [
    (re.compile(r'(?<![A-Za-z0-9])(?:여사원|여직원)(?![A-Za-z0-9])', re.UNICODE), '여사원/여직원', '직원'),
    (re.compile(r'(?<![A-Za-z0-9])(?:남사원|남직원)(?![A-Za-z0-9])', re.UNICODE), '남사원/남직원', '직원'),
    (re.compile(r'(?<![A-Za-z0-9])여의사(?![A-Za-z0-9])', re.UNICODE), '여의사', '의사'),
    (re.compile(r'(?<![A-Za-z0-9])여교사(?![A-Za-z0-9])', re.UNICODE), '여교사', '교사'),
    (re.compile(r'(?<![A-Za-z0-9])여류(?![A-Za-z0-9])', re.UNICODE), '여류', '(직업명만 사용)'),
    (re.compile(r'(?<![A-Za-z0-9])여걸(?![A-Za-z0-9])', re.UNICODE), '여걸', '리더/전문가'),
    (re.compile(r'(?<![A-Za-z0-9])아줌마(?![A-Za-z0-9])', re.UNICODE), '아줌마', '성인/시민'),
    (re.compile(r'(?<![A-Za-z0-9])처녀작(?![A-Za-z0-9])', re.UNICODE), '처녀작', '데뷔작/첫 작품'),
    (re.compile(r'(?<![A-Za-z0-9])(?:그녀|그는)\s', re.UNICODE), '그녀/그는', '해당 인물의 이름 또는 직함'),
]

# 영어 성별 편향 표현
_EN_GENDERED = [
    (re.compile(r'\bchairman\b', re.IGNORECASE), 'chairman', 'chairperson/chair'),
    (re.compile(r'\bpoliceman\b', re.IGNORECASE), 'policeman', 'police officer'),
    (re.compile(r'\bfireman\b', re.IGNORECASE), 'fireman', 'firefighter'),
    (re.compile(r'\bstewardess\b', re.IGNORECASE), 'stewardess', 'flight attendant'),
    (re.compile(r'\bmailman\b', re.IGNORECASE), 'mailman', 'mail carrier'),
    (re.compile(r'\bmanpower\b', re.IGNORECASE), 'manpower', 'workforce/staff'),
    (re.compile(r'\bmankind\b', re.IGNORECASE), 'mankind', 'humankind/humanity'),
    (re.compile(r'\bman-made\b', re.IGNORECASE), 'man-made', 'artificial/synthetic'),
    (re.compile(r'\bsalesman\b', re.IGNORECASE), 'salesman', 'salesperson'),
    (re.compile(r'\bforeman\b', re.IGNORECASE), 'foreman', 'supervisor'),
    (re.compile(r'\bhe\s+or\s+she\b', re.IGNORECASE), 'he or she', 'they'),
]


def check_gender_neutral(content: str) -> dict:
    """성별 포용적 언어 사용을 검사합니다.

    Returns:
        findings, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'findings': [],
            'summary': {
                'total_issues': 0,
                'ko_issues': 0,
                'en_issues': 0,
                'level': 'none',
            },
            'score': 100.0,
            'suggestions': [],
        }

    cleaned = _HEADING_RE.sub('', content)
    findings = []

    # 한국어 검사
    ko_count = 0
    for pattern, label, alternative in _KO_GENDERED:
        matches = pattern.findall(cleaned)
        if matches:
            ko_count += len(matches)
            findings.append({
                'text': label,
                'alternative': alternative,
                'language': 'ko',
                'count': len(matches),
            })

    # 영어 검사
    en_count = 0
    for pattern, label, alternative in _EN_GENDERED:
        matches = pattern.findall(cleaned)
        if matches:
            en_count += len(matches)
            findings.append({
                'text': label,
                'alternative': alternative,
                'language': 'en',
                'count': len(matches),
            })

    total = ko_count + en_count

    # 레벨
    if total == 0:
        level = 'inclusive'
    elif total <= 2:
        level = 'minor'
    elif total <= 5:
        level = 'moderate'
    else:
        level = 'significant'

    # 점수
    if total == 0:
        score = 100.0
    elif total <= 2:
        score = 85.0
    elif total <= 5:
        score = 70.0 - (total - 2) * 5.0
    else:
        score = max(20.0, 55.0 - (total - 5) * 5.0)

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(findings, total, level)

    return {
        'findings': findings[:20],
        'summary': {
            'total_issues': total,
            'ko_issues': ko_count,
            'en_issues': en_count,
            'level': level,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(findings: List[Dict], total: int,
                           level: str) -> List[str]:
    suggestions = []
    level_labels = {
        'inclusive': '포용적', 'minor': '경미',
        'moderate': '보통', 'significant': '주의 필요',
    }

    suggestions.append(
        f'성별 편향 표현 {total}개 ({level_labels.get(level, level)}).'
    )

    if findings:
        for f in findings[:3]:
            suggestions.append(
                f'"{f["text"]}" → "{f["alternative"]}"로 대체를 권장합니다.'
            )

    return suggestions
