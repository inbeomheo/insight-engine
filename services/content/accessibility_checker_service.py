"""
콘텐츠 접근성 검사 서비스

마크다운 콘텐츠의 접근성 문제를 규칙 기반으로 검사합니다.
이미지 alt 텍스트, 헤딩 구조, 링크 텍스트, 색상 의존성 등.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_LINK_PATTERN = re.compile(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)')
_TABLE_PATTERN = re.compile(r'^\|.+\|', re.MULTILINE)
_COLOR_ONLY = re.compile(r'(빨간|파란|초록|노란|색상으로|색으로)\s*(표시|구분|강조)', re.IGNORECASE)
_GENERIC_LINK_TEXT = frozenset(['여기', '클릭', '이곳', '링크', 'here', 'click', 'link', 'this'])


def check_accessibility(content: str) -> dict:
    """콘텐츠의 접근성을 검사합니다.

    Returns:
        {
            'score': float (0.0~1.0),
            'level': str (A/AA/AAA),
            'issues': [{'rule': str, 'severity': str, 'message': str, 'suggestion': str}],
            'passed': [{'rule': str, 'message': str}],
            'total_checks': int,
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()
    issues: List[dict] = []
    passed: List[dict] = []

    # 1) 이미지 alt 텍스트
    _check_image_alt(text, issues, passed)

    # 2) 헤딩 구조
    _check_heading_structure(text, issues, passed)

    # 3) 링크 텍스트 품질
    _check_link_text(text, issues, passed)

    # 4) 테이블 접근성
    _check_tables(text, issues, passed)

    # 5) 색상 의존성
    _check_color_dependency(text, issues, passed)

    # 6) 콘텐츠 길이/구조
    _check_content_structure(text, issues, passed)

    total = len(issues) + len(passed)
    passed_count = len(passed)
    score = round(passed_count / total, 2) if total > 0 else 1.0

    if score >= 0.9:
        level = 'AAA'
    elif score >= 0.7:
        level = 'AA'
    else:
        level = 'A'

    return {
        'score': score,
        'level': level,
        'issues': issues,
        'passed': passed,
        'total_checks': total,
    }


def _check_image_alt(text: str, issues: list, passed: list):
    """이미지 alt 텍스트 검사."""
    images = _IMAGE_PATTERN.findall(text)
    if not images:
        passed.append({'rule': 'img_alt', 'message': '이미지 없음 (검사 불필요)'})
        return

    missing_alt = [url for alt, url in images if not alt.strip()]
    short_alt = [alt for alt, _ in images if alt.strip() and len(alt.strip()) < 3]

    if missing_alt:
        issues.append({
            'rule': 'img_alt_missing',
            'severity': 'error',
            'message': f'{len(missing_alt)}개 이미지에 alt 텍스트가 없습니다',
            'suggestion': '모든 이미지에 설명적인 alt 텍스트를 추가하세요',
        })
    elif short_alt:
        issues.append({
            'rule': 'img_alt_short',
            'severity': 'warning',
            'message': f'{len(short_alt)}개 이미지의 alt 텍스트가 너무 짧습니다',
            'suggestion': 'alt 텍스트를 3자 이상으로 작성하세요',
        })
    else:
        passed.append({'rule': 'img_alt', 'message': f'{len(images)}개 이미지 모두 적절한 alt 텍스트 포함'})


def _check_heading_structure(text: str, issues: list, passed: list):
    """헤딩 구조 검사."""
    headings = _HEADING_PATTERN.findall(text)
    if not headings:
        if len(text) > 500:
            issues.append({
                'rule': 'heading_missing',
                'severity': 'warning',
                'message': '긴 콘텐츠에 헤딩이 없습니다',
                'suggestion': '스크린 리더 사용자를 위해 헤딩으로 구조를 만드세요',
            })
        return

    levels = [len(h[0]) for h in headings]

    # 레벨 건너뛰기 확인
    for i in range(1, len(levels)):
        if levels[i] > levels[i - 1] + 1:
            issues.append({
                'rule': 'heading_skip',
                'severity': 'error',
                'message': f'헤딩 레벨 건너뛰기: H{levels[i-1]} → H{levels[i]}',
                'suggestion': '헤딩 레벨을 순서대로 사용하세요 (H1→H2→H3)',
            })
            return

    passed.append({'rule': 'heading_structure', 'message': '헤딩 구조가 올바릅니다'})


def _check_link_text(text: str, issues: list, passed: list):
    """링크 텍스트 품질 검사."""
    links = _LINK_PATTERN.findall(text)
    if not links:
        return

    generic_links = [lt for lt, _ in links if lt.strip().lower() in _GENERIC_LINK_TEXT]
    if generic_links:
        issues.append({
            'rule': 'link_text_generic',
            'severity': 'warning',
            'message': f'{len(generic_links)}개 링크에 비설명적 텍스트 사용 ({", ".join(generic_links[:3])})',
            'suggestion': '"여기 클릭" 대신 링크 목적을 설명하는 텍스트를 사용하세요',
        })
    else:
        passed.append({'rule': 'link_text', 'message': '모든 링크에 설명적 텍스트 사용'})


def _check_tables(text: str, issues: list, passed: list):
    """테이블 접근성 검사."""
    tables = _TABLE_PATTERN.findall(text)
    if not tables:
        return
    # 마크다운 테이블은 기본적으로 헤더 행이 있음 → OK
    passed.append({'rule': 'table_structure', 'message': f'{len(tables)}줄 테이블 구조 확인'})


def _check_color_dependency(text: str, issues: list, passed: list):
    """색상만으로 정보를 전달하는지 검사."""
    if _COLOR_ONLY.search(text):
        issues.append({
            'rule': 'color_dependency',
            'severity': 'warning',
            'message': '색상에 의존한 정보 전달이 감지되었습니다',
            'suggestion': '색상 외에 텍스트, 아이콘 등 추가 표시를 사용하세요',
        })
    else:
        passed.append({'rule': 'color_dependency', 'message': '색상 의존성 없음'})


def _check_content_structure(text: str, issues: list, passed: list):
    """콘텐츠 구조 접근성 검사."""
    paragraphs = [p for p in text.split('\n\n') if p.strip()]
    long_paras = [p for p in paragraphs if len(p) > 500]

    if long_paras:
        issues.append({
            'rule': 'paragraph_length',
            'severity': 'info',
            'message': f'{len(long_paras)}개 문단이 500자를 초과합니다',
            'suggestion': '긴 문단을 나누면 읽기 쉬워집니다',
        })
    else:
        passed.append({'rule': 'paragraph_length', 'message': '문단 길이 적절'})


def _empty_result() -> dict:
    return {
        'score': 0.0,
        'level': 'A',
        'issues': [{'rule': 'empty_content', 'severity': 'error',
                     'message': '콘텐츠가 비어 있습니다', 'suggestion': '콘텐츠를 작성하세요'}],
        'passed': [],
        'total_checks': 1,
    }
