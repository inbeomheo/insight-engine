"""
인용 아카이브 서비스 — 인용문을 체계적으로 저장/검색/관리
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class Citation:
    """인용문"""
    citation_id: str
    quote: str
    author: str
    source: str
    date: str = ""
    tags: list[str] = field(default_factory=list)
    context: str = ""
    verified: bool = False


@dataclass
class CitationArchive:
    """인용 아카이브"""
    archive_id: str
    citations: list[Citation] = field(default_factory=list)


def _create_archive(archive_id: str | None = None) -> CitationArchive:
    """빈 인용 아카이브 생성"""
    return CitationArchive(
        archive_id=archive_id or str(uuid.uuid4()),
        citations=[],
    )


def add_citation(
    archive: CitationArchive,
    quote: str,
    author: str,
    source: str,
    tags: list[str] | None = None,
    date: str = "",
    context: str = "",
) -> CitationArchive:
    """인용 추가 (중복 체크)

    동일한 quote + author 조합이 이미 존재하면 추가하지 않음.

    Args:
        archive: 대상 아카이브
        quote: 인용문
        author: 저자
        source: 출처
        tags: 태그 목록
        date: 날짜 문자열
        context: 인용 맥락

    Returns:
        업데이트된 아카이브
    """
    # 중복 체크 (quote + author 조합)
    quote_lower = quote.strip().lower()
    author_lower = author.strip().lower()
    for c in archive.citations:
        if c.quote.strip().lower() == quote_lower and c.author.strip().lower() == author_lower:
            return archive  # 중복 — 추가하지 않음

    citation = Citation(
        citation_id=str(uuid.uuid4()),
        quote=quote.strip(),
        author=author.strip(),
        source=source.strip(),
        date=date,
        tags=tags or [],
        context=context,
        verified=False,
    )
    archive.citations.append(citation)
    return archive


def search_citations(
    archive: CitationArchive, query: str, by_field: str = "quote"
) -> list[Citation]:
    """인용 검색

    Args:
        archive: 대상 아카이브
        query: 검색어
        by_field: 검색 필드 (quote/author/tag)

    Returns:
        매칭된 인용 목록
    """
    if not query.strip():
        return []

    query_lower = query.lower()
    results: list[Citation] = []

    for c in archive.citations:
        if by_field == "quote":
            if query_lower in c.quote.lower():
                results.append(c)
        elif by_field == "author":
            if query_lower in c.author.lower():
                results.append(c)
        elif by_field == "tag":
            for tag in c.tags:
                if query_lower in tag.lower():
                    results.append(c)
                    break

    return results


def get_by_author(archive: CitationArchive, author: str) -> list[Citation]:
    """저자별 인용 조회

    Args:
        archive: 대상 아카이브
        author: 저자 이름

    Returns:
        해당 저자의 인용 목록
    """
    return search_citations(archive, author, by_field="author")


def verify_citation(
    archive: CitationArchive, citation_id: str
) -> CitationArchive:
    """인용 검증 완료 표시

    Args:
        archive: 대상 아카이브
        citation_id: 검증할 인용 ID

    Returns:
        업데이트된 아카이브

    Raises:
        ValueError: 인용을 찾을 수 없을 때
    """
    for c in archive.citations:
        if c.citation_id == citation_id:
            c.verified = True
            return archive

    raise ValueError(f"인용을 찾을 수 없습니다: {citation_id}")


def export_bibliography(
    archive: CitationArchive, format: str = "apa"
) -> str:
    """참고문헌 내보내기

    Args:
        archive: 대상 아카이브
        format: 스타일 (apa/mla)

    Returns:
        포맷된 참고문헌 문자열
    """
    if not archive.citations:
        return ""

    lines: list[str] = []

    for c in archive.citations:
        if format.lower() == "apa":
            # APA 스타일 시뮬레이션: 저자. (날짜). 인용문. 출처.
            date_part = f"({c.date})" if c.date else "(n.d.)"
            lines.append(f"{c.author}. {date_part}. \"{c.quote}\". {c.source}.")
        elif format.lower() == "mla":
            # MLA 스타일 시뮬레이션: 저자. "인용문." 출처, 날짜.
            date_part = f", {c.date}" if c.date else ""
            lines.append(f"{c.author}. \"{c.quote}.\" {c.source}{date_part}.")
        else:
            lines.append(f"{c.author} - \"{c.quote}\" ({c.source})")

    return "\n".join(lines)
