"""인용 근거팩 서비스

콘텐츠에서 주장을 추출하고, 각 주장에 대한 검증 필요성과
근거 정보를 구조화하여 EvidencePack으로 반환한다.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class Claim:
    """개별 주장 항목"""
    text: str                          # 주장 원문
    claim_type: str                    # "statistic", "fact", "opinion", "recommendation"
    evidence_needed: bool              # 근거가 필요한지 여부
    evidence_url: str | None = None    # 근거 URL (있는 경우)
    confidence: float = 0.0            # 신뢰도 (0.0 ~ 1.0)


@dataclass
class EvidencePack:
    """인용 근거팩 종합 보고서"""
    content_id: str                    # 콘텐츠 식별자
    claims: list[Claim] = field(default_factory=list)          # 추출된 주장 목록
    bibliography: list[str] = field(default_factory=list)      # 참고문헌 목록
    coverage_score: float = 0.0        # 근거 커버리지 (0.0 ~ 1.0)


# 숫자/퍼센트 패턴 (통계 판별용)
_STAT_PATTERN = re.compile(
    r'(?:\d+(?:[.,]\d+)?)\s*(?:%|퍼센트|percent|배|倍|조|억|만|천)',
    re.IGNORECASE,
)

# 순수 숫자 포함 패턴 (단순 숫자도 통계로 간주)
_NUMBER_PATTERN = re.compile(
    r'\b\d{2,}\b',  # 2자리 이상 숫자
)

# 추천/권유 패턴
_RECOMMENDATION_PATTERN = re.compile(
    r'(?:해야\s*(?:한다|합니다|해요)|하는\s*것이\s*(?:좋다|좋습니다|바람직)|'
    r'권장|추천|필수|반드시|should|must|recommend|필요하다|필요합니다|'
    r'하세요|하십시오|것을\s*권합니다)',
    re.IGNORECASE,
)

# 의견 패턴
_OPINION_PATTERN = re.compile(
    r'(?:생각한다|생각합니다|것\s*같다|것\s*같습니다|느낌|인상|'
    r'아마도|perhaps|maybe|I\s*think|I\s*believe|in\s*my\s*opinion|'
    r'개인적으로|주관적|보인다|보입니다|듯하다|듯합니다)',
    re.IGNORECASE,
)

# 사실 진술 패턴 (단정적 서술)
_FACT_PATTERN = re.compile(
    r'(?:이다|입니다|였다|였습니다|되었다|되었습니다|알려져\s*있다|'
    r'밝혀졌다|확인되었다|is\b|are\b|was\b|were\b|has\s+been|'
    r'proven|confirmed|established|known)',
    re.IGNORECASE,
)

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?。])\s+|(?<=다\.)\s*|(?<=니다\.)\s*')


def _classify_claim(sentence: str) -> str:
    """문장의 주장 유형을 분류한다.

    분류 우선순위: statistic > recommendation > opinion > fact

    Args:
        sentence: 분석할 문장

    Returns:
        "statistic" | "recommendation" | "opinion" | "fact"
    """
    # 숫자/퍼센트 포함 → statistic
    if _STAT_PATTERN.search(sentence) or _NUMBER_PATTERN.search(sentence):
        return 'statistic'

    # ~해야 한다, 권장 등 → recommendation
    if _RECOMMENDATION_PATTERN.search(sentence):
        return 'recommendation'

    # 주관적 표현 → opinion
    if _OPINION_PATTERN.search(sentence):
        return 'opinion'

    # 기본값: 사실 진술
    return 'fact'


def _needs_evidence(claim_type: str) -> bool:
    """주장 유형에 따라 근거 필요 여부를 반환한다.

    Args:
        claim_type: 주장 유형

    Returns:
        statistic/fact은 True, opinion/recommendation은 False
    """
    return claim_type in ('statistic', 'fact')


def _calculate_confidence(claim_type: str, has_evidence: bool) -> float:
    """주장의 신뢰도를 계산한다.

    Args:
        claim_type: 주장 유형
        has_evidence: 근거 보유 여부

    Returns:
        0.0 ~ 1.0 신뢰도 점수
    """
    base_scores = {
        'statistic': 0.3,
        'fact': 0.4,
        'opinion': 0.7,       # 의견은 근거 불필요, 기본 신뢰도 높음
        'recommendation': 0.6,
    }
    score = base_scores.get(claim_type, 0.5)

    if has_evidence:
        score = min(1.0, score + 0.4)

    return round(score, 2)


def extract_claims(content: str) -> list[Claim]:
    """콘텐츠에서 주장을 추출한다.

    문장 단위로 분리하여 각 주장의 유형, 근거 필요성,
    신뢰도를 분석한다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        추출된 Claim 리스트

    Raises:
        ValueError: content가 None인 경우
    """
    if content is None:
        raise ValueError("content는 None일 수 없습니다")

    if not content.strip():
        return []

    # 문장 분리
    sentences = _SENTENCE_SPLIT.split(content.strip())
    claims = []

    for sentence in sentences:
        sentence = sentence.strip()
        # 너무 짧은 문장은 건너뜀 (5자 미만)
        if len(sentence) < 5:
            continue

        claim_type = _classify_claim(sentence)
        evidence_needed = _needs_evidence(claim_type)
        confidence = _calculate_confidence(claim_type, has_evidence=False)

        claims.append(Claim(
            text=sentence,
            claim_type=claim_type,
            evidence_needed=evidence_needed,
            evidence_url=None,
            confidence=confidence,
        ))

    return claims


def attach_evidence(content: str) -> EvidencePack:
    """콘텐츠에 인용 근거팩을 첨부한다.

    주장 추출 → 유형 분류 → 커버리지 계산으로 구성된
    근거팩을 반환한다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        EvidencePack 데이터클래스

    Raises:
        ValueError: content가 None인 경우
    """
    if content is None:
        raise ValueError("content는 None일 수 없습니다")

    content_id = str(uuid.uuid4())
    claims = extract_claims(content)

    # 참고문헌 목록: evidence_url이 있는 것만 수집
    bibliography = [
        c.evidence_url for c in claims
        if c.evidence_url is not None
    ]

    # 커버리지 계산: evidence_needed인 것 중 evidence가 있는 비율
    needs_evidence_claims = [c for c in claims if c.evidence_needed]
    if needs_evidence_claims:
        covered = sum(1 for c in needs_evidence_claims if c.evidence_url is not None)
        coverage_score = round(covered / len(needs_evidence_claims), 2)
    else:
        coverage_score = 1.0  # 근거가 필요한 주장이 없으면 100%

    return EvidencePack(
        content_id=content_id,
        claims=claims,
        bibliography=bibliography,
        coverage_score=coverage_score,
    )
