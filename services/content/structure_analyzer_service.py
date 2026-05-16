"""
콘텐츠 구조 분석 서비스

마크다운 콘텐츠의 헤딩 트리, 섹션 균형도,
구조적 완성도를 규칙 기반으로 분석합니다.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_CODE_BLOCK = re.compile(r'```[\s\S]*?```')
_LIST_ITEM = re.compile(r'^\s*[-*•]\s+|^\s*\d+[.)]\s+', re.MULTILINE)
_IMAGE = re.compile(r'!\[.*?\]\(.*?\)')
_LINK = re.compile(r'\[.*?\]\(.*?\)')


def analyze_structure(content: str) -> dict:
    """마크다운 콘텐츠의 구조를 분석합니다.

    Returns:
        {
            'heading_tree': [{'level': int, 'text': str, 'word_count': int}],
            'section_balance': {'score': float, 'details': [...]},
            'completeness': {'score': float, 'has_intro': bool, 'has_conclusion': bool, ...},
            'element_counts': {'headings': int, 'paragraphs': int, ...},
            'issues': [str],
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()

    # 헤딩 트리 구축
    heading_tree = _build_heading_tree(text)

    # 섹션별 단어수 계산
    sections = _split_by_headings(text)
    section_balance = _calculate_balance(sections)

    # 구조 완성도
    completeness = _check_completeness(text, heading_tree, sections)

    # 요소 카운트
    element_counts = _count_elements(text)

    # 이슈 감지
    issues = _detect_issues(heading_tree, sections, element_counts)

    return {
        'heading_tree': heading_tree,
        'section_balance': section_balance,
        'completeness': completeness,
        'element_counts': element_counts,
        'issues': issues,
    }


def _build_heading_tree(text: str) -> List[dict]:
    """헤딩 트리를 구축합니다."""
    tree = []
    for match in _HEADING_PATTERN.finditer(text):
        level = len(match.group(1))
        heading_text = match.group(2).strip()
        word_count = len(re.findall(r'[\w가-힣]+', heading_text))
        tree.append({
            'level': level,
            'text': heading_text,
            'word_count': word_count,
        })
    return tree


def _split_by_headings(text: str) -> List[dict]:
    """헤딩 기준으로 섹션을 분리합니다."""
    lines = text.split('\n')
    sections = []
    current_heading = '(도입부)'
    current_level = 0
    current_body = []

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match:
            if current_body or current_heading != '(도입부)':
                body_text = '\n'.join(current_body).strip()
                sections.append({
                    'heading': current_heading,
                    'level': current_level,
                    'body': body_text,
                    'word_count': len(re.findall(r'[\w가-힣]+', body_text)),
                })
            current_heading = match.group(2).strip()
            current_level = len(match.group(1))
            current_body = []
        else:
            current_body.append(line)

    # 마지막 섹션
    body_text = '\n'.join(current_body).strip()
    if body_text or current_heading != '(도입부)':
        sections.append({
            'heading': current_heading,
            'level': current_level,
            'body': body_text,
            'word_count': len(re.findall(r'[\w가-힣]+', body_text)),
        })

    return sections


def _calculate_balance(sections: List[dict]) -> dict:
    """섹션 간 균형도를 계산합니다."""
    if len(sections) <= 1:
        return {'score': 1.0, 'details': [], 'avg_words': 0, 'std_dev': 0}

    word_counts = [s['word_count'] for s in sections if s['word_count'] > 0]
    if not word_counts:
        return {'score': 1.0, 'details': [], 'avg_words': 0, 'std_dev': 0}

    avg = sum(word_counts) / len(word_counts)
    variance = sum((w - avg) ** 2 for w in word_counts) / len(word_counts)
    std_dev = variance ** 0.5

    # 변동계수(CV) 기반 균형 점수
    cv = std_dev / avg if avg > 0 else 0
    score = round(max(0.0, 1.0 - cv), 2)

    details = []
    for s in sections:
        if s['word_count'] > 0:
            ratio = s['word_count'] / avg if avg > 0 else 0
            status = 'balanced'
            if ratio > 2.0:
                status = 'too_long'
            elif ratio < 0.3:
                status = 'too_short'
            details.append({
                'heading': s['heading'],
                'word_count': s['word_count'],
                'ratio': round(ratio, 2),
                'status': status,
            })

    return {
        'score': score,
        'details': details,
        'avg_words': round(avg, 1),
        'std_dev': round(std_dev, 1),
    }


def _check_completeness(text: str, heading_tree: list,
                        sections: list) -> dict:
    """구조적 완성도를 확인합니다."""
    lower_text = text.lower()

    # 도입부 확인 (첫 섹션이 헤딩 없이 시작하거나 서론/소개 키워드)
    has_intro = False
    if sections and sections[0]['heading'] == '(도입부)' and sections[0]['word_count'] > 10:
        has_intro = True
    intro_keywords = ['서론', '소개', '개요', '들어가며', 'introduction', 'overview']
    if any(kw in lower_text for kw in intro_keywords):
        has_intro = True

    # 결론 확인
    conclusion_keywords = ['결론', '마무리', '정리', '요약하면', 'conclusion', 'summary']
    has_conclusion = any(kw in lower_text for kw in conclusion_keywords)

    # 헤딩 계층 확인
    has_hierarchy = len(set(h['level'] for h in heading_tree)) > 1 if heading_tree else False

    # 점수 계산
    score = 0.0
    if has_intro:
        score += 0.25
    if has_conclusion:
        score += 0.25
    if heading_tree:
        score += 0.25
    if has_hierarchy:
        score += 0.25

    return {
        'score': round(score, 2),
        'has_intro': has_intro,
        'has_conclusion': has_conclusion,
        'has_headings': bool(heading_tree),
        'has_hierarchy': has_hierarchy,
        'heading_count': len(heading_tree),
    }


def _count_elements(text: str) -> dict:
    """콘텐츠 요소 수를 카운트합니다."""
    # 코드블록 제거 후 분석
    no_code = _CODE_BLOCK.sub('', text)
    paragraphs = [p for p in no_code.split('\n\n') if p.strip() and not _HEADING_PATTERN.match(p.strip())]

    return {
        'headings': len(_HEADING_PATTERN.findall(text)),
        'paragraphs': len(paragraphs),
        'list_items': len(_LIST_ITEM.findall(text)),
        'code_blocks': len(_CODE_BLOCK.findall(text)),
        'images': len(_IMAGE.findall(text)),
        'links': len(_LINK.findall(text)),
        'total_words': len(re.findall(r'[\w가-힣]+', text)),
    }


def _detect_issues(heading_tree: list, sections: list,
                   elements: dict) -> List[str]:
    """구조적 이슈를 감지합니다."""
    issues = []

    # 헤딩 레벨 건너뛰기 (h1 → h3)
    for i in range(1, len(heading_tree)):
        prev_level = heading_tree[i - 1]['level']
        curr_level = heading_tree[i]['level']
        if curr_level > prev_level + 1:
            issues.append(
                f'헤딩 레벨 건너뛰기: H{prev_level} → H{curr_level} '
                f'("{heading_tree[i]["text"]}")'
            )

    # 빈 섹션
    for section in sections:
        if section['heading'] != '(도입부)' and section['word_count'] == 0:
            issues.append(f'빈 섹션: "{section["heading"]}"')

    # 헤딩 없는 긴 글
    if elements['headings'] == 0 and elements['total_words'] > 200:
        issues.append('200단어 이상인데 헤딩이 없습니다. 구조화를 권장합니다.')

    # 너무 많은 연속 리스트
    if elements['list_items'] > 20 and elements['paragraphs'] < 3:
        issues.append('리스트가 지나치게 많습니다. 설명 문단을 추가하세요.')

    return issues


def _empty_result() -> dict:
    return {
        'heading_tree': [],
        'section_balance': {'score': 1.0, 'details': [], 'avg_words': 0, 'std_dev': 0},
        'completeness': {
            'score': 0.0, 'has_intro': False, 'has_conclusion': False,
            'has_headings': False, 'has_hierarchy': False, 'heading_count': 0,
        },
        'element_counts': {
            'headings': 0, 'paragraphs': 0, 'list_items': 0,
            'code_blocks': 0, 'images': 0, 'links': 0, 'total_words': 0,
        },
        'issues': [],
    }
