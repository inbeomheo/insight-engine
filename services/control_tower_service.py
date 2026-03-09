"""
컨트롤 타워 서비스.

여러 파이프라인의 상태를 통합 모니터링하고
이상 징후 알림을 생성한다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class PipelineStatus:
    """파이프라인 상태."""
    pipeline_id: str
    name: str
    status: str = "idle"  # idle / running / completed / failed
    progress_pct: float = 0.0
    started_at: str = ""
    error_count: int = 0


@dataclass
class TowerDashboard:
    """컨트롤 타워 대시보드."""
    total_pipelines: int
    active: int
    completed: int
    failed: int
    avg_progress: float
    alerts: list[str] = field(default_factory=list)


# 인메모리 저장소
_pipelines: dict[str, PipelineStatus] = {}


def _reset_store():
    """테스트용 저장소 초기화."""
    _pipelines.clear()


def register_pipeline(pipeline_id: str, name: str) -> PipelineStatus:
    """
    파이프라인 등록.

    새 파이프라인을 idle 상태로 등록한다.
    """
    status = PipelineStatus(
        pipeline_id=pipeline_id,
        name=name,
        status="idle",
        progress_pct=0.0,
        started_at=datetime.now(timezone.utc).isoformat(),
        error_count=0,
    )
    _pipelines[pipeline_id] = status
    return status


def update_status(
    pipeline_id: str,
    status: str,
    progress_pct: float,
    error_count: int = 0,
) -> PipelineStatus:
    """
    파이프라인 상태 업데이트.

    Raises:
        KeyError: 등록되지 않은 pipeline_id.
    """
    if pipeline_id not in _pipelines:
        raise KeyError(f"Pipeline '{pipeline_id}' not registered")

    ps = _pipelines[pipeline_id]
    ps.status = status
    ps.progress_pct = progress_pct
    ps.error_count = error_count
    return ps


def get_dashboard(statuses: list[PipelineStatus]) -> TowerDashboard:
    """
    대시보드 집계.

    Args:
        statuses: 파이프라인 상태 리스트.

    Returns:
        TowerDashboard 집계 결과.
    """
    total = len(statuses)
    active = sum(1 for s in statuses if s.status == "running")
    completed = sum(1 for s in statuses if s.status == "completed")
    failed = sum(1 for s in statuses if s.status == "failed")

    if total > 0:
        avg_progress = sum(s.progress_pct for s in statuses) / total
    else:
        avg_progress = 0.0

    alerts = generate_alerts(statuses)

    return TowerDashboard(
        total_pipelines=total,
        active=active,
        completed=completed,
        failed=failed,
        avg_progress=round(avg_progress, 1),
        alerts=alerts,
    )


def generate_alerts(statuses: list[PipelineStatus]) -> list[str]:
    """
    이상 징후 알림 생성.

    - 실패율 > 30%
    - 진행률 0%인 running 파이프라인 (정체)
    - 에러 카운트 3회 이상
    """
    if not statuses:
        return []

    alerts = []
    total = len(statuses)
    failed_count = sum(1 for s in statuses if s.status == "failed")

    # 실패율 30% 초과 경고
    if total > 0:
        fail_rate = failed_count / total
        if fail_rate > 0.3:
            pct = round(fail_rate * 100, 1)
            alerts.append(f"실패율 {pct}%: 전체 {total}개 중 {failed_count}개 실패")

    # 개별 파이프라인 이상 징후
    for s in statuses:
        # running인데 진행률 0% → 정체
        if s.status == "running" and s.progress_pct == 0.0:
            alerts.append(f"'{s.name}' 파이프라인 진행 정체 (0%)")

        # 에러 3회 이상
        if s.error_count >= 3:
            alerts.append(f"'{s.name}' 파이프라인 에러 다발 ({s.error_count}회)")

    return alerts
