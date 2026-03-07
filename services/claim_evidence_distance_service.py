"""
Claim-Evidence Distance Analyzer 서비스

주장 문장과 근거(출처, 수치, 예시)가 너무
멀리 떨어진 구간을 찾아 신뢰 저하 지점을 표시합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 주장 패턴
_CLAIM_PATTERNS = [
    re.compile(r'(?:이다|입니다|됩니다|합니다)[\s.]*$'),
    re.compile(r'(?:중요하|필수적|핵심적|효과적|유용하|필요하)', re.IGNORECASE),
    re.compile(r'(?:해야|해서는|하면\s*안)', re.IGNORECASE),
    re.compile(r'(?:최선|최적|가장\s*좋|추천)', re.IGNORECASE),
    re.compile(r'\b(?:is\s+(?:important|essential|necessary|critical|better|best))\b', re.IGNORECASE),
    re.compile(r'\b(?:should|must|need\s+to|have\s+to)\b', re.IGNORECASE),
    re.compile(r'\b(?:proven|effective|superior|recommended)\b', re.IGNORECASE),
]

# 근거 패턴
_EVIDENCE_PATTERNS = [
    re.compile(r'(?:연구|논문|보고서|조사|통계)(?:에\s*따르면|에서|에\s*의하면)', re.IGNORECASE),
    re.compile(r'(?:예를\s*들어|예시|사례|구체적으로)', re.IGNORECASE),
    re.compile(r'\d+\s*(?:%|퍼센트|percent)', re.IGNORECASE),
    re.compile(r'(?:출처|참고|인용|레퍼런스)', re.IGNORECASE),
    re.compile(r'https?://\S+', re.IGNORECASE),
    re.compile(r'\[\d+\]|\(\d{4}\)', re.IGNORECASE),  # 인용 마커
    re.compile(r'```[\s\S]*?```'),  # 코드 예시
    re.compile(r'\b(?:according\s+to|research\s+shows|study\s+(?:found|shows))\b', re.IGNORECASE),
    re.compile(r'\b(?:for\s+example|for\s+instance|such\s+as|e\.g\.)\b', re.IGNORECASE),
    re.compile(r'\b(?:data|evidence|source|reference)\b', re.IGNORECASE),
]

# 적정 거리 임계값 (문장 수)
_MAX_DISTANCE = 3  # 주장 후 3문장 이내에 근거가 있어야 함


def _is_claim(sentence: str) -> bool:
    """주장 문장인지 판별합니다."""
    return any(p.search(sentence) for p in _CLAIM_PATTERNS)


def _is_evidence(sentence: str) -> bool:
    """근거 문장인지 판별합니다."""
    return any(p.search(sentence) for p in _EVIDENCE_PATTERNS)


def analyze_claim_evidence_distance(content: str) -> dict:
    """주장-근거 거리를 분석합니다.

    Returns:
        score, summary, distant_claims, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 100.0,
            'summary': {
                'total_claims': 0,
                'supported_claims': 0,
                'distant_claims': 0,
                'unsupported_claims': 0,
                'level': 'none',
            },
            'distant_claims': [],
            'suggestions': [],
        }

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content)
                 if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        return {
            'score': 100.0,
            'summary': {
                'total_claims': 0,
                'supported_claims': 0,
                'distant_claims': 0,
                'unsupported_claims': 0,
                'level': 'none',
            },
            'distant_claims': [],
            'suggestions': [],
        }

    # 각 문장의 역할 분류
    roles = []
    for s in sentences:
        if _is_evidence(s):
            roles.append('evidence')
        elif _is_claim(s):
            roles.append('claim')
        else:
            roles.append('neutral')

    # 주장별 가장 가까운 근거 거리 계산
    claim_indices = [i for i, r in enumerate(roles) if r == 'claim']
    evidence_indices = [i for i, r in enumerate(roles) if r == 'evidence']

    supported = 0
    distant = 0
    unsupported = 0
    distant_items = []

    for ci in claim_indices:
        if not evidence_indices:
            unsupported += 1
            distant_items.append({
                'sentence': sentences[ci][:80],
                'position': ci,
                'nearest_evidence_distance': -1,
                'issue': '문서에 근거가 없음',
            })
            continue

        # 가장 가까운 근거까지의 거리
        min_dist = min(abs(ci - ei) for ei in evidence_indices)

        if min_dist <= _MAX_DISTANCE:
            supported += 1
        else:
            distant += 1
            distant_items.append({
                'sentence': sentences[ci][:80],
                'position': ci,
                'nearest_evidence_distance': min_dist,
                'issue': f'가장 가까운 근거가 {min_dist}문장 떨어짐',
            })

    total_claims = len(claim_indices)

    # 레벨 판정
    if total_claims == 0:
        level = 'none'
    elif distant + unsupported == 0:
        level = 'well_supported'
    elif (distant + unsupported) / total_claims <= 0.2:
        level = 'mostly_supported'
    elif (distant + unsupported) / total_claims <= 0.5:
        level = 'mixed'
    else:
        level = 'weakly_supported'

    # 점수 계산
    if level in ('none', 'well_supported'):
        score = 100.0
    elif level == 'mostly_supported':
        score = 80.0
    elif level == 'mixed':
        score = 55.0
    else:
        score = 30.0

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        total_claims, supported, distant, unsupported, level, distant_items
    )

    return {
        'score': score,
        'summary': {
            'total_claims': total_claims,
            'supported_claims': supported,
            'distant_claims': distant,
            'unsupported_claims': unsupported,
            'level': level,
        },
        'distant_claims': distant_items[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, supported: int, distant: int,
                           unsupported: int, level: str,
                           items: List[Dict]) -> List[str]:
    suggestions = []

    level_labels = {
        'none': '해당 없음', 'well_supported': '잘 뒷받침됨',
        'mostly_supported': '대부분 뒷받침', 'mixed': '혼재',
        'weakly_supported': '약한 뒷받침',
    }
    suggestions.append(
        f'주장-근거 거리: {level_labels.get(level, level)}. '
        f'주장 {total}건 중 지원 {supported}건, 먼 거리 {distant}건, '
        f'미지원 {unsupported}건.'
    )

    if distant > 0:
        suggestions.append(
            '주장 문장 직후(3문장 이내)에 근거(데이터, 출처, 예시)를 배치하세요.'
        )

    if unsupported > 0:
        suggestions.append(
            '근거 없는 주장이 있습니다. 출처나 데이터를 추가하세요.'
        )

    for item in items[:2]:
        suggestions.append(
            f'먼 주장: "{item["sentence"][:40]}..." — {item["issue"]}.'
        )

    return suggestions
