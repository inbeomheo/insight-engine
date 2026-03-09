"""
CoAgent 서비스 — 여러 에이전트가 협력하여 작업을 수행하는 오케스트레이션
"""

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone


VALID_ROLES = {"researcher", "writer", "reviewer", "editor"}
VALID_STATUSES = {"pending", "in_progress", "completed", "review"}


@dataclass
class AgentRole:
    """에이전트 역할"""
    agent_id: str
    name: str
    role: str  # researcher / writer / reviewer / editor
    capabilities: list = field(default_factory=list)


@dataclass
class CoTask:
    """협업 태스크"""
    task_id: str
    description: str
    assigned_agent: str
    status: str = "pending"  # pending / in_progress / completed / review
    output: str = ""


@dataclass
class CoSession:
    """협업 세션"""
    session_id: str
    agents: list = field(default_factory=list)   # list[AgentRole]
    tasks: list = field(default_factory=list)     # list[CoTask]
    messages: list = field(default_factory=list)  # list[dict]


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_session(agent_configs: list) -> CoSession:
    """협업 세션 생성

    Args:
        agent_configs: 에이전트 설정 목록
            각 항목: {"name": str, "role": str, "capabilities": list[str]}

    Returns:
        CoSession: 생성된 세션
    """
    agents = []
    for cfg in agent_configs:
        role = cfg.get("role", "writer")
        if role not in VALID_ROLES:
            raise ValueError(f"유효하지 않은 역할: {role}. 허용: {VALID_ROLES}")

        agent = AgentRole(
            agent_id=_new_id("agent"),
            name=cfg.get("name", "Agent"),
            role=role,
            capabilities=cfg.get("capabilities", []),
        )
        agents.append(agent)

    session = CoSession(
        session_id=_new_id("session"),
        agents=agents,
        tasks=[],
        messages=[{
            "type": "system",
            "content": f"세션 생성됨. 에이전트 {len(agents)}명 참여.",
            "timestamp": _timestamp(),
        }],
    )
    return session


def assign_task(session: CoSession, task_desc: str, agent_id: str) -> CoSession:
    """태스크 할당

    Args:
        session: 대상 세션
        task_desc: 태스크 설명
        agent_id: 할당할 에이전트 ID

    Returns:
        CoSession: 태스크가 추가된 세션
    """
    # 에이전트 존재 확인
    agent_ids = {a.agent_id for a in session.agents}
    if agent_id not in agent_ids:
        raise ValueError(f"존재하지 않는 에이전트: {agent_id}")

    task = CoTask(
        task_id=_new_id("task"),
        description=task_desc,
        assigned_agent=agent_id,
        status="in_progress",
    )

    new_tasks = list(session.tasks) + [task]
    new_messages = list(session.messages) + [{
        "type": "assign",
        "content": f"태스크 '{task_desc}' → {agent_id}",
        "timestamp": _timestamp(),
    }]

    return CoSession(
        session_id=session.session_id,
        agents=session.agents,
        tasks=new_tasks,
        messages=new_messages,
    )


def complete_task(session: CoSession, task_id: str, output: str) -> CoSession:
    """태스크 완료 처리

    Args:
        session: 대상 세션
        task_id: 완료할 태스크 ID
        output: 태스크 결과물

    Returns:
        CoSession: 업데이트된 세션
    """
    found = False
    new_tasks = []
    for t in session.tasks:
        if t.task_id == task_id:
            found = True
            updated = CoTask(
                task_id=t.task_id,
                description=t.description,
                assigned_agent=t.assigned_agent,
                status="completed",
                output=output,
            )
            new_tasks.append(updated)
        else:
            new_tasks.append(t)

    if not found:
        raise ValueError(f"존재하지 않는 태스크: {task_id}")

    new_messages = list(session.messages) + [{
        "type": "complete",
        "content": f"태스크 {task_id} 완료.",
        "timestamp": _timestamp(),
    }]

    return CoSession(
        session_id=session.session_id,
        agents=session.agents,
        tasks=new_tasks,
        messages=new_messages,
    )


def get_session_summary(session: CoSession) -> dict:
    """세션 요약 (완료율, 에이전트별 기여도)

    Args:
        session: 대상 세션

    Returns:
        dict: {total_tasks, completed, completion_rate, agent_contributions}
    """
    total = len(session.tasks)
    completed = sum(1 for t in session.tasks if t.status == "completed")

    # 에이전트별 기여도 (완료한 태스크 수)
    contributions = {}
    for agent in session.agents:
        agent_tasks = [t for t in session.tasks if t.assigned_agent == agent.agent_id]
        agent_completed = sum(1 for t in agent_tasks if t.status == "completed")
        contributions[agent.agent_id] = {
            "name": agent.name,
            "role": agent.role,
            "assigned": len(agent_tasks),
            "completed": agent_completed,
        }

    return {
        "session_id": session.session_id,
        "total_tasks": total,
        "completed": completed,
        "completion_rate": completed / total if total > 0 else 0.0,
        "agent_contributions": contributions,
        "message_count": len(session.messages),
    }
