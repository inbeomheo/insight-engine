"""
arXiv 논문 추출 서비스

arXiv API(http://export.arxiv.org/api/query)를 사용하여
논문 메타데이터와 초록을 가져옵니다.
추가 패키지 없이 requests + xml.etree.ElementTree 사용.
"""
from __future__ import annotations

import re
from typing import Dict, List
from xml.etree import ElementTree

import requests

# arXiv Atom 피드 네임스페이스
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"

_API_BASE = "http://export.arxiv.org/api/query"
_REQUEST_TIMEOUT = 15  # 초


def _ns(tag: str) -> str:
    """Atom 네임스페이스 접두사를 반환합니다."""
    return f"{{{_ATOM_NS}}}{tag}"


def _parse_entry(entry: ElementTree.Element) -> Dict:
    """Atom <entry> 요소를 딕셔너리로 변환합니다."""
    def text(tag: str) -> str:
        el = entry.find(_ns(tag))
        return (el.text or "").strip() if el is not None else ""

    # 논문 ID (URL 형식에서 순수 ID 추출)
    id_raw = text("id")
    arxiv_id = re.sub(r".*arxiv\.org/abs/", "", id_raw).strip()

    # 저자 목록
    authors = [
        (a.find(_ns("name")).text or "").strip()
        for a in entry.findall(_ns("author"))
        if a.find(_ns("name")) is not None
    ]

    # 초록 정리
    abstract = re.sub(r"\s+", " ", text("summary")).strip()

    # PDF 링크
    pdf_url = ""
    for link in entry.findall(_ns("link")):
        if link.get("title") == "pdf":
            pdf_url = link.get("href", "")
            break

    title = re.sub(r"\s+", " ", text("title")).strip()
    published = text("published")  # ISO 8601

    # 카테고리
    categories = [
        c.get("term", "")
        for c in entry.findall(f"{{{_ARXIV_NS}}}primary_category")
    ]
    cat_el = entry.find(f"{{{_ARXIV_NS}}}primary_category")
    primary_category = cat_el.get("term", "") if cat_el is not None else ""

    # 콘텐츠: 제목 + 초록 (AI 생성 입력용)
    content = f"제목: {title}\n\n초록:\n{abstract}"
    if authors:
        content = f"저자: {', '.join(authors)}\n" + content
    if published:
        content += f"\n\n발행일: {published[:10]}"
    if primary_category:
        content += f"\n분야: {primary_category}"

    return {
        "title": title,
        "content": content,
        "abstract": abstract,
        "authors": authors,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": pdf_url,
        "arxiv_id": arxiv_id,
        "published": published[:10] if published else "",
        "category": primary_category,
        "source_type": "arxiv",
    }


def fetch_paper(arxiv_id: str) -> Dict:
    """arXiv 논문 ID로 논문 메타데이터와 초록을 가져옵니다.

    Args:
        arxiv_id: arXiv 논문 ID (예: '2303.08774', 'cs.AI/0612069')

    Returns:
        {
            "title": str,
            "content": str,       # AI 생성 입력용 (제목+초록)
            "abstract": str,
            "authors": List[str],
            "url": str,
            "pdf_url": str,
            "arxiv_id": str,
            "published": str,     # YYYY-MM-DD
            "category": str,
            "source_type": "arxiv"
        }

    Raises:
        ValueError: 논문을 찾을 수 없는 경우
        requests.RequestException: 네트워크 오류
    """
    # URL에서 ID 추출 (arxiv.org/abs/xxxx 형식 지원)
    arxiv_id = re.sub(r".*arxiv\.org/abs/", "", arxiv_id).strip()
    arxiv_id = arxiv_id.rstrip("/")

    params = {"id_list": arxiv_id, "max_results": 1}
    resp = requests.get(_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    entries = root.findall(_ns("entry"))

    if not entries:
        raise ValueError(f"arXiv 논문을 찾을 수 없습니다: {arxiv_id}")

    # 첫 번째 엔트리 반환
    return _parse_entry(entries[0])


def search_papers(query: str, max_results: int = 5) -> List[Dict]:
    """arXiv에서 논문을 검색합니다.

    Args:
        query: 검색어 (예: 'machine learning transformer')
        max_results: 최대 결과 수 (기본 5, 최대 20)

    Returns:
        논문 딕셔너리 목록

    Raises:
        requests.RequestException: 네트워크 오류
    """
    max_results = min(max_results, 20)
    params = {
        "search_query": f"all:{query}",
        "start": 0,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending",
    }

    resp = requests.get(_API_BASE, params=params, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()

    root = ElementTree.fromstring(resp.content)
    entries = root.findall(_ns("entry"))

    return [_parse_entry(e) for e in entries]
