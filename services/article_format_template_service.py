"""
Article Format Template Checker 서비스

콘텐츠가 일반적인 글 형식 템플릿(리스트형, 하우투, 비교, Q&A 등)에
얼마나 부합하는지 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

# 포맷 감지 패턴
_FORMAT_PATTERNS = {
    'listicle': {
        'signals': [
            re.compile(r'(?:\d+가지|Top\s*\d+|\d+개|N가지|\d+\s*Things)', re.IGNORECASE),
            re.compile(r'^(?:\d+[.)]\s|[-*]\s)', re.MULTILINE),
        ],
        'label': '리스트형',
        'description': '숫자 기반 목록 형식 (N가지 방법, Top 10 등)',
    },
    'how_to': {
        'signals': [
            re.compile(r'(?:방법|하는\s*법|따라하기|가이드|튜토리얼)', re.IGNORECASE),
            re.compile(r'\b(?:How\s+to|Step\s+\d|Guide|Tutorial)\b', re.IGNORECASE),
            re.compile(r'(?:단계|스텝|Step)\s*\d'),
        ],
        'label': '하우투/가이드',
        'description': '단계별 설명 형식',
    },
    'comparison': {
        'signals': [
            re.compile(r'(?:비교|대결|vs\.?|versus|차이점|장단점)', re.IGNORECASE),
            re.compile(r'\b(?:Comparison|Pros\s+and\s+Cons|Advantages)\b', re.IGNORECASE),
        ],
        'label': '비교/분석',
        'description': '두 가지 이상 항목 비교 형식',
    },
    'qna': {
        'signals': [
            re.compile(r'(?:자주\s*묻는|FAQ|Q&A|질문과\s*답)', re.IGNORECASE),
            re.compile(r'^(?:Q\d*[.:]\s|A\d*[.:]\s)', re.MULTILINE),
            re.compile(r'\?$', re.MULTILINE),
        ],
        'label': 'Q&A/FAQ',
        'description': '질문-답변 형식',
    },
    'review': {
        'signals': [
            re.compile(r'(?:리뷰|후기|사용기|체험기|평가)', re.IGNORECASE),
            re.compile(r'\b(?:Review|Rating|Score|Verdict)\b', re.IGNORECASE),
            re.compile(r'(?:별점|점수|평점|\d+/\d+점)'),
        ],
        'label': '리뷰/평가',
        'description': '제품/서비스 평가 형식',
    },
    'case_study': {
        'signals': [
            re.compile(r'(?:사례|케이스|실제|성공|실패|경험담)', re.IGNORECASE),
            re.compile(r'\b(?:Case\s+Study|Real[- ]World|Success\s+Story)\b', re.IGNORECASE),
        ],
        'label': '사례 연구',
        'description': '실제 사례 기반 분석 형식',
    },
}

# 구조 요소
_INTRO_SIGNALS = re.compile(r'(?:서론|소개|개요|배경|Introduction|Overview)', re.IGNORECASE)
_BODY_SIGNALS = re.compile(r'(?:본론|본문|내용|Main|Body)', re.IGNORECASE)
_CONCLUSION_SIGNALS = re.compile(r'(?:결론|마무리|정리|요약|Conclusion|Summary)', re.IGNORECASE)


def check_article_format(content: str) -> dict:
    """콘텐츠의 글 형식 템플릿 부합도를 분석합니다.

    Returns:
        detected_formats, structure_elements, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'detected_formats': [],
            'structure_elements': {},
            'summary': {'primary_format': 'none', 'format_count': 0,
                        'has_intro': False, 'has_body': True, 'has_conclusion': False},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 포맷 감지
    detected = []
    for fmt_id, fmt_info in _FORMAT_PATTERNS.items():
        match_count = 0
        for pattern in fmt_info['signals']:
            matches = pattern.findall(content)
            match_count += len(matches)

        if match_count >= 2:  # 최소 2개 신호
            detected.append({
                'format': fmt_id,
                'label': fmt_info['label'],
                'description': fmt_info['description'],
                'signal_count': match_count,
                'confidence': 'high' if match_count >= 4 else 'medium',
            })

    # 신호 수로 정렬
    detected.sort(key=lambda x: x['signal_count'], reverse=True)

    # 구조 요소 감지
    headings = [m.group(2).strip() for m in _HEADING_RE.finditer(content)]
    heading_text = ' '.join(headings)

    has_intro = bool(_INTRO_SIGNALS.search(heading_text)) or bool(_INTRO_SIGNALS.search(content[:200]))
    has_conclusion = bool(_CONCLUSION_SIGNALS.search(heading_text))
    has_body = len(headings) >= 2  # 헤딩 2개 이상이면 본문 구조 있음

    structure = {
        'has_intro': has_intro,
        'has_body': has_body,
        'has_conclusion': has_conclusion,
        'heading_count': len(headings),
    }

    primary = detected[0]['format'] if detected else 'unstructured'

    # 점수 계산
    score = _calculate_score(detected, structure)

    suggestions = _generate_suggestions(detected, structure, primary)

    return {
        'detected_formats': detected,
        'structure_elements': structure,
        'summary': {
            'primary_format': primary,
            'format_count': len(detected),
            'has_intro': has_intro,
            'has_body': has_body,
            'has_conclusion': has_conclusion,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _calculate_score(detected: List[Dict], structure: Dict) -> float:
    score = 40.0  # 기본

    # 포맷 감지 보너스
    if detected:
        top = detected[0]
        score += 20.0 if top['confidence'] == 'high' else 10.0

    # 구조 요소 보너스
    if structure['has_intro']:
        score += 10.0
    if structure['has_body']:
        score += 10.0
    if structure['has_conclusion']:
        score += 10.0

    # 헤딩 보너스
    hc = structure['heading_count']
    if 3 <= hc <= 15:
        score += 10.0
    elif hc > 0:
        score += 5.0

    return round(max(0.0, min(100.0, score)), 1)


def _generate_suggestions(detected: List[Dict], structure: Dict,
                           primary: str) -> List[str]:
    suggestions = []

    if detected:
        labels = [d['label'] for d in detected[:3]]
        suggestions.append(f'감지된 형식: {", ".join(labels)}.')
    else:
        suggestions.append('명확한 글 형식이 감지되지 않았습니다. 리스트형, 하우투, 비교 등 형식을 선택하면 구조가 강화됩니다.')

    if not structure['has_intro']:
        suggestions.append('서론/소개 섹션이 없습니다. 도입부를 추가하세요.')
    if not structure['has_conclusion']:
        suggestions.append('결론/마무리 섹션이 없습니다. 핵심 요약을 추가하세요.')
    if structure['heading_count'] < 3:
        suggestions.append(f'헤딩 {structure["heading_count"]}개로 부족합니다. 섹션을 나눠 구조를 강화하세요.')

    return suggestions
