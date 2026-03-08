"""
키워드 밀도 분석 서비스

콘텐츠에서 키워드 빈도, 밀도(%), 위치 분포를 분석하고
적정 범위(1~3%)를 기준으로 과다/부족을 판정합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 한국어 불용어
_STOPWORDS = {
    '이', '그', '저', '것', '수', '등', '및', '또', '더', '를', '을', '에', '의',
    '가', '는', '은', '로', '으로', '와', '과', '도', '만', '에서', '까지', '부터',
    '있다', '하다', '되다', '이다', '없다', '않다', '같다', '위해', '통해', '대한',
    '있습니다', '합니다', '입니다', '됩니다', '있는', '하는', '되는', '않는',
}

# 적정 밀도 범위
_OPTIMAL_MIN = 1.0  # %
_OPTIMAL_MAX = 3.0  # %
_WARNING_MAX = 5.0  # % 이상이면 키워드 스터핑 경고


def analyze_density(content: str, keywords: list = None) -> dict:
    """지정된 키워드의 밀도를 분석합니다.

    Args:
        content: 분석할 콘텐츠
        keywords: 분석할 키워드 목록

    Returns:
        {
            "keywords": [{"keyword": str, "count": int, "density": float,
                          "status": str, "positions": list}],
            "total_words": int,
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'keywords': [],
            'total_words': 0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    if not keywords:
        return {
            'keywords': [],
            'total_words': len(_tokenize(content)),
            'suggestions': ['분석할 키워드를 지정해 주세요.'],
        }

    words = _tokenize(content)
    total_words = len(words)
    if total_words == 0:
        return {
            'keywords': [],
            'total_words': 0,
            'suggestions': ['단어가 추출되지 않았습니다.'],
        }

    content_lower = content.lower()
    results = []
    suggestions = []

    for kw in keywords:
        if not kw or not kw.strip():
            continue
        kw_clean = kw.strip()
        kw_lower = kw_clean.lower()

        # 키워드 등장 횟수 및 위치
        positions = []
        for match in re.finditer(re.escape(kw_lower), content_lower):
            # 위치를 전체 텍스트 비율로 계산
            pos_ratio = match.start() / max(len(content), 1)
            if pos_ratio <= 0.25:
                positions.append('top')
            elif pos_ratio >= 0.75:
                positions.append('bottom')
            else:
                positions.append('middle')

        count = len(positions)
        density = round((count / total_words) * 100, 2)

        if density < _OPTIMAL_MIN and count > 0:
            status = 'low'
            suggestions.append(f'"{kw_clean}" 밀도({density}%)가 낮습니다. {_OPTIMAL_MIN}~{_OPTIMAL_MAX}% 범위를 목표로 하세요.')
        elif density > _WARNING_MAX:
            status = 'stuffing'
            suggestions.append(f'"{kw_clean}" 밀도({density}%)가 과다합니다. 키워드 스터핑으로 판정될 수 있습니다.')
        elif density > _OPTIMAL_MAX:
            status = 'high'
            suggestions.append(f'"{kw_clean}" 밀도({density}%)가 다소 높습니다. 자연스럽게 줄여 보세요.')
        elif count == 0:
            status = 'missing'
            suggestions.append(f'"{kw_clean}"이(가) 콘텐츠에 없습니다. 자연스럽게 포함시켜 보세요.')
        else:
            status = 'optimal'

        results.append({
            'keyword': kw_clean,
            'count': count,
            'density': density,
            'status': status,
            'positions': positions,
        })

    if not suggestions:
        suggestions.append('모든 키워드가 적정 밀도 범위에 있습니다.')

    return {
        'keywords': results,
        'total_words': total_words,
        'suggestions': suggestions,
    }


def get_density_report(content: str, top_n: int = 10) -> dict:
    """콘텐츠에서 자동으로 상위 키워드를 추출하고 밀도를 분석합니다.

    Args:
        content: 분석할 콘텐츠
        top_n: 상위 N개 키워드

    Returns:
        {
            "top_keywords": [{"keyword": str, "count": int, "density": float, "status": str}],
            "total_words": int,
            "unique_words": int,
            "lexical_diversity": float,
            "suggestions": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'top_keywords': [],
            'total_words': 0,
            'unique_words': 0,
            'lexical_diversity': 0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    words = _tokenize(content)
    total_words = len(words)

    # 불용어 제외 빈도 계산
    freq = {}
    for w in words:
        if w not in _STOPWORDS and len(w) >= 2:
            freq[w] = freq.get(w, 0) + 1

    unique_words = len(freq)
    lexical_diversity = round(unique_words / max(total_words, 1), 3)

    # 상위 키워드
    sorted_kws = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:top_n]

    top_keywords = []
    for kw, count in sorted_kws:
        density = round((count / total_words) * 100, 2)
        if density > _WARNING_MAX:
            status = 'stuffing'
        elif density > _OPTIMAL_MAX:
            status = 'high'
        elif density >= _OPTIMAL_MIN:
            status = 'optimal'
        else:
            status = 'low'

        top_keywords.append({
            'keyword': kw,
            'count': count,
            'density': density,
            'status': status,
        })

    suggestions = []
    stuffing = [k for k in top_keywords if k['status'] == 'stuffing']
    if stuffing:
        suggestions.append(f'{len(stuffing)}개 키워드가 과다 사용되었습니다. 동의어로 대체해 보세요.')

    if lexical_diversity < 0.3:
        suggestions.append('어휘 다양성이 낮습니다. 다양한 표현을 사용해 보세요.')
    elif lexical_diversity > 0.8:
        suggestions.append('어휘 다양성이 높습니다. 핵심 키워드 반복이 부족할 수 있습니다.')

    if not suggestions:
        suggestions.append('키워드 분포가 양호합니다.')

    return {
        'top_keywords': top_keywords,
        'total_words': total_words,
        'unique_words': unique_words,
        'lexical_diversity': lexical_diversity,
        'suggestions': suggestions,
    }


def _tokenize(text: str) -> list:
    """텍스트를 단어로 분리합니다 (한국어+영어)."""
    # 한국어 2자 이상 + 영어 2자 이상
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', text)
    return [w.lower() for w in words]
