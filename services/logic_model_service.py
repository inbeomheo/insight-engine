"""
로직모델 서비스 — 프로그램/프로젝트 로직모델 구성
"""

import uuid
from dataclasses import dataclass, field


ELEMENT_CHAIN = ['input', 'activity', 'output', 'outcome', 'impact']


@dataclass
class LogicElement:
    """로직 요소"""
    element_id: str
    element_type: str  # input / activity / output / outcome / impact
    description: str
    indicators: list[str]


@dataclass
class LogicModel:
    """로직모델"""
    model_id: str
    title: str
    elements: list[LogicElement] = field(default_factory=list)
    connections: list[tuple] = field(default_factory=list)


def create_model(title: str) -> LogicModel:
    """로직모델 생성"""
    return LogicModel(
        model_id=str(uuid.uuid4())[:8],
        title=title
    )


def add_element(model: LogicModel, element_type: str, description: str,
                indicators: list[str]) -> LogicModel:
    """요소 추가"""
    if element_type not in ELEMENT_CHAIN:
        raise ValueError(f"유효하지 않은 요소 유형: {element_type}")

    element = LogicElement(
        element_id=str(uuid.uuid4())[:8],
        element_type=element_type,
        description=description,
        indicators=indicators
    )
    new_elements = model.elements + [element]
    return LogicModel(
        model_id=model.model_id,
        title=model.title,
        elements=new_elements,
        connections=model.connections
    )


def connect(model: LogicModel, from_id: str, to_id: str) -> LogicModel:
    """요소 연결"""
    element_ids = {e.element_id for e in model.elements}
    if from_id not in element_ids:
        raise ValueError(f"존재하지 않는 요소: {from_id}")
    if to_id not in element_ids:
        raise ValueError(f"존재하지 않는 요소: {to_id}")

    new_connections = model.connections + [(from_id, to_id)]
    return LogicModel(
        model_id=model.model_id,
        title=model.title,
        elements=model.elements,
        connections=new_connections
    )


def validate_model(model: LogicModel) -> list[str]:
    """로직모델 검증 — 입력→활동→산출→성과→임팩트 체인"""
    errors = []
    type_present = {e.element_type for e in model.elements}

    for required in ELEMENT_CHAIN:
        if required not in type_present:
            errors.append(f"'{required}' 유형의 요소가 없습니다.")

    # 연결 체인 검증: 각 단계가 다음 단계로 연결되어야 함
    if model.connections:
        type_map = {e.element_id: e.element_type for e in model.elements}
        for from_id, to_id in model.connections:
            from_type = type_map.get(from_id, '')
            to_type = type_map.get(to_id, '')
            if from_type and to_type:
                from_idx = ELEMENT_CHAIN.index(from_type) if from_type in ELEMENT_CHAIN else -1
                to_idx = ELEMENT_CHAIN.index(to_type) if to_type in ELEMENT_CHAIN else -1
                if from_idx >= 0 and to_idx >= 0 and to_idx != from_idx + 1:
                    errors.append(f"'{from_type}' → '{to_type}' 연결은 권장 체인 순서가 아닙니다.")

    return errors


def export_model(model: LogicModel) -> str:
    """텍스트 내보내기"""
    lines = [f"로직모델: {model.title}", ""]

    for etype in ELEMENT_CHAIN:
        elements = [e for e in model.elements if e.element_type == etype]
        lines.append(f"[{etype.upper()}]")
        for e in elements:
            lines.append(f"  - {e.description}")
            if e.indicators:
                lines.append(f"    지표: {', '.join(e.indicators)}")
        lines.append("")

    if model.connections:
        lines.append("[연결]")
        for from_id, to_id in model.connections:
            lines.append(f"  {from_id} → {to_id}")

    return '\n'.join(lines)
