"""
키워드 갭 분석 서비스

경쟁 콘텐츠 키워드 vs 내 콘텐츠 키워드를 비교하여
누락 키워드 + 추가 추천을 제공합니다.
웹 스크래핑으로 경쟁 콘텐츠를 가져옵니다.
"""
import re
import logging
from collections import Counter
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# 불용어 (분석에서 제외)
_STOPWORDS = {
    '그', '이', '저', '것', '수', '등', '및', '더', '또', '를', '을', '에', '의', '가',
    '은', '는', '로', '으로', '와', '과', '에서', '까지', '부터', '하는', '한', '할',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'and', 'or', 'but', 'in',
    'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'it', 'this',
    'that', 'not', 'no', 'so', 'if', 'as',
}


def _extract_keywords(text: str, top_n: int = 30) -> List[str]:
    """텍스트에서 상위 키워드를 추출합니다."""
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text.lower())
    filtered = [w for w in words if w not in _STOPWORDS]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(top_n)]


def _fetch_competitor_text(url: str) -> str:
    """URL에서 경쟁 콘텐츠 텍스트를 가져옵니다."""
    try:
        from services.web_scraper_service import scrape_url
        result = scrape_url(url)
        return result.get('content', '') if result else ''
    except Exception as e:
        logger.warning(f"경쟁 URL 스크래핑 실패 ({url}): {e}")
        return ''


def analyze_keyword_gap(
    content: str,
    competitor_urls: List[str],
) -> Dict[str, Any]:
    """내 콘텐츠와 경쟁 콘텐츠의 키워드 갭을 분석합니다.

    Args:
        content: 내 콘텐츠 텍스트
        competitor_urls: 경쟁 콘텐츠 URL 리스트

    Returns:
        {
            "my_keywords": list,        # 내 키워드 목록
            "competitor_keywords": list, # 경쟁 키워드 통합 목록
            "missing_keywords": list,    # 내가 빠뜨린 키워드
            "unique_keywords": list,     # 내만의 차별 키워드
            "common_keywords": list,     # 공통 키워드
        }
    """
    if not content:
        return {
            'my_keywords': [],
            'competitor_keywords': [],
            'missing_keywords': [],
            'unique_keywords': [],
            'common_keywords': [],
        }

    my_keywords = set(_extract_keywords(content))

    # 경쟁 콘텐츠 키워드 수집
    competitor_all = Counter()
    for url in (competitor_urls or []):
        text = _fetch_competitor_text(url)
        if text:
            words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text.lower())
            filtered = [w for w in words if w not in _STOPWORDS]
            competitor_all.update(filtered)

    # 경쟁 상위 키워드
    competitor_keywords = set(
        word for word, _ in competitor_all.most_common(50)
    )

    missing = competitor_keywords - my_keywords
    unique = my_keywords - competitor_keywords
    common = my_keywords & competitor_keywords

    # 누락 키워드: 경쟁에서 빈도 높은 순서대로 정렬
    missing_sorted = sorted(missing, key=lambda w: competitor_all.get(w, 0), reverse=True)

    return {
        'my_keywords': sorted(my_keywords),
        'competitor_keywords': sorted(competitor_keywords),
        'missing_keywords': missing_sorted[:20],
        'unique_keywords': sorted(unique)[:20],
        'common_keywords': sorted(common),
    }
