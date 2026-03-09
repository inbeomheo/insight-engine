"""
실행 버전/재생 서비스.

파이프라인 실행 이력을 버전으로 관리하고,
버전 간 차이 비교 및 스냅샷 재생을 지원한다.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid


@dataclass
class ExecutionVersion:
    """실행 버전."""
    version_id: str
    pipeline_id: str
    version_number: int
    snapshot: dict = field(default_factory=dict)
    created_at: str = ""
    tags: list[str] = field(default_factory=list)


# 인메모리 저장소
_versions: dict[str, ExecutionVersion] = {}
# pipeline_id → 다음 버전 번호
_version_counters: dict[str, int] = {}


def _reset_store():
    """테스트용 저장소 초기화."""
    _versions.clear()
    _version_counters.clear()


def save_version(
    pipeline_id: str,
    snapshot: dict,
    tags: list[str] | None = None,
) -> ExecutionVersion:
    """
    실행 스냅샷 저장.

    버전 번호는 pipeline_id별로 자동 증가.
    """
    if tags is None:
        tags = []

    # 버전 번호 자동 증가
    if pipeline_id not in _version_counters:
        _version_counters[pipeline_id] = 1
    else:
        _version_counters[pipeline_id] += 1

    version_number = _version_counters[pipeline_id]
    version_id = uuid.uuid4().hex[:12]

    version = ExecutionVersion(
        version_id=version_id,
        pipeline_id=pipeline_id,
        version_number=version_number,
        snapshot=dict(snapshot),  # 방어적 복사
        created_at=datetime.now(timezone.utc).isoformat(),
        tags=list(tags),
    )

    _versions[version_id] = version
    return version


def list_versions(pipeline_id: str) -> list[ExecutionVersion]:
    """
    특정 파이프라인의 버전 목록 반환.

    버전 번호 오름차순 정렬.
    """
    result = [v for v in _versions.values() if v.pipeline_id == pipeline_id]
    result.sort(key=lambda v: v.version_number)
    return result


def get_version(version_id: str) -> ExecutionVersion | None:
    """버전 ID로 조회."""
    return _versions.get(version_id)


def compare_versions(
    v1: ExecutionVersion,
    v2: ExecutionVersion,
) -> dict:
    """
    두 버전의 스냅샷 차이점 비교.

    Returns:
        {
            "added": v2에만 있는 키 목록,
            "removed": v1에만 있는 키 목록,
            "changed": 양쪽 다 있지만 값이 다른 키 목록,
        }
    """
    keys1 = set(v1.snapshot.keys())
    keys2 = set(v2.snapshot.keys())

    added = sorted(keys2 - keys1)
    removed = sorted(keys1 - keys2)
    changed = sorted(
        k for k in keys1 & keys2
        if v1.snapshot[k] != v2.snapshot[k]
    )

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def replay_version(version: ExecutionVersion) -> dict:
    """
    스냅샷 기반 재생 데이터 반환.

    스냅샷에 메타데이터를 추가하여 반환.
    """
    return {
        "version_id": version.version_id,
        "pipeline_id": version.pipeline_id,
        "version_number": version.version_number,
        "replayed_at": datetime.now(timezone.utc).isoformat(),
        "snapshot": dict(version.snapshot),
    }
