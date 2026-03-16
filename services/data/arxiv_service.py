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
import logging

logger = logging.getLogger(__name__)

# arXiv Atom 피드 네임스페이스
_ATOM_NS = "http://www.w3.org/2005/Atom"
_ARXIV_NS = "http://arxiv.org/schemas/atom"

_API_BASE = "http://export.arxiv.org/api/query"
_REQUEST_TIMEOUT = 15  # 초


def _ns(tag: str) -> str:
    """Atom 네임스페이스 접두사를 반환합니다."""
    return f"{{{_ATOM_NS}}}{tag}"


def _build_content_text(title: str, abstract: str, authors: List[str],
                        published: str, primary_category: str,
                        all_categories: List[str]) -> str:
    """AI 생성 입력용 콘텐츠 텍스트를 조합합니다."""
    content = f"제목: {title}\n\n초록:\n{abstract}"
    if authors:
        content = f"저자: {', '.join(authors)}\n" + content
    if published:
        content += f"\n\n발행일: {published[:10]}"
    if primary_category:
        content += f"\n분야: {primary_category}"
    if all_categories:
        content += f"\n카테고리: {', '.join(all_categories)}"
    return content


def _parse_entry(entry: ElementTree.Element) -> Dict:
    """Atom <entry> 요소를 딕셔너리로 변환합니다."""
    def text(tag: str) -> str:
        el = entry.find(_ns(tag))
        return (el.text or "").strip() if el is not None else ""

    arxiv_id = re.sub(r".*arxiv\.org/abs/", "", text("id")).strip()

    authors = [
        (a.find(_ns("name")).text or "").strip()
        for a in entry.findall(_ns("author"))
        if a.find(_ns("name")) is not None
    ]

    abstract = re.sub(r"\s+", " ", text("summary")).strip()

    pdf_url = ""
    for link in entry.findall(_ns("link")):
        if link.get("title") == "pdf":
            pdf_url = link.get("href", "")
            break

    title = re.sub(r"\s+", " ", text("title")).strip()
    published = text("published")

    cat_el = entry.find(f"{{{_ARXIV_NS}}}primary_category")
    primary_category = cat_el.get("term", "") if cat_el is not None else ""

    all_categories = [
        c.get("term", "")
        for c in entry.findall(_ns("category"))
        if c.get("term")
    ]

    return {
        "title": title,
        "content": _build_content_text(
            title, abstract, authors, published, primary_category, all_categories
        ),
        "abstract": abstract,
        "authors": authors,
        "url": f"https://arxiv.org/abs/{arxiv_id}",
        "pdf_url": pdf_url,
        "arxiv_id": arxiv_id,
        "published": published[:10] if published else "",
        "category": primary_category,
        "categories": all_categories,
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
    try:
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
    except (ValueError, requests.RequestException):
        raise
    except Exception as e:
        logger.error("fetch_paper 실패: %s", e, exc_info=True)
        return {}


def fetch_paper_fulltext(arxiv_id: str) -> Dict:
    """논문 메타데이터 + PDF 전문 텍스트를 가져옵니다.

    PDF에서 전문 텍스트 추출을 시도하고, 실패 시 초록만 반환합니다.

    Args:
        arxiv_id: arXiv 논문 ID

    Returns:
        fetch_paper() 결과 + fulltext 필드 (추출 성공 시)
    """
    paper = fetch_paper(arxiv_id)

    if not paper.get('pdf_url'):
        return paper

    try:
        pdf_resp = requests.get(paper['pdf_url'], timeout=30)
        pdf_resp.raise_for_status()

        import io
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=pdf_resp.content, filetype="pdf")
            pages_text = []
            for page in doc:
                pages_text.append(page.get_text())
            doc.close()
            fulltext = "\n\n".join(pages_text).strip()
        except ImportError:
            # PyMuPDF 없으면 pdfplumber 시도
            try:
                import pdfplumber
                pdf_file = io.BytesIO(pdf_resp.content)
                with pdfplumber.open(pdf_file) as pdf:
                    pages_text = [p.extract_text() or "" for p in pdf.pages]
                fulltext = "\n\n".join(pages_text).strip()
            except ImportError:
                # PDF 라이브러리 없음 — 초록만 사용
                return paper

        if fulltext and len(fulltext) > len(paper['abstract']):
            # 전문이 초록보다 길면 콘텐츠에 포함
            paper['fulltext'] = fulltext
            # content 필드를 전문 기반으로 업데이트 (너무 길면 앞부분만)
            max_chars = 15000
            trimmed = fulltext[:max_chars]
            if len(fulltext) > max_chars:
                trimmed += f"\n\n... (총 {len(fulltext):,}자 중 앞부분만 포함)"
            paper['content'] = (
                f"저자: {', '.join(paper['authors'])}\n"
                f"제목: {paper['title']}\n"
                f"발행일: {paper['published']}\n"
                f"분야: {paper['category']}\n\n"
                f"전문:\n{trimmed}"
            )

    except Exception:
        # PDF 다운로드/파싱 실패 — 초록만 사용
        pass

    return paper


def search_papers(query: str, max_results: int = 5) -> Dict:
    """arXiv에서 논문을 검색합니다.

    Args:
        query: 검색어 (예: 'machine learning transformer')
        max_results: 최대 결과 수 (기본 5, 최대 20)

    Returns:
        {"papers": List[Dict], "total_results": int}

    Raises:
        requests.RequestException: 네트워크 오류
    """
    try:
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

        # OpenSearch totalResults 추출
        _OPENSEARCH_NS = "http://a9.com/-/spec/opensearch/1.1/"
        total_el = root.find(f"{{{_OPENSEARCH_NS}}}totalResults")
        total_results = int(total_el.text) if total_el is not None and total_el.text else len(entries)

        papers = [_parse_entry(e) for e in entries]
        return {"papers": papers, "total_results": total_results}
    except requests.RequestException:
        raise
    except Exception as e:
        logger.error("search_papers 실패: %s", e, exc_info=True)
        return {"papers": [], "total_results": 0}
