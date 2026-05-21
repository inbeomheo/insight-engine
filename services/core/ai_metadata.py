"""AI 생성 콘텐츠에서 SEO/GEO/FAQ/CTA 메타데이터를 추출하는 정규식 헬퍼.

ai_service.py에서 분리됨. 모든 함수는 마크다운 본문을 입력으로 받아 dict 또는
None을 반환하는 순수 함수다 (AI API 호출 없음).
"""
from __future__ import annotations

import re
from typing import Any, Dict, Optional


# ── SEO 메타 정규식 ───────────────────────────────────────
_SEO_META_RE = re.compile(r'\*\*메타 설명\*\*\s*\|?\s*(.+?)(?:\s*\||\n)')
_SEO_KW_RE = re.compile(r'\*\*타겟 키워드\*\*\s*\|?\s*(.+?)(?:\s*\||\n)')
_SEO_KW_MAIN_RE = re.compile(r'메인\s*[:：]\s*')
_SEO_KW_RELATED_RE = re.compile(r'연관\s*[:：]\s*')
_SEO_SLUG_RE = re.compile(r'\*\*추천 URL\*\*\s*\|?\s*(/?.+?)(?:\s*\||\n)')
_SEO_TAG_RE = re.compile(r'(?:\*\*태그\*\*|#태그|태그\s*[:：])\s*(.+?)(?:\n|$)')
_SEO_HASHTAG_RE = re.compile(r'#([\w가-힣]+)')

# ── GEO 메타 정규식 ───────────────────────────────────────
_GEO_FACTS_RE = re.compile(r'[-•✓]\s*✓?\s*(.+?)(?:\n|$)')
_GEO_STRUCT_RE = re.compile(r'###\s*구조화\s*데이터\s*\n((?:\|.+\|\n?)+)')
_GEO_ENTITY_RE = re.compile(r'###\s*엔티티\s*태그\s*\n(.+?)(?:\n\n|\n---|\n###|$)', re.DOTALL)
_GEO_BACKTICK_RE = re.compile(r'`([^`]+)`')
_GEO_DEF_RE = re.compile(r'###\s*한 줄 정의\s*\n>\s*(.+?)(?:\n|$)')
_GEO_QA_RE = re.compile(r'A\.\s*(.+?)(?:\n|$)')

# ── CTA 정규식 ───────────────────────────────────────────
_CTA_PRIMARY_RE = re.compile(r'\*\*CTA_PRIMARY\*\*\s*[:：]\s*(.+?)(?:\n|$)')
_CTA_SECONDARY_RE = re.compile(r'\*\*CTA_SECONDARY\*\*\s*[:：]\s*(.+?)(?:\n|$)')

# ── FAQ 정규식 ───────────────────────────────────────────
_FAQ_QA_RE = re.compile(
    r'\*\*Q\.\s*(.+?)\*\*\s*\n\s*A\.\s*(.+?)(?=\n\s*\*\*Q\.|\n---|\n##|\Z)',
    re.DOTALL
)


def extract_seo_metadata(content: str) -> Optional[Dict[str, Any]]:
    """blog_seo 스타일 콘텐츠에서 SEO 메타데이터를 정규식으로 추출합니다.

    Args:
        content: 마크다운 본문

    Returns:
        dict 또는 None: {meta_description, keywords, slug, tags}
    """
    if not content:
        return None

    seo = {}

    # 메타 설명
    meta_match = _SEO_META_RE.search(content)
    if meta_match:
        seo['meta_description'] = meta_match.group(1).strip()

    # 타겟 키워드
    kw_match = _SEO_KW_RE.search(content)
    if kw_match:
        raw = kw_match.group(1).strip()
        # "메인: X, 연관: Y, Z" 또는 "X, Y, Z" 형식 파싱
        raw = _SEO_KW_MAIN_RE.sub('', raw)
        raw = _SEO_KW_RELATED_RE.sub('', raw)
        keywords = [k.strip().strip('[]') for k in raw.split(',') if k.strip()]
        seo['keywords'] = keywords

    # 추천 URL 슬러그
    slug_match = _SEO_SLUG_RE.search(content)
    if slug_match:
        seo['slug'] = slug_match.group(1).strip().strip('/')

    # 태그 (#태그 형식)
    tag_match = _SEO_TAG_RE.search(content)
    if tag_match:
        raw_tags = tag_match.group(1).strip()
        tags = _SEO_HASHTAG_RE.findall(raw_tags)
        if tags:
            seo['tags'] = tags

    # 최소 1개 필드 파싱 성공 시 반환
    return seo if seo else None


def extract_geo_metadata(content: str) -> Optional[Dict[str, Any]]:
    """geo_seo 스타일 콘텐츠에서 GEO 메타데이터를 정규식으로 추출합니다.

    Args:
        content: 마크다운 본문

    Returns:
        dict 또는 None: {citations, structured_data, entity_tags, key_facts}
    """
    if not content:
        return None

    geo = {}

    # 주요 팩트 (✓ 로 시작하는 줄)
    facts = _GEO_FACTS_RE.findall(content)
    if facts:
        geo['key_facts'] = [f.strip() for f in facts if f.strip()]

    # 구조화 데이터 (마크다운 테이블에서 추출 — "구조화 데이터" 섹션)
    table_section = _GEO_STRUCT_RE.search(content)
    if table_section:
        rows = table_section.group(1).strip().split('\n')
        structured = {}
        for row in rows:
            cells = [c.strip().strip('*') for c in row.split('|') if c.strip()]
            if len(cells) >= 2 and '---' not in cells[0]:
                key = cells[0].strip()
                val = cells[1].strip()
                if key and val and key != '항목' and key != '내용':
                    structured[key] = val
        if structured:
            geo['structured_data'] = structured

    # 엔티티 태그 (백틱으로 감싼 태그들 — "엔티티 태그" 섹션)
    tag_section = _GEO_ENTITY_RE.search(content)
    if tag_section:
        raw_tags = tag_section.group(1).strip()
        tags = _GEO_BACKTICK_RE.findall(raw_tags)
        if tags:
            geo['entity_tags'] = [t.strip() for t in tags]

    # 인용문 (핵심 요약 + Q&A 답변에서 추출 — 첫 문장들)
    citations = []

    # 한 줄 정의
    definition = _GEO_DEF_RE.search(content)
    if definition:
        citations.append(definition.group(1).strip())

    # Q&A 답변의 첫 문장
    qa_answers = _GEO_QA_RE.findall(content)
    for ans in qa_answers:
        text = ans.strip()
        if text and len(text) > 10:
            citations.append(text)

    if citations:
        geo['citations'] = citations

    # 최소 1개 필드 파싱 성공 시 반환
    return geo if geo else None


def extract_faq_schema(content: str) -> Optional[Dict[str, Any]]:
    """마크다운 본문에서 FAQ Q&A를 파싱하여 JSON-LD FAQPage 스키마를 반환합니다.

    "### 자주 묻는 질문" 섹션의 **Q. ...?** / A. ... 패턴을 인식합니다.

    Args:
        content: 마크다운 본문 문자열

    Returns:
        dict 또는 None: JSON-LD FAQPage 스키마 dict, Q&A가 없으면 None
    """
    if not content:
        return None

    # Q&A 패턴 추출: **Q. 질문?** 다음 줄에 A. 답변
    matches = _FAQ_QA_RE.findall(content)

    if not matches:
        return None

    entities = []
    for question, answer in matches:
        q_text = question.strip()
        a_text = ' '.join(answer.strip().split())  # 줄바꿈 정규화
        if q_text and a_text:
            entities.append({
                "@type": "Question",
                "name": q_text,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a_text
                }
            })

    if not entities:
        return None

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities
    }


def extract_cta(content: str) -> Optional[Dict[str, str]]:
    """geo_seo 스타일 콘텐츠에서 CTA 문구를 추출합니다.

    **CTA_PRIMARY**: ... / **CTA_SECONDARY**: ... 패턴을 인식합니다.

    Args:
        content: 마크다운 본문 문자열

    Returns:
        dict 또는 None: {"primary": "...", "secondary": "..."} 또는 None
    """
    if not content:
        return None

    cta = {}

    primary_match = _CTA_PRIMARY_RE.search(content)
    if primary_match:
        cta['primary'] = primary_match.group(1).strip()

    secondary_match = _CTA_SECONDARY_RE.search(content)
    if secondary_match:
        cta['secondary'] = secondary_match.group(1).strip()

    return cta if cta else None
