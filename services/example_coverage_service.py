"""
Example Coverage Analyzer 서비스

주장/조언/개념 설명 뒤에 예시, 사례, 수치, before/after가
부족한 구간을 탐지하여 콘텐츠 근거 보강 포인트를 제시합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 주장/조언 감지 패턴 (한국어)
_CLAIM_PATTERNS_KO = [
    r'해야\s*(한다|합니다)',
    r'하는\s*것이\s*좋(다|습니다)',
    r'(이|가)\s*중요(하다|합니다)',
    r'(이|가)\s*필수(다|입니다|적)',
    r'(이|가)\s*필요(하다|합니다)',
    r'(을|를)\s*권장(한다|합니다)',
    r'[가-힣]야\s*(한다|합니다)',  # ~아야/어야/라야 등 모든 어미
    r'바람직(하다|합니다)',
]

# 주장/조언 감지 패턴 (영어)
_CLAIM_PATTERNS_EN = [
    r'\bshould\b',
    r'\bmust\b',
    r'\bimportant\b',
    r'\brecommend(ed)?\b',
    r'\bessential\b',
    r'\bneed\s+to\b',
    r'\bcrucial\b',
]

# 근거/예시 감지 패턴 — (패턴, 근거 타입)
_EVIDENCE_PATTERNS = [
    # 예시 (example)
    (r'예를\s*들(어|면)', 'example'),
    (r'예시\s*:', 'example'),
    (r'예컨대', 'example'),
    (r'\bfor\s+example\b', 'example'),
    (r'\be\.?\s*g\.', 'example'),
    (r'가령', 'example'),
    (r'대표적으로', 'example'),

    # 사례 (case)
    (r'사례\s*:', 'case'),
    (r'\bcase\s+study\b', 'case'),
    (r'실제로', 'case'),
    (r'실험\s*결과', 'case'),
    (r'연구\s*결과', 'case'),
    (r'조사\s*결과', 'case'),

    # 수치 (number) — 숫자 + 단위
    (r'\d+(\.\d+)?\s*(%|퍼센트|배|건|명|원|달러|개|시간|분|초|회)', 'number'),
    (r'\d+(\.\d+)?\s*(times|percent|users|cases|hours|days)', 'number'),

    # before/after
    (r'전\s*/\s*후', 'before_after'),
    (r'이전\s*/\s*이후', 'before_after'),
    (r'\bbefore\s*/?\s*after\b', 'before_after'),
    (r'개선\s*(전|후)', 'before_after'),
    (r'변경\s*(전|후)', 'before_after'),
    (r'적용\s*(전|후)', 'before_after'),

    # 인용 (quote)
    (r'에\s*따르면', 'quote'),
    (r'에\s*의하면', 'quote'),
    (r'\baccording\s+to\b', 'quote'),
]

# 컴파일된 주장 패턴
_COMPILED_CLAIM_KO = [re.compile(p, re.IGNORECASE) for p in _CLAIM_PATTERNS_KO]
_COMPILED_CLAIM_EN = [re.compile(p, re.IGNORECASE) for p in _CLAIM_PATTERNS_EN]

# 컴파일된 근거 패턴
_COMPILED_EVIDENCE = [(re.compile(p, re.IGNORECASE), etype) for p, etype in _EVIDENCE_PATTERNS]


def analyze_example_coverage(content: str) -> dict:
    """콘텐츠의 주장/조언에 대한 예시·근거 커버리지를 분석합니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        {
            "claims": [{"claim_sentence": str, "has_evidence": bool,
                         "evidence_type": str|None, "status": str}],
            "summary": {"total_claims": int, "supported": int, "unsupported": int},
            "coverage_score": float,  # 0-100
            "weak_sections": list[str],
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'claims': [],
            'summary': {'total_claims': 0, 'supported': 0, 'unsupported': 0},
            'coverage_score': 0.0,
            'weak_sections': [],
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 문장 분리
    sentences = _split_sentences(content)

    if not sentences:
        return {
            'claims': [],
            'summary': {'total_claims': 0, 'supported': 0, 'unsupported': 0},
            'coverage_score': 0.0,
            'weak_sections': [],
            'suggestions': ['분석할 문장이 없습니다.'],
        }

    # 주장 문장 탐지
    claim_indices = _detect_claims(sentences)

    if not claim_indices:
        return {
            'claims': [],
            'summary': {'total_claims': 0, 'supported': 0, 'unsupported': 0},
            'coverage_score': 100.0,
            'weak_sections': [],
            'suggestions': ['주장/조언 문장이 없습니다. 근거 분석이 불필요합니다.'],
        }

    # 각 주장에 대한 근거 확인
    claims = []
    for idx in claim_indices:
        evidence = _find_evidence(sentences, idx)
        claims.append({
            'claim_sentence': sentences[idx],
            'has_evidence': evidence is not None,
            'evidence_type': evidence,
            'status': 'supported' if evidence else 'unsupported',
        })

    # 요약 통계
    supported = sum(1 for c in claims if c['has_evidence'])
    unsupported = len(claims) - supported
    total = len(claims)

    # 커버리지 점수 (0-100)
    coverage_score = round((supported / total) * 100, 1) if total > 0 else 0.0

    # 약한 구간 (근거 없는 주장 문장)
    weak_sections = [c['claim_sentence'] for c in claims if not c['has_evidence']]

    # 개선 제안
    suggestions = _generate_suggestions(claims, coverage_score)

    return {
        'claims': claims,
        'summary': {'total_claims': total, 'supported': supported, 'unsupported': unsupported},
        'coverage_score': coverage_score,
        'weak_sections': weak_sections,
        'suggestions': suggestions,
    }


def _split_sentences(content: str) -> list:
    """콘텐츠를 문장 단위로 분리합니다."""
    # 마침표/느낌표/물음표/줄바꿈 기준 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    # 빈 문자열 및 너무 짧은 문장 제거
    return [s.strip() for s in raw if len(s.strip()) >= 5]


def _detect_claims(sentences: list) -> list:
    """주장/조언 문장의 인덱스를 반환합니다."""
    claim_indices = []
    for i, sentence in enumerate(sentences):
        if _is_claim(sentence):
            claim_indices.append(i)
    return claim_indices


def _is_claim(sentence: str) -> bool:
    """문장이 주장/조언인지 판별합니다."""
    for pattern in _COMPILED_CLAIM_KO:
        if pattern.search(sentence):
            return True
    for pattern in _COMPILED_CLAIM_EN:
        if pattern.search(sentence):
            return True
    return False


def _find_evidence(sentences: list, claim_idx: int) -> str:
    """주장 뒤 3문장 이내에서 근거를 찾습니다. 발견 시 근거 타입을 반환합니다."""
    # 주장 뒤 1~3문장 범위 탐색
    start = claim_idx + 1
    end = min(claim_idx + 4, len(sentences))  # 최대 3문장 뒤까지

    for i in range(start, end):
        evidence_type = _detect_evidence_type(sentences[i])
        if evidence_type:
            return evidence_type

    # 주장 문장 자체에도 근거가 포함될 수 있음
    evidence_type = _detect_evidence_type(sentences[claim_idx])
    if evidence_type:
        return evidence_type

    return None


def _detect_evidence_type(sentence: str) -> str:
    """문장에서 근거 패턴을 감지하여 타입을 반환합니다."""
    for pattern, etype in _COMPILED_EVIDENCE:
        if pattern.search(sentence):
            return etype
    return None


def _generate_suggestions(claims: list, coverage_score: float) -> list:
    """분석 결과에 기반한 개선 제안을 생성합니다."""
    suggestions = []

    unsupported = [c for c in claims if not c['has_evidence']]

    if coverage_score >= 80:
        suggestions.append('근거 커버리지가 우수합니다. 기존 예시의 구체성을 더 높이면 좋습니다.')
    elif coverage_score >= 50:
        suggestions.append(f'근거가 부족한 주장이 {len(unsupported)}개 있습니다. 구체적 예시나 수치를 추가하세요.')
    else:
        suggestions.append(f'대부분의 주장({len(unsupported)}개)에 근거가 없습니다. 예시, 사례, 수치 데이터를 보강하세요.')

    # 근거 타입별 분포 확인
    evidence_types = [c['evidence_type'] for c in claims if c['evidence_type']]
    if evidence_types and 'number' not in evidence_types:
        suggestions.append('수치 데이터가 없습니다. 통계나 숫자를 추가하면 설득력이 높아집니다.')

    if evidence_types and 'case' not in evidence_types:
        suggestions.append('구체적 사례가 없습니다. 실제 사례나 실험 결과를 추가하면 신뢰도가 높아집니다.')

    if not evidence_types:
        suggestions.append('어떤 형태의 근거도 발견되지 않았습니다. 예시, 수치, 사례, 인용을 추가하세요.')

    return suggestions
