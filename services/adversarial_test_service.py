"""
적대적 페르소나 테스트 서비스

콘텐츠를 다양한 비판적 페르소나(회의론자, 규제자, 경쟁사, 초보자) 관점에서
규칙 기반으로 검증하여 잠재적 문제를 사전에 발견합니다.
순수 파이썬, AI API 호출 없음.
"""
import re
from dataclasses import dataclass, field
from typing import List, Optional, Callable


@dataclass
class StressResult:
    """적대적 테스트 결과."""
    persona: str
    test_name: str
    passed: bool
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


# ── 기본 페르소나 목록 ──
_DEFAULT_PERSONAS = ['skeptic', 'regulator', 'competitor', 'beginner']


# ── Skeptic (회의론자): 근거 없는 주장 탐지 ──

_UNSUBSTANTIATED_CLAIMS = [
    re.compile(r'(?:최고의|최상의|최강의|최대의|세계\s*최초)', re.IGNORECASE),
    re.compile(r'(?:혁신적|혁명적|획기적|게임체인저|압도적|경이로운)', re.IGNORECASE),
    re.compile(r'(?:놀라운|탁월한|인상적|뛰어난|강력한)', re.IGNORECASE),
    re.compile(r'(?:유일한|독보적|비교\s*불가|대체\s*불가)', re.IGNORECASE),
    re.compile(r'\b(?:best|greatest|revolutionary|game[- ]?changer|unmatched)\b', re.IGNORECASE),
]

# 근거 제시 패턴 (숫자, 출처, 연구)
_EVIDENCE_PATTERNS = [
    re.compile(r'\d+%'),
    re.compile(r'(?:연구|조사|통계|보고서|논문|데이터|출처|참고)'),
    re.compile(r'(?:according\s+to|research|study|survey|data|source)', re.IGNORECASE),
    re.compile(r'\(\d{4}\)'),  # 연도 인용
]


def _test_skeptic(content: str) -> StressResult:
    """회의론자 관점: 근거 없는 주장 검증."""
    issues = []
    suggestions = []

    # 근거 없는 주장 탐지
    claims_found = []
    for pat in _UNSUBSTANTIATED_CLAIMS:
        for m in pat.finditer(content):
            claims_found.append(m.group())

    # 근거 존재 여부
    has_evidence = any(pat.search(content) for pat in _EVIDENCE_PATTERNS)

    if claims_found:
        unique_claims = list(dict.fromkeys(claims_found))[:5]
        issues.append(f'근거 없는 주장 표현 {len(claims_found)}개 발견: {", ".join(unique_claims)}')
        if not has_evidence:
            issues.append('수치, 출처, 연구 등 근거 자료가 전혀 없습니다.')
            suggestions.append('주장에 대한 구체적 데이터나 출처를 추가하세요.')
        else:
            suggestions.append('일부 근거가 있으나, 모든 주장에 대해 출처를 명시하세요.')

    passed = len(issues) == 0
    if passed:
        suggestions.append('근거 없는 과장 표현이 발견되지 않았습니다.')

    return StressResult(
        persona='skeptic',
        test_name='근거 없는 주장 검증',
        passed=passed,
        issues=issues,
        suggestions=suggestions,
    )


# ── Regulator (규제자): 규정 준수 검증 ──

_REQUIRED_DISCLAIMERS = [
    re.compile(r'(?:개인\s*정보|privacy\s*policy)', re.IGNORECASE),
    re.compile(r'(?:이용\s*약관|terms\s*(?:of\s*(?:use|service)))', re.IGNORECASE),
]

_MISLEADING_PATTERNS = [
    re.compile(r'(?:100%\s*(?:안전|보장|확실|성공))', re.IGNORECASE),
    re.compile(r'(?:부작용\s*(?:없|전혀|zero))', re.IGNORECASE),
    re.compile(r'(?:위험\s*(?:없|zero|전무))', re.IGNORECASE),
    re.compile(r'\b(?:guaranteed\s+results?|no\s+risk|zero\s+risk)\b', re.IGNORECASE),
]

_REGULATORY_KEYWORDS = [
    re.compile(r'(?:의약품|건강기능식품|의료|치료|진단)', re.IGNORECASE),
    re.compile(r'(?:금융|투자|수익률|원금)', re.IGNORECASE),
    re.compile(r'(?:supplement|medical|financial|investment)', re.IGNORECASE),
]


def _test_regulator(content: str) -> StressResult:
    """규제자 관점: 규정 준수 검증."""
    issues = []
    suggestions = []

    # 오해 유발 표현
    misleading = []
    for pat in _MISLEADING_PATTERNS:
        for m in pat.finditer(content):
            misleading.append(m.group())

    if misleading:
        unique = list(dict.fromkeys(misleading))[:5]
        issues.append(f'오해 유발 표현 발견: {", ".join(unique)}')
        suggestions.append('절대적 보증/안전 표현을 완화하거나 단서를 추가하세요.')

    # 규제 민감 분야 언급 시 면책 문구 확인
    has_regulated = any(pat.search(content) for pat in _REGULATORY_KEYWORDS)
    has_disclaimer = any(pat.search(content) for pat in _REQUIRED_DISCLAIMERS)

    if has_regulated and not has_disclaimer:
        issues.append('규제 민감 분야(의료, 금융 등)를 다루면서 면책 문구가 없습니다.')
        suggestions.append('관련 법적 고지(이용약관, 면책조항)를 추가하세요.')

    passed = len(issues) == 0
    if passed:
        suggestions.append('규정 준수 관점에서 문제가 발견되지 않았습니다.')

    return StressResult(
        persona='regulator',
        test_name='규정 준수 검증',
        passed=passed,
        issues=issues,
        suggestions=suggestions,
    )


# ── Competitor (경쟁사): 경쟁사 비방 패턴 탐지 ──

_COMPETITOR_DISPARAGEMENT = [
    re.compile(r'(?:경쟁\s*(?:사|업체|제품).*?(?:열등|뒤떨어|못한|부족|느린|불안정))', re.IGNORECASE),
    re.compile(r'(?:(?:타사|다른\s*(?:회사|제품|서비스)).*?(?:문제|결함|버그|오류|취약))', re.IGNORECASE),
    re.compile(r'\b(?:competitor.*?(?:inferior|lacking|poor|slow|buggy))\b', re.IGNORECASE),
    re.compile(r'\b(?:unlike\s+(?:other|competing).*?(?:fail|lack|poor))\b', re.IGNORECASE),
]

_COMPARATIVE_CLAIMS = [
    re.compile(r'(?:보다\s*(?:우수|뛰어남|빠름|안정))', re.IGNORECASE),
    re.compile(r'(?:대비\s*\d+\s*(?:%|배|배\s*이상))', re.IGNORECASE),
    re.compile(r'\b(?:\d+x?\s*(?:faster|better|more\s+(?:efficient|reliable)))\b', re.IGNORECASE),
]


def _test_competitor(content: str) -> StressResult:
    """경쟁사 관점: 비방/불공정 비교 탐지."""
    issues = []
    suggestions = []

    # 직접적 비방
    disparagement = []
    for pat in _COMPETITOR_DISPARAGEMENT:
        for m in pat.finditer(content):
            disparagement.append(m.group())

    if disparagement:
        unique = list(dict.fromkeys(disparagement))[:5]
        issues.append(f'경쟁사 비방 표현 발견: {", ".join(unique)}')
        suggestions.append('경쟁사를 직접 비방하는 표현을 제거하고, 자사 장점을 중심으로 서술하세요.')

    # 근거 없는 비교 주장
    comparisons = []
    for pat in _COMPARATIVE_CLAIMS:
        for m in pat.finditer(content):
            comparisons.append(m.group())

    has_evidence = any(pat.search(content) for pat in _EVIDENCE_PATTERNS)

    if comparisons and not has_evidence:
        unique = list(dict.fromkeys(comparisons))[:3]
        issues.append(f'비교 주장에 근거 부족: {", ".join(unique)}')
        suggestions.append('비교 수치에 대한 출처나 테스트 결과를 명시하세요.')

    passed = len(issues) == 0
    if passed:
        suggestions.append('경쟁사 관련 불공정 표현이 발견되지 않았습니다.')

    return StressResult(
        persona='competitor',
        test_name='경쟁사 비방/불공정 비교 탐지',
        passed=passed,
        issues=issues,
        suggestions=suggestions,
    )


# ── Beginner (초보자): 전문용어 과다 체크 ──

_JARGON_PATTERNS = [
    re.compile(r'\b(?:API|SDK|REST|GraphQL|OAuth|JWT|CORS|CI/CD|DevOps)\b'),
    re.compile(r'\b(?:마이크로서비스|컨테이너화|오케스트레이션|디커플링|리팩토링)\b'),
    re.compile(r'\b(?:paradigm|scalability|abstraction|polymorphism|encapsulation)\b', re.IGNORECASE),
    re.compile(r'\b(?:블록체인|토큰화|스마트\s*컨트랙트|디파이|NFT)\b'),
    re.compile(r'\b(?:머신러닝|딥러닝|신경망|트랜스포머|파인튜닝|임베딩)\b'),
]

# 전문용어 설명 패턴 (괄호 안 설명, "~란" 등)
_EXPLANATION_PATTERNS = [
    re.compile(r'\([^)]{5,}\)'),  # 괄호 안 설명 (5자 이상)
    re.compile(r'(?:이란|란|라는\s*것은|의미하는)'),
    re.compile(r'(?:즉,?\s|다시\s*말해|쉽게\s*말하면)'),
]

_JARGON_THRESHOLD = 0.03  # 전문용어 비율 3% 초과 시 경고


def _test_beginner(content: str) -> StressResult:
    """초보자 관점: 전문용어 과다 체크."""
    issues = []
    suggestions = []

    # 전문용어 수집
    jargon_found = []
    for pat in _JARGON_PATTERNS:
        for m in pat.finditer(content):
            jargon_found.append(m.group())

    word_count = max(len(content.split()), 1)
    jargon_ratio = len(jargon_found) / word_count

    # 설명 존재 여부
    has_explanations = any(pat.search(content) for pat in _EXPLANATION_PATTERNS)

    if jargon_ratio > _JARGON_THRESHOLD:
        unique_jargon = list(dict.fromkeys(jargon_found))[:10]
        issues.append(
            f'전문용어 비율이 높습니다 ({len(jargon_found)}개, {jargon_ratio:.1%}): '
            f'{", ".join(unique_jargon)}'
        )
        if not has_explanations:
            issues.append('전문용어에 대한 설명이 부족합니다.')
            suggestions.append('전문용어 첫 등장 시 괄호 안에 간단한 설명을 추가하세요.')
        else:
            suggestions.append('일부 설명이 있으나, 모든 전문용어에 대해 설명을 확인하세요.')
    elif jargon_found and not has_explanations:
        issues.append(f'전문용어({len(jargon_found)}개)에 대한 설명이 없습니다.')
        suggestions.append('초보 독자를 위해 전문용어에 간단한 설명을 추가하세요.')

    passed = len(issues) == 0
    if passed:
        suggestions.append('초보자가 이해하기 적절한 수준의 용어 사용입니다.')

    return StressResult(
        persona='beginner',
        test_name='전문용어 과다 체크',
        passed=passed,
        issues=issues,
        suggestions=suggestions,
    )


# ── 페르소나 → 검사 함수 매핑 ──
_PERSONA_TESTS: dict[str, Callable[[str], StressResult]] = {
    'skeptic': _test_skeptic,
    'regulator': _test_regulator,
    'competitor': _test_competitor,
    'beginner': _test_beginner,
}


def get_available_personas() -> List[str]:
    """사용 가능한 페르소나 목록을 반환합니다."""
    return list(_PERSONA_TESTS.keys())


def stress_test(
    content: str,
    personas: Optional[List[str]] = None,
) -> List[StressResult]:
    """적대적 페르소나 관점에서 콘텐츠를 테스트합니다.

    Args:
        content: 검증할 콘텐츠 텍스트
        personas: 사용할 페르소나 목록 (None이면 전체)

    Returns:
        StressResult 목록
    """
    if not content or not content.strip():
        return []

    target_personas = personas if personas else _DEFAULT_PERSONAS
    results = []

    for persona in target_personas:
        tester = _PERSONA_TESTS.get(persona)
        if tester is None:
            continue
        results.append(tester(content))

    return results
