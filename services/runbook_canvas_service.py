"""
런북 캔버스 서비스 — 운영 절차서를 캔버스 형태로 구조화
"""

import uuid
from dataclasses import dataclass, field


VALID_STEP_TYPES = {"manual", "automated", "decision"}


@dataclass
class RunbookStep:
    """런북 단계"""
    step_id: str
    title: str
    description: str
    step_type: str  # manual / automated / decision
    next_steps: list = field(default_factory=list)  # list[str] — step_id 참조
    checklist: list = field(default_factory=list)    # list[str]


@dataclass
class Runbook:
    """런북"""
    runbook_id: str
    title: str
    steps: list = field(default_factory=list)  # list[RunbookStep]
    owner: str = ""
    version: str = "1.0"


def _new_id(prefix: str = "step") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_runbook(title: str, owner: str) -> Runbook:
    """런북 생성

    Args:
        title: 런북 제목
        owner: 소유자

    Returns:
        Runbook: 생성된 런북
    """
    if not title.strip():
        raise ValueError("런북 제목은 비어있을 수 없습니다.")

    return Runbook(
        runbook_id=_new_id("runbook"),
        title=title.strip(),
        steps=[],
        owner=owner.strip(),
        version="1.0",
    )


def add_step(runbook: Runbook, step_config: dict) -> Runbook:
    """런북에 단계 추가

    Args:
        runbook: 대상 런북
        step_config: 단계 설정
            title, description, step_type, next_steps (선택), checklist (선택)

    Returns:
        Runbook: 단계가 추가된 런북
    """
    step_type = step_config.get("step_type", "manual")
    if step_type not in VALID_STEP_TYPES:
        raise ValueError(f"유효하지 않은 단계 유형: {step_type}")

    step = RunbookStep(
        step_id=step_config.get("step_id", _new_id()),
        title=step_config.get("title", ""),
        description=step_config.get("description", ""),
        step_type=step_type,
        next_steps=step_config.get("next_steps", []),
        checklist=step_config.get("checklist", []),
    )

    new_steps = list(runbook.steps) + [step]
    return Runbook(
        runbook_id=runbook.runbook_id,
        title=runbook.title,
        steps=new_steps,
        owner=runbook.owner,
        version=runbook.version,
    )


def validate_runbook(runbook: Runbook) -> list:
    """런북 검증 — 고아 단계, 순환 참조, 빈 체크리스트 탐지

    Args:
        runbook: 검증할 런북

    Returns:
        list[str]: 검증 오류 목록 (비어있으면 유효)
    """
    errors = []
    step_ids = {s.step_id for s in runbook.steps}

    # 1. 고아 단계 (참조하는 next_step이 존재하지 않는 경우)
    for step in runbook.steps:
        for ns in step.next_steps:
            if ns not in step_ids:
                errors.append(f"고아 참조: '{step.step_id}' → 존재하지 않는 '{ns}'")

    # 2. 순환 참조 탐지 (DFS)
    def _has_cycle(start_id: str) -> bool:
        visited = set()
        stack = [start_id]
        while stack:
            current = stack.pop()
            if current in visited:
                return True
            visited.add(current)
            step_map = {s.step_id: s for s in runbook.steps}
            if current in step_map:
                for ns in step_map[current].next_steps:
                    if ns in step_ids:
                        stack.append(ns)
        return False

    # 간단한 자기 참조 + 짧은 순환 탐지
    for step in runbook.steps:
        if step.step_id in step.next_steps:
            errors.append(f"자기 순환: '{step.step_id}'가 자기 자신을 참조")

    # DFS 기반 순환 탐지
    step_map = {s.step_id: s for s in runbook.steps}
    for step in runbook.steps:
        # 이 단계에서 시작해 자신으로 돌아오는 경로 검사
        visited = set()
        queue = list(step.next_steps)
        found_cycle = False
        while queue and not found_cycle:
            nid = queue.pop(0)
            if nid == step.step_id:
                # 자기 순환은 위에서 처리
                if nid not in step.next_steps or nid != step.step_id:
                    errors.append(f"순환 참조 감지: '{step.step_id}' 경로에 순환 존재")
                found_cycle = True
                break
            if nid in visited or nid not in step_ids:
                continue
            visited.add(nid)
            if nid in step_map:
                queue.extend(step_map[nid].next_steps)

    # 3. decision 단계의 빈 체크리스트
    for step in runbook.steps:
        if step.step_type == "decision" and not step.checklist:
            errors.append(f"빈 체크리스트: decision 단계 '{step.step_id}'에 체크리스트 없음")

    return errors


def export_as_checklist(runbook: Runbook) -> str:
    """런북을 체크리스트 텍스트로 내보내기

    Args:
        runbook: 대상 런북

    Returns:
        str: 체크리스트 텍스트
    """
    lines = [f"# {runbook.title}", f"담당자: {runbook.owner}", f"버전: {runbook.version}", ""]

    for idx, step in enumerate(runbook.steps, 1):
        type_label = {"manual": "수동", "automated": "자동", "decision": "판단"}.get(
            step.step_type, step.step_type
        )
        lines.append(f"## {idx}. {step.title} [{type_label}]")
        lines.append(f"   {step.description}")

        if step.checklist:
            for item in step.checklist:
                lines.append(f"   [ ] {item}")

        lines.append("")

    return "\n".join(lines)
