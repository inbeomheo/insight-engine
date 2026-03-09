"""멀티모달 증거 서비스

주장에 대한 다양한 모달리티의 증거를 수집하고 평가합니다.
증거 강도 분류, 번들링, 커버리지 분석, 모순 탐지 기능을 제공합니다.
"""
import uuid
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class Evidence:
    """증거 항목"""
    evidence_id: str                    # 증거 고유 ID
    claim: str                          # 관련 주장
    modality: str                       # text / image / audio / data
    content: str                        # 증거 내용
    strength: str = 'moderate'         # strong / moderate / weak
    source: str = ''                    # 출처


@dataclass
class EvidenceBundle:
    """증거 묶음"""
    claim: str                          # 주장
    evidences: list[Evidence] = field(default_factory=list)
    overall_strength: str = 'moderate'  # 전체 강도
    modality_coverage: list[str] = field(default_factory=list)  # 포함된 모달리티


# ── 증거 강도 분류 키워드 ────────────────────────────────────
_STRONG_KEYWORDS = [
    '데이터', '통계', '연구', '실험', '조사', '측정', '수치',
    '논문', '학술', '검증', '증명', '확인', '결과',
    'data', 'statistics', 'research', 'experiment', 'study',
    'evidence', 'proven', 'verified', 'confirmed', 'measured',
    '%', '퍼센트', '배', '증가', '감소',
]

_WEAK_KEYWORDS = [
    '의견', '생각', '추측', '아마', '가능성', '느낌', '인상',
    '일부', '누군가', '들었', '듣기에', '소문',
    'opinion', 'think', 'guess', 'maybe', 'perhaps',
    'possibly', 'someone', 'rumor', 'impression', 'feel',
]

_VALID_MODALITIES = {'text', 'image', 'audio', 'data'}
_VALID_STRENGTHS = {'strong', 'moderate', 'weak'}


def classify_strength(content: str, claim: str) -> str:
    """증거 강도 분류

    키워드 매칭 기반으로 증거의 강도를 분류합니다.

    Args:
        content: 증거 내용
        claim: 관련 주장

    Returns:
        'strong' | 'moderate' | 'weak'
    """
    if not content:
        return 'weak'

    text = (content + ' ' + claim).lower()

    strong_count = sum(1 for kw in _STRONG_KEYWORDS if kw in text)
    weak_count = sum(1 for kw in _WEAK_KEYWORDS if kw in text)

    if strong_count >= 2 or (strong_count >= 1 and weak_count == 0):
        return 'strong'
    elif weak_count >= 2 or (weak_count >= 1 and strong_count == 0):
        return 'weak'
    else:
        return 'moderate'


def bundle_evidence(
    claim: str,
    evidences: list[Evidence],
) -> EvidenceBundle:
    """증거 묶음 생성

    전체 강도는 증거들의 최빈 강도로 결정합니다.

    Args:
        claim: 주장
        evidences: 증거 목록

    Returns:
        EvidenceBundle
    """
    if not evidences:
        return EvidenceBundle(
            claim=claim,
            evidences=[],
            overall_strength='weak',
            modality_coverage=[],
        )

    # 전체 강도: 최빈값 (동일 빈도 시 강한 쪽 우선)
    strength_counter = Counter(e.strength for e in evidences)
    strength_order = ['strong', 'moderate', 'weak']

    max_count = max(strength_counter.values())
    for s in strength_order:
        if strength_counter.get(s, 0) == max_count:
            overall = s
            break
    else:
        overall = 'moderate'

    # 모달리티 커버리지
    modalities = sorted(set(e.modality for e in evidences))

    return EvidenceBundle(
        claim=claim,
        evidences=list(evidences),
        overall_strength=overall,
        modality_coverage=modalities,
    )


def assess_coverage(bundle: EvidenceBundle) -> dict:
    """모달리티 커버리지 분석

    Args:
        bundle: 증거 묶음

    Returns:
        커버리지 분석 딕셔너리
    """
    all_modalities = {'text', 'image', 'audio', 'data'}
    covered = set(bundle.modality_coverage)
    missing = all_modalities - covered

    # 모달리티별 증거 수
    modality_counts: dict[str, int] = Counter()
    for e in bundle.evidences:
        modality_counts[e.modality] += 1

    # 강도 분포
    strength_counts: dict[str, int] = Counter()
    for e in bundle.evidences:
        strength_counts[e.strength] += 1

    coverage_ratio = len(covered) / len(all_modalities) if all_modalities else 0.0

    return {
        'covered_modalities': sorted(covered),
        'missing_modalities': sorted(missing),
        'coverage_ratio': round(coverage_ratio, 2),
        'modality_counts': dict(modality_counts),
        'strength_distribution': dict(strength_counts),
        'total_evidences': len(bundle.evidences),
    }


def find_contradictions(
    evidences: list[Evidence],
) -> list[tuple[Evidence, Evidence]]:
    """모순 증거 쌍 탐지

    같은 주장에 대해 하나는 strong, 다른 하나는 weak인 경우를 모순으로 판별합니다.
    또한 내용에 부정 키워드가 포함된 경우도 모순 후보로 검토합니다.

    Args:
        evidences: 증거 목록

    Returns:
        모순 증거 쌍 목록
    """
    # 주장별 그룹화
    claim_groups: dict[str, list[Evidence]] = {}
    for e in evidences:
        claim_key = e.claim.strip().lower()
        if claim_key not in claim_groups:
            claim_groups[claim_key] = []
        claim_groups[claim_key].append(e)

    contradictions: list[tuple[Evidence, Evidence]] = []

    # 부정 키워드
    negation_words = {
        '아니', '없', '반대', '부정', '거짓', '틀',
        'not', 'no', 'false', 'wrong', 'incorrect', 'deny',
        '불가능', '실패', '감소',
    }

    for claim_key, group in claim_groups.items():
        if len(group) < 2:
            continue

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                a, b = group[i], group[j]

                # 강도 대립 (strong vs weak)
                if (a.strength == 'strong' and b.strength == 'weak') or \
                   (a.strength == 'weak' and b.strength == 'strong'):
                    contradictions.append((a, b))
                    continue

                # 부정 키워드 포함 여부 비교
                a_has_neg = any(nw in a.content.lower() for nw in negation_words)
                b_has_neg = any(nw in b.content.lower() for nw in negation_words)

                if a_has_neg != b_has_neg:
                    contradictions.append((a, b))

    return contradictions
