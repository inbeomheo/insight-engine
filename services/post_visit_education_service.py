"""
진료후 교육 서비스 — 진료/시술 후 교육 자료 생성
"""

import uuid
from dataclasses import dataclass, field


DEFAULT_DISCLAIMER = "본 자료는 참고용이며 전문 의료인의 진단 및 처방을 대체할 수 없습니다."


@dataclass
class EducationMaterial:
    """교육 자료"""
    material_id: str
    procedure: str
    instructions: list[str]
    warnings: list[str]
    follow_up: list[str]
    emergency_signs: list[str]
    disclaimer: str


def generate_material(procedure: str, instructions: list[str],
                      warnings: list[str]) -> EducationMaterial:
    """교육 자료 생성 — 의료 면책조항 자동 포함"""
    return EducationMaterial(
        material_id=str(uuid.uuid4())[:8],
        procedure=procedure,
        instructions=instructions,
        warnings=warnings,
        follow_up=[],
        emergency_signs=[],
        disclaimer=DEFAULT_DISCLAIMER
    )


def simplify_language(material: EducationMaterial, reading_level: str = 'simple') -> EducationMaterial:
    """쉬운 말로 변환 — 간단한 규칙 기반"""
    replacements = {
        '투여': '복용',
        '처방': '약 지시',
        '부작용': '나쁜 반응',
        '합병증': '문제',
        '경구': '입으로',
        '외용': '바르는',
        '도포': '바르기',
        '섭취': '먹기',
    }

    def simplify_text(text: str) -> str:
        result = text
        for old, new in replacements.items():
            result = result.replace(old, new)
        return result

    return EducationMaterial(
        material_id=material.material_id,
        procedure=material.procedure,
        instructions=[simplify_text(i) for i in material.instructions],
        warnings=[simplify_text(w) for w in material.warnings],
        follow_up=[simplify_text(f) for f in material.follow_up],
        emergency_signs=[simplify_text(e) for e in material.emergency_signs],
        disclaimer=material.disclaimer
    )


def create_checklist(material: EducationMaterial) -> list[str]:
    """체크리스트 생성"""
    checklist = []
    for inst in material.instructions:
        checklist.append(f"[ ] {inst}")
    for warn in material.warnings:
        checklist.append(f"[!] {warn}")
    for fu in material.follow_up:
        checklist.append(f"[>] {fu}")
    return checklist


def validate_material(material: EducationMaterial) -> list[str]:
    """필수 항목 검증"""
    errors = []
    if not material.procedure:
        errors.append('시술명이 비어 있습니다.')
    if not material.instructions:
        errors.append('지시사항이 없습니다.')
    if not material.warnings:
        errors.append('주의사항이 없습니다.')
    if not material.disclaimer:
        errors.append('면책조항이 없습니다.')
    return errors
