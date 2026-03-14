"""
GEO/SEO JSON-LD 구조화 데이터 생성 서비스

VideoObject, FAQPage, Article 스키마를 생성하여
AI 검색 엔진 최적화(GEO)를 지원합니다.
"""

import re
from datetime import datetime, timezone


def _get_video_id(video_url: str) -> str | None:
    """YouTube URL에서 video_id를 추출합니다."""
    if not video_url:
        return None
    patterns = [
        r'(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})',
    ]
    for pattern in patterns:
        m = re.search(pattern, video_url)
        if m:
            return m.group(1)
    return None


def generate_video_object_schema(video_url: str, title: str, description: str = '') -> dict:
    """VideoObject JSON-LD 스키마를 생성합니다.

    Args:
        video_url: YouTube 영상 URL
        title: 영상 제목
        description: 영상 설명 (옵션)

    Returns:
        dict: JSON-LD VideoObject 스키마
    """
    video_id = _get_video_id(video_url)
    thumbnail_url = (
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
        if video_id else ''
    )
    content_url = (
        f"https://www.youtube.com/watch?v={video_id}"
        if video_id else video_url or ''
    )

    schema: dict = {
        "@context": "https://schema.org",
        "@type": "VideoObject",
        "name": title or '',
        "description": description[:500] if description else '',
        "contentUrl": content_url,
        "uploadDate": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if thumbnail_url:
        schema["thumbnailUrl"] = thumbnail_url

    return schema


def generate_faq_page_schema(faq_pairs: list[dict]) -> dict:
    """FAQPage JSON-LD 스키마를 생성합니다.

    Args:
        faq_pairs: [{"question": "...", "answer": "..."}, ...] 형식 리스트

    Returns:
        dict: JSON-LD FAQPage 스키마
    """
    entities = []
    for item in faq_pairs:
        q = (item.get('question') or '').strip()
        a = (item.get('answer') or '').strip()
        if q and a:
            entities.append({
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": a,
                },
            })

    return {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": entities,
    }


def generate_article_schema(title: str, description: str = '', keywords: list[str] | None = None) -> dict:
    """Article JSON-LD 스키마를 생성합니다.

    Args:
        title: 기사 제목
        description: 기사 설명 (옵션)
        keywords: 키워드 리스트 (옵션)

    Returns:
        dict: JSON-LD Article 스키마
    """
    schema: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": (title or '')[:110],  # 구글 권장 최대 110자
        "description": (description or '')[:300],
        "datePublished": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }
    if keywords:
        schema["keywords"] = keywords[:15]  # 키워드 최대 15개

    return schema


def generate_all_schemas(
    video_url: str,
    title: str,
    content: str,
    faq_pairs: list[dict],
    keywords: list[str] | None = None,
    description: str = '',
) -> list[dict]:
    """모든 JSON-LD 스키마를 생성하여 리스트로 반환합니다.

    Args:
        video_url: YouTube 영상 URL
        title: 콘텐츠 제목
        content: 생성된 마크다운 본문 (설명 자동 추출용)
        faq_pairs: FAQ Q&A 쌍 리스트
        keywords: 키워드 리스트
        description: 명시적 설명 (없으면 content 첫 문장에서 추출)

    Returns:
        list[dict]: [VideoObject, FAQPage, Article] 스키마 리스트
    """
    # 설명이 없으면 본문 첫 비빈 줄에서 추출
    if not description and content:
        for line in content.split('\n'):
            clean = line.strip().lstrip('#>-* ')
            if clean and len(clean) > 20:
                description = clean[:300]
                break

    schemas = []

    # VideoObject (YouTube URL이 있을 때만 추가)
    if video_url:
        schemas.append(generate_video_object_schema(video_url, title, description))

    # FAQPage (FAQ가 있을 때만 추가)
    if faq_pairs:
        faq_schema = generate_faq_page_schema(faq_pairs)
        if faq_schema.get('mainEntity'):
            schemas.append(faq_schema)

    # Article
    schemas.append(generate_article_schema(title, description, keywords))

    return schemas
