"""
보이스 파인튜닝 서비스 (T13.2)
1분 보이스 파인튜닝 시뮬레이션 — 외부 API 없이 규칙 기반으로 결과를 산출합니다.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 기본 학습 파라미터
_DEFAULT_TRAINING_PARAMS = {
    "epochs": 100,
    "learning_rate": 0.001,
    "batch_size": 8,
    "warmup_steps": 10,
}

# 모델 크기 기준 (에폭 수 기반)
_MODEL_SIZE_THRESHOLDS = [
    (500, "large"),
    (200, "medium"),
    (1, "small"),
]

# 품질 계수
_QUALITY_BASE = 60.0          # 기본 품질
_EPOCH_BONUS_RATE = 0.05      # 에폭당 보너스 (최대 +20)
_EPOCH_BONUS_CAP = 20.0
_LR_PENALTY_THRESHOLD = 0.01  # 이 이상이면 품질 페널티
_LR_PENALTY = 10.0
_LR_LOW_THRESHOLD = 0.0001   # 이 이하면 품질 보너스 (학습이 안정적)
_LR_LOW_BONUS = 5.0
_BATCH_BONUS_THRESHOLD = 16  # 이 이상이면 품질 보너스
_BATCH_BONUS = 3.0
_DESC_LENGTH_BONUS_RATE = 0.01  # 설명 글자당 보너스 (최대 +10)
_DESC_LENGTH_BONUS_CAP = 10.0


@dataclass
class FinetuneResult:
    """파인튜닝 결과"""
    finetune_id: str
    status: str
    estimated_quality: float
    training_steps: int
    model_size: str
    created_at: str


def _determine_model_size(epochs: int) -> str:
    """에폭 수에 따라 모델 크기를 결정합니다."""
    for threshold, size in _MODEL_SIZE_THRESHOLDS:
        if epochs >= threshold:
            return size
    return "small"


def _calculate_training_steps(epochs: int, batch_size: int) -> int:
    """학습 스텝 수를 산정합니다 (시뮬레이션)."""
    # 가상 데이터셋 크기 100 기준
    dataset_size = 100
    steps_per_epoch = max(1, dataset_size // batch_size)
    return epochs * steps_per_epoch


def _estimate_quality(
    audio_description: str,
    epochs: int,
    learning_rate: float,
    batch_size: int,
) -> float:
    """
    학습 파라미터와 설명에 따라 예상 품질을 규칙 기반으로 산정합니다.

    Returns:
        0.0 ~ 100.0 사이의 품질 점수
    """
    quality = _QUALITY_BASE

    # 에폭 보너스 (많을수록 좋지만 상한 있음)
    epoch_bonus = min(epochs * _EPOCH_BONUS_RATE, _EPOCH_BONUS_CAP)
    quality += epoch_bonus

    # 학습률 페널티/보너스
    if learning_rate > _LR_PENALTY_THRESHOLD:
        quality -= _LR_PENALTY
    elif learning_rate <= _LR_LOW_THRESHOLD:
        quality += _LR_LOW_BONUS

    # 배치 크기 보너스
    if batch_size >= _BATCH_BONUS_THRESHOLD:
        quality += _BATCH_BONUS

    # 설명 길이 보너스 (상세한 설명이 좋은 결과를 낸다는 가정)
    desc_bonus = min(len(audio_description) * _DESC_LENGTH_BONUS_RATE, _DESC_LENGTH_BONUS_CAP)
    quality += desc_bonus

    return round(max(0.0, min(100.0, quality)), 1)


def _determine_status(epochs: int, learning_rate: float) -> str:
    """학습 파라미터에 따라 상태를 결정합니다."""
    # 학습률이 너무 높으면 실패 위험
    if learning_rate > 0.1:
        return "failed"
    # 에폭이 0 이하면 보류
    if epochs <= 0:
        return "pending"
    # 에폭이 매우 적으면 학습 중
    if epochs < 10:
        return "training"
    return "completed"


def finetune_voice(audio_description: str, training_params: dict = None) -> FinetuneResult:
    """
    1분 보이스 파인튜닝을 시뮬레이션합니다.

    오디오 설명과 학습 파라미터를 기반으로 파인튜닝 결과를 규칙 기반으로 산출합니다.

    Args:
        audio_description: 오디오 특성 설명 텍스트
        training_params: 학습 파라미터 dict (선택)
            - epochs: 학습 에폭 수 (기본 100)
            - learning_rate: 학습률 (기본 0.001)
            - batch_size: 배치 크기 (기본 8)
            - warmup_steps: 웜업 스텝 (기본 10)

    Returns:
        FinetuneResult 결과 객체

    Raises:
        ValueError: 오디오 설명이 비어있을 때
    """
    if not audio_description or not audio_description.strip():
        raise ValueError("오디오 설명이 필요합니다")

    audio_description = audio_description.strip()

    # 파라미터 병합 (기본값 + 사용자 입력)
    params = dict(_DEFAULT_TRAINING_PARAMS)
    if training_params:
        for key in _DEFAULT_TRAINING_PARAMS:
            if key in training_params:
                params[key] = training_params[key]

    epochs = params["epochs"]
    learning_rate = params["learning_rate"]
    batch_size = params["batch_size"]

    # 결과 산출
    status = _determine_status(epochs, learning_rate)
    training_steps = _calculate_training_steps(epochs, batch_size)
    model_size = _determine_model_size(epochs)
    estimated_quality = _estimate_quality(
        audio_description, epochs, learning_rate, batch_size,
    )

    # 실패 상태면 품질 0
    if status == "failed":
        estimated_quality = 0.0

    result = FinetuneResult(
        finetune_id=uuid.uuid4().hex,
        status=status,
        estimated_quality=estimated_quality,
        training_steps=training_steps,
        model_size=model_size,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        "파인튜닝 완료: status=%s, quality=%.1f, steps=%d, size=%s",
        result.status, result.estimated_quality,
        result.training_steps, result.model_size,
    )

    return result
