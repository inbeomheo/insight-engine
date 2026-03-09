"""
인컨텍스트 QA 서비스.

콘텐츠 내 문맥 기반 품질 검사를 수행한다.
"""

from dataclasses import dataclass, field
import re
import uuid


@dataclass
class QACheck:
    """QA 검사 항목"""
    check_id: str = ""
    check_type: str = ""  # grammar / consistency / factual / style
    passed: bool = True
    details: str = ""
    location: str = ""


@dataclass
class QAReport:
    """QA 보고서"""
    content_id: str = ""
    checks: list = field(default_factory=list)
    pass_rate: float = 1.0
    critical_issues: int = 0


def check_consistency(content: str) -> list:
    """
    용어 일관성 검사.

    같은 개념을 다른 표기로 사용한 경우를 탐지한다.
    """
    checks = []

    # 일관성 검사 패턴 쌍 (동일 개념의 다른 표기)
    consistency_pairs = [
        ("인공지능", "AI"),
        ("머신러닝", "기계학습"),
        ("데이터베이스", "DB"),
        ("서버", "Server"),
        ("애플리케이션", "어플리케이션"),
    ]

    for term_a, term_b in consistency_pairs:
        has_a = term_a in content
        has_b = term_b in content

        if has_a and has_b:
            checks.append(QACheck(
                check_id=str(uuid.uuid4()),
                check_type="consistency",
                passed=False,
                details=f"'{term_a}'와 '{term_b}'이(가) 혼용되고 있습니다. 하나로 통일하세요.",
                location="전체 문서",
            ))

    if not checks:
        checks.append(QACheck(
            check_id=str(uuid.uuid4()),
            check_type="consistency",
            passed=True,
            details="용어 일관성 검사 통과",
            location="전체 문서",
        ))

    return checks


def check_grammar_basics(content: str) -> list:
    """
    기초 문법 검사.

    이중 공백, 이중 마침표, 줄 시작 공백 등을 검사한다.
    """
    checks = []
    lines = content.splitlines()

    for i, line in enumerate(lines, 1):
        # 이중 공백
        if "  " in line.strip():
            checks.append(QACheck(
                check_id=str(uuid.uuid4()),
                check_type="grammar",
                passed=False,
                details="이중 공백이 발견되었습니다",
                location=f"{i}번째 줄",
            ))

        # 이중 마침표
        if ".." in line and "..." not in line:
            checks.append(QACheck(
                check_id=str(uuid.uuid4()),
                check_type="grammar",
                passed=False,
                details="이중 마침표가 발견되었습니다",
                location=f"{i}번째 줄",
            ))

    if not checks:
        checks.append(QACheck(
            check_id=str(uuid.uuid4()),
            check_type="grammar",
            passed=True,
            details="기초 문법 검사 통과",
            location="전체 문서",
        ))

    return checks


def check_broken_references(content: str) -> list:
    """
    깨진 참조 검사.

    [TODO], [TBD], [FIXME], [INSERT] 등 미완성 마커를 탐지한다.
    """
    checks = []

    # 미완성 참조 패턴
    patterns = [
        (r'\[TODO\]', "[TODO]"),
        (r'\[TBD\]', "[TBD]"),
        (r'\[FIXME\]', "[FIXME]"),
        (r'\[INSERT\b[^\]]*\]', "[INSERT...]"),
        (r'\[XX+\]', "[XX]"),
        (r'TODO:', "TODO:"),
    ]

    for pattern, label in patterns:
        matches = list(re.finditer(pattern, content, re.IGNORECASE))
        for match in matches:
            # 위치 추정 (줄 번호)
            line_num = content[:match.start()].count("\n") + 1
            checks.append(QACheck(
                check_id=str(uuid.uuid4()),
                check_type="factual",
                passed=False,
                details=f"미완성 참조 '{label}'이(가) 발견되었습니다",
                location=f"{line_num}번째 줄",
            ))

    if not checks:
        checks.append(QACheck(
            check_id=str(uuid.uuid4()),
            check_type="factual",
            passed=True,
            details="깨진 참조 검사 통과",
            location="전체 문서",
        ))

    return checks


def run_qa(content: str) -> QAReport:
    """전체 QA 검사"""
    all_checks = []

    all_checks.extend(check_consistency(content))
    all_checks.extend(check_grammar_basics(content))
    all_checks.extend(check_broken_references(content))

    total = len(all_checks)
    passed = sum(1 for c in all_checks if c.passed)
    failed = total - passed

    # 심각한 이슈: factual 유형 실패
    critical = sum(1 for c in all_checks if not c.passed and c.check_type == "factual")

    pass_rate = passed / total if total > 0 else 1.0

    return QAReport(
        content_id=str(uuid.uuid4()),
        checks=all_checks,
        pass_rate=round(pass_rate, 4),
        critical_issues=critical,
    )
