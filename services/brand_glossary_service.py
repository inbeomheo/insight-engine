"""
브랜드 용어집 서비스.

브랜드 고유 용어를 관리하고 콘텐츠에서 금지 표현 사용을 탐지한다.
"""

from dataclasses import dataclass, field
import uuid


@dataclass
class GlossaryTerm:
    """용어집 항목"""
    term_id: str = ""
    term: str = ""
    definition: str = ""
    usage_example: str = ""
    do_not_use: list = field(default_factory=list)  # 사용 금지 표현


@dataclass
class Glossary:
    """용어집"""
    glossary_id: str = ""
    terms: list = field(default_factory=list)


def add_term(
    glossary: Glossary,
    term: str,
    definition: str,
    example: str = "",
    do_not_use: list = None
) -> Glossary:
    """용어 추가"""
    new_term = GlossaryTerm(
        term_id=str(uuid.uuid4()),
        term=term,
        definition=definition,
        usage_example=example,
        do_not_use=do_not_use or [],
    )

    new_terms = list(glossary.terms) + [new_term]
    return Glossary(
        glossary_id=glossary.glossary_id,
        terms=new_terms,
    )


def search_term(glossary: Glossary, query: str) -> list:
    """
    용어 검색.

    용어명, 정의, 사용 예시에서 대소문자 무시 검색.
    """
    query_lower = query.lower()
    results = []

    for term in glossary.terms:
        if (
            query_lower in term.term.lower()
            or query_lower in term.definition.lower()
            or query_lower in term.usage_example.lower()
        ):
            results.append(term)

    return results


def check_content(glossary: Glossary, content: str) -> list:
    """
    콘텐츠에서 금지 표현 사용 탐지.

    각 용어의 do_not_use 목록에 있는 표현이 콘텐츠에 있는지 검사한다.
    """
    violations = []
    content_lower = content.lower()

    for term in glossary.terms:
        for forbidden in term.do_not_use:
            if forbidden.lower() in content_lower:
                violations.append({
                    "term": term.term,
                    "forbidden_expression": forbidden,
                    "suggestion": f"'{forbidden}' 대신 '{term.term}'을(를) 사용하세요",
                    "definition": term.definition,
                })

    return violations


def export_glossary(glossary: Glossary) -> str:
    """마크다운 형식으로 용어집 내보내기"""
    lines = ["# 브랜드 용어집", ""]

    for term in glossary.terms:
        lines.append(f"## {term.term}")
        lines.append(f"**정의**: {term.definition}")
        if term.usage_example:
            lines.append(f"**사용 예시**: {term.usage_example}")
        if term.do_not_use:
            forbidden = ", ".join(term.do_not_use)
            lines.append(f"**사용 금지**: {forbidden}")
        lines.append("")

    return "\n".join(lines)
