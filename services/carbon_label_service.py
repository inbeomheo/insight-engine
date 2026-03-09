"""
탄소 라벨 서비스.

콘텐츠 생성 과정의 탄소 배출량을 추정하고 라벨을 부여한다.
"""

from dataclasses import dataclass, field
from typing import Optional
import uuid


@dataclass
class CarbonEstimate:
    """개별 탄소 추정"""
    process: str = ""
    energy_kwh: float = 0.0
    carbon_g: float = 0.0
    region: str = "global"


@dataclass
class CarbonLabel:
    """탄소 라벨"""
    content_id: str = ""
    estimates: list = field(default_factory=list)
    total_carbon_g: float = 0.0
    label_grade: str = "A"
    offset_suggestions: list = field(default_factory=list)


# 지역별 탄소 집약도 (gCO2/kWh)
REGION_CARBON_INTENSITY = {
    "global": 475,
    "us": 386,
    "eu": 276,
    "kr": 459,
    "jp": 471,
    "cn": 581,
    "nordic": 30,  # 수력/풍력 위주
}


def estimate_inference(
    tokens: int,
    model_size_b: float,
    region: str = "global"
) -> CarbonEstimate:
    """
    AI 추론 탄소 추정.

    토큰 수 x 모델 크기 기반으로 에너지 소비와 탄소 배출을 계산한다.
    """
    if tokens <= 0 or model_size_b <= 0:
        return CarbonEstimate(process="inference", region=region)

    # GPU 전력 소비 추정 (와트)
    # 모델 크기에 비례 (7B → ~200W, 70B → ~700W)
    gpu_watts = min(1000, 100 + model_size_b * 15)

    # 추론 시간 추정 (초): 토큰당 시간은 모델 크기에 비례
    tokens_per_sec = max(1, 1000 / model_size_b)
    inference_time_s = tokens / tokens_per_sec

    # 에너지 소비 (kWh)
    energy_kwh = (gpu_watts * inference_time_s) / (3600 * 1000)

    # PUE (Power Usage Effectiveness) 보정: 데이터센터 오버헤드
    pue = 1.2
    energy_kwh *= pue

    # 탄소 배출 (g)
    intensity = REGION_CARBON_INTENSITY.get(region, REGION_CARBON_INTENSITY["global"])
    carbon_g = energy_kwh * intensity

    return CarbonEstimate(
        process="inference",
        energy_kwh=round(energy_kwh, 6),
        carbon_g=round(carbon_g, 4),
        region=region,
    )


def estimate_storage(
    size_mb: float,
    duration_days: int,
    region: str = "global"
) -> CarbonEstimate:
    """
    저장소 탄소 추정.

    저장 크기와 기간 기반으로 탄소 배출을 계산한다.
    """
    if size_mb <= 0 or duration_days <= 0:
        return CarbonEstimate(process="storage", region=region)

    # 스토리지 전력: ~0.001 W/MB (SSD 기준)
    watts_per_mb = 0.001
    total_watts = size_mb * watts_per_mb

    # 에너지 (kWh): 와트 × 시간
    hours = duration_days * 24
    energy_kwh = (total_watts * hours) / 1000

    # PUE 보정
    pue = 1.2
    energy_kwh *= pue

    intensity = REGION_CARBON_INTENSITY.get(region, REGION_CARBON_INTENSITY["global"])
    carbon_g = energy_kwh * intensity

    return CarbonEstimate(
        process="storage",
        energy_kwh=round(energy_kwh, 6),
        carbon_g=round(carbon_g, 6),
        region=region,
    )


def calculate_label(estimates: list) -> CarbonLabel:
    """
    전체 탄소 라벨 생성.

    등급: A(<10g), B(<50g), C(<100g), D(<500g), E(500g+)
    """
    total_carbon = sum(e.carbon_g for e in estimates)

    if total_carbon < 10:
        grade = "A"
    elif total_carbon < 50:
        grade = "B"
    elif total_carbon < 100:
        grade = "C"
    elif total_carbon < 500:
        grade = "D"
    else:
        grade = "E"

    label = CarbonLabel(
        content_id=str(uuid.uuid4()),
        estimates=estimates,
        total_carbon_g=round(total_carbon, 4),
        label_grade=grade,
        offset_suggestions=[],
    )

    label.offset_suggestions = suggest_offset(label)
    return label


def suggest_offset(label: CarbonLabel) -> list:
    """탄소 상쇄 제안"""
    suggestions = []

    if label.total_carbon_g > 0:
        suggestions.append("에너지 효율이 높은 데이터센터(Nordic 등) 활용 검토")

    if label.total_carbon_g >= 50:
        suggestions.append("더 작은 모델 사용으로 추론 에너지 절감")

    if label.total_carbon_g >= 100:
        suggestions.append("캐싱 전략으로 중복 추론 방지")
        suggestions.append("배치 처리로 GPU 활용률 향상")

    if label.total_carbon_g >= 500:
        suggestions.append("탄소 크레딧 구매를 통한 상쇄 권장")
        suggestions.append("모델 양자화(INT8/INT4)로 에너지 소비 절감")

    if not suggestions:
        suggestions.append("현재 탄소 배출이 매우 낮습니다")

    return suggestions
