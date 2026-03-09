"""
탄소 스케줄러 서비스 — 탄소 배출이 낮은 시간대에 작업 스케줄링
"""

from dataclasses import dataclass


@dataclass
class TimeSlot:
    """시간대"""
    slot_id: str
    start_hour: int
    end_hour: int
    carbon_intensity: float  # g CO2/kWh
    renewable_pct: float


@dataclass
class ScheduleDecision:
    """스케줄 결정"""
    task_name: str
    recommended_slot: TimeSlot
    carbon_saved_g: float
    reason: str


def find_green_slots(slots: list[TimeSlot], threshold: float = 200.0) -> list[TimeSlot]:
    """친환경 슬롯 — intensity < threshold"""
    return [s for s in slots if s.carbon_intensity < threshold]


def schedule_task(task_name: str, energy_kwh: float, slots: list[TimeSlot]) -> ScheduleDecision:
    """최적 시간대 추천 — 가장 낮은 탄소 집약도"""
    if not slots:
        raise ValueError("사용 가능한 슬롯이 없습니다.")

    best = min(slots, key=lambda s: s.carbon_intensity)
    worst = max(slots, key=lambda s: s.carbon_intensity)

    saved = calculate_savings(worst, best, energy_kwh)

    return ScheduleDecision(
        task_name=task_name,
        recommended_slot=best,
        carbon_saved_g=saved,
        reason=f"{best.start_hour}시~{best.end_hour}시 슬롯 (탄소 집약도: {best.carbon_intensity}g CO2/kWh, 재생에너지: {best.renewable_pct}%)"
    )


def calculate_savings(default_slot: TimeSlot, green_slot: TimeSlot, energy_kwh: float) -> float:
    """탄소 절감량 (g)"""
    default_emission = default_slot.carbon_intensity * energy_kwh
    green_emission = green_slot.carbon_intensity * energy_kwh
    return round(default_emission - green_emission, 2)
