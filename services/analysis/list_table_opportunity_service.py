"""
List/Table Opportunity Detector 서비스

긴 설명 덩어리를 목록이나 표로 바꿔야 할 후보 구간을 찾아
모바일 스캔성과 정보 흡수 속도를 개선합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


# ── 나열형 패턴 (목록 변환 후보) ──
_ENUMERATION_PATTERNS = [
    # "A, B, C, D" (쉼표로 4개 이상 나열)
    re.compile(r'(?:[^,]{2,20},\s*){3,}[^,]{2,20}'),
    # "A와/과 B, C, D"
    re.compile(r'[가-힣A-Za-z]+(?:와|과)\s+[가-힣A-Za-z]+(?:,\s*[가-힣A-Za-z]+){2,}'),
    # "첫째... 둘째... 셋째..."
    re.compile(r'첫째.*둘째.*셋째', re.DOTALL),
    # "First... Second... Third..."
    re.compile(r'First\b.*Second\b.*Third\b', re.DOTALL | re.IGNORECASE),
    # "1) ... 2) ... 3) ..." 인라인
    re.compile(r'1\).*2\).*3\)'),
]

# ── 비교형 패턴 (표 변환 후보) ──
_COMPARISON_PATTERNS = [
    # "A는 ~이고, B는 ~이다"
    re.compile(r'[가-힣A-Za-z]+(?:은|는)\s+.{3,30}(?:이고|이며|인\s*반면)'),
    # "A vs B" 또는 "A 대 B"
    re.compile(r'[가-힣A-Za-z]+\s+(?:vs\.?|대|versus)\s+[가-힣A-Za-z]+', re.IGNORECASE),
    # "~에 비해", "~와 비교하면"
    re.compile(r'(?:에\s*비해|와\s*비교하면|보다\s*(?:더|덜))'),
    # "compared to", "whereas"
    re.compile(r'\b(?:compared\s+to|whereas|while|on\s+the\s+other\s+hand)\b', re.IGNORECASE),
]

# ── 긴 문단 감지 ──
_LONG_PARAGRAPH_THRESHOLD = 200  # 200자 이상
_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)


def _parse_paragraphs(content: str) -> List[Dict]:
    """콘텐츠를 문단 단위로 파싱합니다."""
    # 헤딩 기반 섹션 분리
    lines = content.split('\n')
    paragraphs = []
    current_section = '(서론)'
    current_para = []

    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if m:
            if current_para:
                text = '\n'.join(current_para).strip()
                if text:
                    paragraphs.append({'section': current_section, 'text': text})
                current_para = []
            current_section = m.group(2).strip()
        elif line.strip() == '':
            if current_para:
                text = '\n'.join(current_para).strip()
                if text:
                    paragraphs.append({'section': current_section, 'text': text})
                current_para = []
        else:
            current_para.append(line)

    if current_para:
        text = '\n'.join(current_para).strip()
        if text:
            paragraphs.append({'section': current_section, 'text': text})

    return paragraphs


_EMPTY_RESULT = {
    'opportunities': [],
    'summary': {'total_opportunities': 0, 'list_candidates': 0,
                'table_candidates': 0, 'long_paragraphs': 0},
    'score': 100.0,
    'suggestions': [],
}


def _scan_paragraph_opportunities(paragraphs: List[Dict]) -> tuple:
    """문단별로 목록/표 변환 후보를 스캔합니다.

    Returns:
        (opportunities, list_candidates, table_candidates, long_paragraphs)
    """
    opportunities = []
    list_candidates = 0
    table_candidates = 0
    long_paragraphs = 0

    for para in paragraphs:
        text = para['text']
        opp_type = None
        reason = ''

        for pattern in _ENUMERATION_PATTERNS:
            if pattern.search(text):
                opp_type = 'list'
                reason = '나열형 구문 — 목록(ul/ol)으로 변환 권장'
                list_candidates += 1
                break

        if not opp_type:
            for pattern in _COMPARISON_PATTERNS:
                if pattern.search(text):
                    opp_type = 'table'
                    reason = '비교 구문 — 비교 표로 변환 권장'
                    table_candidates += 1
                    break

        if not opp_type and len(text) >= _LONG_PARAGRAPH_THRESHOLD:
            opp_type = 'list'
            reason = f'긴 문단({len(text)}자) — 핵심 포인트를 목록으로 분리 권장'
            long_paragraphs += 1
            list_candidates += 1

        if opp_type:
            opportunities.append({
                'section': para['section'], 'type': opp_type, 'reason': reason,
                'excerpt': text if len(text) <= 100 else text[:97] + '...',
            })

    return opportunities, list_candidates, table_candidates, long_paragraphs


def detect_list_table_opportunities(content: str) -> dict:
    """목록/표 변환 후보 구간을 감지합니다.

    Returns:
        opportunities, summary, score, suggestions를 포함하는 dict
    """
    try:
        if not content or not content.strip():
            return dict(_EMPTY_RESULT)

        paragraphs = _parse_paragraphs(content)
        if not paragraphs:
            return dict(_EMPTY_RESULT)

        opportunities, list_cands, table_cands, long_paras = _scan_paragraph_opportunities(paragraphs)

        total = len(opportunities)
        opp_ratio = (total / len(paragraphs)) if paragraphs else 0.0
        score = round(max(0.0, min(100.0, (1.0 - opp_ratio) * 100.0)), 1)

        return {
            'opportunities': opportunities,
            'summary': {'total_opportunities': total, 'list_candidates': list_cands,
                        'table_candidates': table_cands, 'long_paragraphs': long_paras},
            'score': score,
            'suggestions': _generate_suggestions(opportunities, list_cands, table_cands, long_paras),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _generate_suggestions(opps: List[Dict], lists: int, tables: int, longs: int) -> List[str]:
    suggestions = []
    if not opps:
        suggestions.append('목록/표 변환이 필요한 구간이 없습니다. 스캔성이 양호합니다.')
        return suggestions

    if lists > 0:
        suggestions.append(f'목록 변환 후보 {lists}개: 나열된 항목을 불릿 리스트로 정리하면 가독성이 높아집니다.')
    if tables > 0:
        suggestions.append(f'표 변환 후보 {tables}개: 비교 구문을 표로 정리하면 정보 비교가 쉬워집니다.')
    if longs > 0:
        suggestions.append(f'긴 문단 {longs}개: 핵심 포인트를 추출하여 목록으로 분리하세요.')
    return suggestions
