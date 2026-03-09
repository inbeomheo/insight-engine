"""
브랜드 보이스 드리프트 감지 + 가드레일 적용 서비스

문단별 브랜드 보이스 이탈 점수화 + 생성 중 브랜드 규칙/금지어/CTA 원칙 재주입.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class BrandRules:
    """브랜드 보이스 규칙 정의."""
    brand_name: str
    tone: str                              # "전문적", "친근한", "격식있는"
    forbidden_words: list                  # 금지어 목록
    required_cta: str = ""                 # 필수 CTA 문구
    max_sentence_length: int = 0           # 최대 문장 길이 (0=제한없음)
    preferred_words: list = field(default_factory=list)


@dataclass
class ParagraphDrift:
    """문단별 이탈 점수."""
    paragraph_index: int
    text_preview: str       # 첫 50자
    drift_score: float      # 0~100 (0=완벽 일치, 100=완전 이탈)
    violations: list        # 위반 사항 목록


@dataclass
class Violation:
    """위반 사항 상세."""
    violation_type: str     # "forbidden_word", "tone_mismatch", "cta_missing", "sentence_too_long"
    detail: str
    location: str           # "paragraph 3" 등
    severity: str           # "high", "medium", "low"


# ── 톤 키워드 매핑 ──
_TONE_KEYWORDS = {
    '전문적': {
        'positive': ['분석', '검토', '평가', '수행', '적용', '구현', '고려', '판단'],
        'negative': ['대박', '짱', 'ㅋㅋ', 'ㅎㅎ', '완전', '개꿀', '레알', '존맛'],
    },
    '친근한': {
        'positive': ['함께', '우리', '여러분', '쉽게', '재미', '즐거운'],
        'negative': ['본 보고서는', '상기', '하기', '귀하', '당 사업'],
    },
    '격식있는': {
        'positive': ['귀하', '존경', '안내', '말씀', '감사', '요청'],
        'negative': ['대박', '짱', 'ㅋㅋ', 'ㅎㅎ', '완전', '개꿀'],
    },
}


def _split_paragraphs(content: str) -> List[str]:
    """콘텐츠를 문단 단위로 분리합니다."""
    paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
    return paragraphs


def _split_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 한국어/영어 문장 분리 (마침표, 물음표, 느낌표 기준)
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _check_forbidden_words(text: str, forbidden_words: List[str]) -> List[str]:
    """텍스트에서 금지어 포함 여부를 확인합니다."""
    found = []
    text_lower = text.lower()
    for word in forbidden_words:
        if word.lower() in text_lower:
            found.append(word)
    return found


def _check_tone_mismatch(text: str, tone: str) -> List[str]:
    """톤 불일치 단어를 감지합니다."""
    mismatches = []
    tone_config = _TONE_KEYWORDS.get(tone)
    if not tone_config:
        return mismatches

    text_lower = text.lower()
    for neg_word in tone_config['negative']:
        if neg_word.lower() in text_lower:
            mismatches.append(neg_word)
    return mismatches


def _check_sentence_length(text: str, max_length: int) -> List[str]:
    """최대 문장 길이 초과 문장을 찾습니다."""
    if max_length <= 0:
        return []

    violations = []
    sentences = _split_sentences(text)
    for sentence in sentences:
        if len(sentence) > max_length:
            preview = sentence[:30] + '...' if len(sentence) > 30 else sentence
            violations.append(f"문장 길이 {len(sentence)}자 초과: \"{preview}\"")
    return violations


def score_drift(content: str, brand_rules: BrandRules) -> List[ParagraphDrift]:
    """문단별 브랜드 보이스 이탈 점수를 계산합니다.

    점수 기준:
    - 금지어 포함: +30점
    - 톤 불일치: +25점
    - 문장 길이 초과: +15점
    - 최대 100점 상한

    Args:
        content: 분석할 콘텐츠
        brand_rules: 브랜드 규칙

    Returns:
        문단별 ParagraphDrift 목록
    """
    if not content or not content.strip():
        return []

    paragraphs = _split_paragraphs(content)
    results = []

    for idx, paragraph in enumerate(paragraphs):
        drift_score = 0.0
        violations = []

        # 금지어 검사: 건당 +30
        forbidden_found = _check_forbidden_words(paragraph, brand_rules.forbidden_words)
        for word in forbidden_found:
            drift_score += 30.0
            violations.append(f"금지어 \"{word}\" 포함")

        # 톤 불일치 검사: 건당 +25
        tone_mismatches = _check_tone_mismatch(paragraph, brand_rules.tone)
        for word in tone_mismatches:
            drift_score += 25.0
            violations.append(f"톤 불일치 표현 \"{word}\"")

        # 문장 길이 초과 검사: 건당 +15
        length_violations = _check_sentence_length(paragraph, brand_rules.max_sentence_length)
        for detail in length_violations:
            drift_score += 15.0
            violations.append(detail)

        # 상한 100
        drift_score = min(drift_score, 100.0)

        preview = paragraph[:50] if len(paragraph) > 50 else paragraph
        results.append(ParagraphDrift(
            paragraph_index=idx,
            text_preview=preview,
            drift_score=drift_score,
            violations=violations,
        ))

    return results


def apply_guardrails(prompt: str, rules: BrandRules) -> str:
    """프롬프트 끝에 브랜드 규칙을 주입합니다.

    Args:
        prompt: 원본 프롬프트
        rules: 브랜드 규칙

    Returns:
        규칙이 주입된 프롬프트
    """
    guardrail_parts = [
        f"\n\n--- 브랜드 가드레일 ({rules.brand_name}) ---",
        f"톤: {rules.tone}",
    ]

    if rules.forbidden_words:
        words_str = ', '.join(rules.forbidden_words)
        guardrail_parts.append(f"금지어 (절대 사용 금지): {words_str}")

    if rules.required_cta:
        guardrail_parts.append(f"필수 CTA: 반드시 다음 문구를 포함하세요 — \"{rules.required_cta}\"")

    if rules.max_sentence_length > 0:
        guardrail_parts.append(f"문장 길이 제한: 한 문장 {rules.max_sentence_length}자 이내")

    if rules.preferred_words:
        pref_str = ', '.join(rules.preferred_words)
        guardrail_parts.append(f"선호 표현: {pref_str}")

    guardrail_parts.append("--- 가드레일 끝 ---")

    return prompt + '\n'.join(guardrail_parts)


def check_violations(content: str, rules: BrandRules) -> List[Violation]:
    """전체 콘텐츠에서 브랜드 규칙 위반 사항을 찾습니다.

    Args:
        content: 검사할 콘텐츠
        rules: 브랜드 규칙

    Returns:
        Violation 목록
    """
    if not content or not content.strip():
        return []

    violations = []
    paragraphs = _split_paragraphs(content)

    for idx, paragraph in enumerate(paragraphs):
        location = f"paragraph {idx + 1}"

        # 금지어 검사 (severity: high)
        forbidden_found = _check_forbidden_words(paragraph, rules.forbidden_words)
        for word in forbidden_found:
            violations.append(Violation(
                violation_type="forbidden_word",
                detail=f"금지어 \"{word}\" 사용됨",
                location=location,
                severity="high",
            ))

        # 톤 불일치 검사 (severity: medium)
        tone_mismatches = _check_tone_mismatch(paragraph, rules.tone)
        for word in tone_mismatches:
            violations.append(Violation(
                violation_type="tone_mismatch",
                detail=f"톤 불일치 표현 \"{word}\"",
                location=location,
                severity="medium",
            ))

        # 문장 길이 초과 (severity: low)
        length_violations = _check_sentence_length(paragraph, rules.max_sentence_length)
        for detail in length_violations:
            violations.append(Violation(
                violation_type="sentence_too_long",
                detail=detail,
                location=location,
                severity="low",
            ))

    # CTA 누락 검사 (severity: high)
    if rules.required_cta and rules.required_cta not in content:
        violations.append(Violation(
            violation_type="cta_missing",
            detail=f"필수 CTA \"{rules.required_cta}\" 누락",
            location="entire content",
            severity="high",
        ))

    return violations


def get_drift_summary(drifts: List[ParagraphDrift]) -> Dict:
    """이탈 분석 결과 요약을 생성합니다.

    Args:
        drifts: ParagraphDrift 목록

    Returns:
        평균 점수, 최고 이탈 문단, 주요 위반 요약을 포함하는 dict
    """
    if not drifts:
        return {
            'average_score': 0.0,
            'max_drift_paragraph': None,
            'total_violations': 0,
            'violation_summary': {},
        }

    avg_score = round(sum(d.drift_score for d in drifts) / len(drifts), 1)

    max_drift = max(drifts, key=lambda d: d.drift_score)
    max_paragraph = {
        'index': max_drift.paragraph_index,
        'score': max_drift.drift_score,
        'preview': max_drift.text_preview,
    }

    # 위반 유형별 집계
    violation_counts: Dict[str, int] = {}
    total = 0
    for drift in drifts:
        total += len(drift.violations)
        for v in drift.violations:
            # 위반 유형 추출 (금지어, 톤 불일치, 문장 길이)
            if '금지어' in v:
                key = 'forbidden_word'
            elif '톤 불일치' in v:
                key = 'tone_mismatch'
            elif '문장 길이' in v:
                key = 'sentence_too_long'
            else:
                key = 'other'
            violation_counts[key] = violation_counts.get(key, 0) + 1

    return {
        'average_score': avg_score,
        'max_drift_paragraph': max_paragraph,
        'total_violations': total,
        'violation_summary': violation_counts,
    }
