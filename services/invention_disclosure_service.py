"""
발명 공개서 서비스 — 발명 문서 구조화
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class InventionDisclosure:
    """발명 공개서"""
    disclosure_id: str
    title: str
    inventors: list[str]
    abstract: str
    background: str
    description: str
    claims: list[str]
    prior_art: list[str]
    filing_date: str


def create_disclosure(title: str, inventors: list[str], abstract: str,
                      description: str) -> InventionDisclosure:
    """발명 공개서 생성"""
    return InventionDisclosure(
        disclosure_id=str(uuid.uuid4())[:8],
        title=title,
        inventors=inventors,
        abstract=abstract,
        background='',
        description=description,
        claims=[],
        prior_art=[],
        filing_date=datetime.now().strftime('%Y-%m-%d')
    )


def add_claim(disclosure: InventionDisclosure, claim: str) -> InventionDisclosure:
    """청구항 추가"""
    new_claims = disclosure.claims + [claim]
    return InventionDisclosure(
        disclosure_id=disclosure.disclosure_id,
        title=disclosure.title,
        inventors=disclosure.inventors,
        abstract=disclosure.abstract,
        background=disclosure.background,
        description=disclosure.description,
        claims=new_claims,
        prior_art=disclosure.prior_art,
        filing_date=disclosure.filing_date
    )


def add_prior_art(disclosure: InventionDisclosure, reference: str) -> InventionDisclosure:
    """선행 기술 추가"""
    new_prior = disclosure.prior_art + [reference]
    return InventionDisclosure(
        disclosure_id=disclosure.disclosure_id,
        title=disclosure.title,
        inventors=disclosure.inventors,
        abstract=disclosure.abstract,
        background=disclosure.background,
        description=disclosure.description,
        claims=disclosure.claims,
        prior_art=new_prior,
        filing_date=disclosure.filing_date
    )


def validate_disclosure(disclosure: InventionDisclosure) -> list[str]:
    """필수 섹션 검증"""
    errors = []
    if not disclosure.title:
        errors.append('제목이 비어 있습니다.')
    if not disclosure.inventors:
        errors.append('발명자가 지정되지 않았습니다.')
    if not disclosure.abstract:
        errors.append('초록이 비어 있습니다.')
    if not disclosure.description:
        errors.append('설명이 비어 있습니다.')
    if not disclosure.claims:
        errors.append('청구항이 없습니다.')
    return errors


def export_disclosure(disclosure: InventionDisclosure) -> str:
    """텍스트 내보내기"""
    lines = [
        f"발명 공개서: {disclosure.title}",
        f"출원일: {disclosure.filing_date}",
        f"발명자: {', '.join(disclosure.inventors)}",
        "",
        f"[초록]",
        disclosure.abstract,
        "",
        f"[배경]",
        disclosure.background or '(미작성)',
        "",
        f"[설명]",
        disclosure.description,
        "",
        f"[청구항]",
    ]
    for i, claim in enumerate(disclosure.claims, 1):
        lines.append(f"  {i}. {claim}")
    lines.append("")
    lines.append("[선행 기술]")
    for ref in disclosure.prior_art:
        lines.append(f"  - {ref}")

    return '\n'.join(lines)
