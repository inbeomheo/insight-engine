"""
자가복구 생성 서비스.

콘텐츠 생성 실패 시 자동 복구 전략을 제안하고
입력 단순화 등의 복구 처리를 수행한다.
"""

from dataclasses import dataclass
import uuid
import re


@dataclass
class GenerationAttempt:
    """콘텐츠 생성 시도."""
    attempt_id: str
    content_type: str
    input_text: str
    output_text: str
    quality_score: float  # 0.0 ~ 1.0
    status: str  # success / failed / partial


@dataclass
class RecoveryStrategy:
    """복구 전략."""
    strategy_type: str  # simplify / chunk / retry / fallback
    description: str


def assess_quality(output_text: str) -> float:
    """
    품질 점수 (0~1). 길이/구조/완성도 기반.

    - 길이 점수: 100자 이상이면 만점 기여
    - 구조 점수: 줄바꿈/문단 존재 여부
    - 완성도 점수: 문장 종결 여부
    """
    if not output_text or not output_text.strip():
        return 0.0

    text = output_text.strip()
    score = 0.0

    # 길이 점수 (0 ~ 0.4)
    text_len = len(text)
    if text_len >= 200:
        score += 0.4
    elif text_len >= 100:
        score += 0.3
    elif text_len >= 50:
        score += 0.2
    else:
        score += 0.1

    # 구조 점수 (0 ~ 0.3): 문단이나 줄바꿈 존재
    lines = text.split("\n")
    if len(lines) >= 3:
        score += 0.3
    elif len(lines) >= 2:
        score += 0.2
    else:
        score += 0.1

    # 완성도 점수 (0 ~ 0.3): 문장 종결 부호 존재
    sentences = re.findall(r'[.!?。]', text)
    if len(sentences) >= 3:
        score += 0.3
    elif len(sentences) >= 1:
        score += 0.2
    else:
        score += 0.05

    return round(min(score, 1.0), 2)


def needs_recovery(attempt: GenerationAttempt) -> bool:
    """
    복구 필요 여부.

    quality_score < 0.5 또는 status가 failed이면 복구 필요.
    """
    if attempt.status == "failed":
        return True
    if attempt.quality_score < 0.5:
        return True
    return False


def suggest_recovery(attempt: GenerationAttempt) -> RecoveryStrategy:
    """
    실패 유형별 복구 전략 제안.

    - failed + 입력 긴 경우 → simplify
    - failed + 입력 짧은 경우 → retry
    - partial → chunk (분할 처리)
    - 낮은 품질 → fallback
    """
    if attempt.status == "failed":
        if len(attempt.input_text) > 500:
            return RecoveryStrategy(
                strategy_type="simplify",
                description="입력 텍스트가 길어 단순화 후 재시도합니다.",
            )
        else:
            return RecoveryStrategy(
                strategy_type="retry",
                description="짧은 입력이므로 동일 조건으로 재시도합니다.",
            )

    if attempt.status == "partial":
        return RecoveryStrategy(
            strategy_type="chunk",
            description="부분 생성 결과를 청크로 분할하여 보완합니다.",
        )

    # 낮은 품질
    return RecoveryStrategy(
        strategy_type="fallback",
        description="대체 모델이나 간소화된 프롬프트로 재생성합니다.",
    )


def apply_simplification(input_text: str) -> str:
    """
    입력 단순화.

    - 긴 문장을 마침표 기준으로 분할하여 앞부분만 유지
    - 괄호 내용 제거
    - 연속 공백 정리
    """
    if not input_text or not input_text.strip():
        return input_text

    text = input_text.strip()

    # 괄호 내용 제거 (한국어 괄호 포함)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'（[^）]*）', '', text)

    # 연속 공백 정리
    text = re.sub(r'\s+', ' ', text).strip()

    # 긴 텍스트는 앞부분만 유지 (문장 단위)
    if len(text) > 500:
        # 마침표 기준 분할 후 500자 이내로
        sentences = re.split(r'(?<=[.!?。])\s*', text)
        simplified = ""
        for sent in sentences:
            if len(simplified) + len(sent) > 500:
                break
            simplified += sent + " "
        text = simplified.strip() if simplified.strip() else text[:500]

    return text
