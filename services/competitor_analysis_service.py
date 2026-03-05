"""
경쟁 콘텐츠 분석 서비스

키워드로 웹 검색 후 상위 결과를 분석하여 차별화 포인트를 추천합니다.
"""
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


def _analyze_content_structure(text: str) -> Dict:
    """콘텐츠 구조를 분석합니다."""
    lines = text.split('\n')
    headings = [l for l in lines if l.strip().startswith('#')]
    paragraphs = [l for l in lines if l.strip() and not l.strip().startswith('#')]
    word_count = len(text.split())
    char_count = len(text)

    # 리스트/불릿 포인트 수
    list_items = len([l for l in lines if re.match(r'^\s*[-*•]\s', l.strip())])

    return {
        "char_count": char_count,
        "word_count": word_count,
        "heading_count": len(headings),
        "paragraph_count": len(paragraphs),
        "list_items": list_items,
        "has_images": bool(re.search(r'!\[', text) or re.search(r'<img', text)),
    }


def _extract_keywords_simple(text: str, top_n: int = 10) -> List[str]:
    """단순 빈도 기반 키워드 추출 (불용어 제거)."""
    from services.auto_tag_service import _tokenize, _compute_tfidf
    tokens = _tokenize(text)
    return _compute_tfidf(tokens, top_n=top_n)


def analyze_competitors(
    keyword: str,
    my_content: Optional[str] = None,
) -> Dict:
    """키워드로 경쟁 콘텐츠를 분석합니다.

    Args:
        keyword: 분석할 키워드/주제
        my_content: 내 콘텐츠 (비교 분석용, 선택)

    Returns:
        dict: {
            keyword, competitors: [{title, url, structure, keywords}],
            avg_stats, my_analysis, differentiation_tips
        }

    Raises:
        ValueError: 키워드가 비어있을 때
    """
    if not keyword or not keyword.strip():
        raise ValueError("분석할 키워드를 입력해주세요.")

    from services.web_scraper_service import scrape_webpage

    # 웹 검색으로 상위 URL 수집
    search_urls = _search_urls(keyword)

    competitors = []
    for url_info in search_urls[:5]:
        try:
            scraped = scrape_webpage(url_info['url'])
            content = scraped.get('content', '')
            if not content or len(content) < 50:
                continue

            structure = _analyze_content_structure(content)
            keywords = _extract_keywords_simple(content, top_n=8)

            competitors.append({
                "title": scraped.get('title', url_info.get('title', '')),
                "url": url_info['url'],
                "structure": structure,
                "keywords": keywords,
            })
        except Exception as e:
            logger.warning(f"경쟁 URL 분석 실패: {url_info['url']} - {e}")
            continue

    # 평균 통계 계산
    avg_stats = _calculate_avg_stats(competitors)

    # 내 콘텐츠 분석
    my_analysis = None
    if my_content and my_content.strip():
        my_analysis = {
            "structure": _analyze_content_structure(my_content),
            "keywords": _extract_keywords_simple(my_content, top_n=8),
        }

    # 차별화 포인트 생성
    tips = _generate_differentiation_tips(competitors, my_analysis, avg_stats)

    return {
        "keyword": keyword,
        "competitors": competitors,
        "competitor_count": len(competitors),
        "avg_stats": avg_stats,
        "my_analysis": my_analysis,
        "differentiation_tips": tips,
    }


def _search_urls(keyword: str) -> List[Dict]:
    """키워드로 관련 URL을 검색합니다.

    웹 검색 서비스가 있으면 활용, 없으면 빈 목록 반환.
    """
    try:
        from services.web_research_service import search_web
        results = search_web(keyword, max_results=5)
        return [{"url": r.get("url", ""), "title": r.get("title", "")} for r in results if r.get("url")]
    except (ImportError, Exception) as e:
        logger.info(f"웹 검색 폴백: {e}")
        return []


def _calculate_avg_stats(competitors: List[Dict]) -> Dict:
    """경쟁 콘텐츠의 평균 통계를 계산합니다."""
    if not competitors:
        return {
            "avg_char_count": 0,
            "avg_heading_count": 0,
            "avg_list_items": 0,
        }

    total_chars = sum(c['structure']['char_count'] for c in competitors)
    total_headings = sum(c['structure']['heading_count'] for c in competitors)
    total_lists = sum(c['structure']['list_items'] for c in competitors)
    n = len(competitors)

    return {
        "avg_char_count": round(total_chars / n),
        "avg_heading_count": round(total_headings / n, 1),
        "avg_list_items": round(total_lists / n, 1),
    }


def _generate_differentiation_tips(
    competitors: List[Dict],
    my_analysis: Optional[Dict],
    avg_stats: Dict,
) -> List[str]:
    """차별화 포인트를 생성합니다."""
    tips = []

    if not competitors:
        tips.append("경쟁 콘텐츠를 찾지 못했습니다. 해당 주제에서 선점 기회가 있습니다.")
        return tips

    # 키워드 갭 분석
    all_competitor_keywords = set()
    for c in competitors:
        all_competitor_keywords.update(c.get('keywords', []))

    if my_analysis:
        my_keywords = set(my_analysis.get('keywords', []))
        missing = all_competitor_keywords - my_keywords
        if missing:
            tips.append(f"경쟁 콘텐츠에서 자주 등장하지만 내 콘텐츠에 없는 키워드: {', '.join(list(missing)[:5])}")

        my_struct = my_analysis.get('structure', {})
        if my_struct.get('char_count', 0) < avg_stats.get('avg_char_count', 0) * 0.7:
            tips.append("경쟁 콘텐츠 대비 글자 수가 부족합니다. 더 상세한 내용 추가를 권장합니다.")
        if my_struct.get('heading_count', 0) < avg_stats.get('avg_heading_count', 0):
            tips.append("경쟁 콘텐츠 대비 소제목이 적습니다. 구조를 더 세분화해보세요.")

    # 공통 키워드 분석
    if all_competitor_keywords:
        common = list(all_competitor_keywords)[:5]
        tips.append(f"경쟁 콘텐츠의 공통 키워드: {', '.join(common)}")

    if avg_stats.get('avg_char_count', 0) > 0:
        tips.append(f"경쟁 콘텐츠 평균 길이: 약 {avg_stats['avg_char_count']:,}자")

    return tips
