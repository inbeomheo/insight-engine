"""
콘텐츠 카니발리제이션 감지 서비스

동일/유사 키워드를 타겟하는 콘텐츠 간의 경쟁(카니발리제이션)을 감지하고
병합 또는 차별화 제안을 제공합니다.
"""
import re
import logging
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)

# 불용어 (한국어 기본)
_STOPWORDS = {
    '이', '그', '저', '것', '수', '등', '및', '또는', '그리고', '하지만',
    '때문', '위해', '대한', '통해', '따라', '관련', '같은', '모든', '많은',
    '있는', '하는', '되는', '위한', '없는', '있다', '하다', '되다', '않다',
    '더', '가장', '매우', '아주', '정말', '약', '각', '또한', '이미',
}

# 최소 키워드 길이
_MIN_KEYWORD_LEN = 2


def detect_cannibalization(contents: List[dict]) -> dict:
    """여러 콘텐츠 간의 키워드 카니발리제이션을 감지합니다.

    Args:
        contents: [{"id": str, "title": str, "content": str}, ...]

    Returns:
        {
            "conflicts": [
                {
                    "keyword": str,
                    "affected_contents": [{"id": str, "title": str, "density": float}],
                    "severity": "high" | "medium" | "low",
                    "suggestion": str,
                }
            ],
            "total_conflicts": int,
            "summary": str,
        }
    """
    if not contents or len(contents) < 2:
        return {
            'conflicts': [],
            'total_conflicts': 0,
            'summary': '카니발리제이션 분석에는 최소 2개 콘텐츠가 필요합니다.',
        }

    # 각 콘텐츠의 키워드 추출
    content_keywords = {}
    for item in contents:
        cid = item.get('id', '')
        text = f"{item.get('title', '')} {item.get('content', '')}"
        keywords = _extract_keywords(text)
        content_keywords[cid] = {
            'title': item.get('title', ''),
            'keywords': keywords,
        }

    # 키워드 겹침 감지
    conflicts = _find_conflicts(content_keywords)

    # 심각도 정렬
    conflicts.sort(key=lambda c: {'high': 0, 'medium': 1, 'low': 2}[c['severity']])

    total = len(conflicts)
    if total == 0:
        summary = '카니발리제이션이 감지되지 않았습니다.'
    elif total <= 3:
        summary = f'{total}개 키워드에서 경미한 카니발리제이션이 감지되었습니다.'
    else:
        summary = f'{total}개 키워드에서 카니발리제이션이 감지되었습니다. 콘텐츠 차별화가 필요합니다.'

    return {
        'conflicts': conflicts,
        'total_conflicts': total,
        'summary': summary,
    }


def check_pair(content_a: str, content_b: str, title_a: str = '', title_b: str = '') -> dict:
    """두 콘텐츠 간의 카니발리제이션을 확인합니다.

    Args:
        content_a: 첫 번째 콘텐츠
        content_b: 두 번째 콘텐츠
        title_a: 첫 번째 제목
        title_b: 두 번째 제목

    Returns:
        {
            "similarity_score": float (0~1),
            "shared_keywords": list[str],
            "is_cannibalized": bool,
            "suggestion": str,
        }
    """
    if not content_a or not content_b:
        return {
            'similarity_score': 0.0,
            'shared_keywords': [],
            'is_cannibalized': False,
            'suggestion': '비교할 콘텐츠가 부족합니다.',
        }

    kw_a = _extract_keywords(f"{title_a} {content_a}")
    kw_b = _extract_keywords(f"{title_b} {content_b}")

    set_a = set(kw_a.keys())
    set_b = set(kw_b.keys())

    shared = set_a & set_b
    union = set_a | set_b

    similarity = len(shared) / len(union) if union else 0.0
    similarity = round(similarity, 3)

    # 상위 공유 키워드
    shared_sorted = sorted(shared, key=lambda k: kw_a.get(k, 0) + kw_b.get(k, 0), reverse=True)

    is_cannibalized = similarity > 0.3 and len(shared) >= 3

    if is_cannibalized:
        if similarity > 0.6:
            suggestion = '유사도가 매우 높습니다. 두 콘텐츠를 하나로 병합하는 것을 권장합니다.'
        else:
            suggestion = '키워드 겹침이 있습니다. 각 콘텐츠의 타겟 키워드를 차별화하세요.'
    else:
        suggestion = '카니발리제이션 위험이 낮습니다.'

    return {
        'similarity_score': similarity,
        'shared_keywords': shared_sorted[:10],
        'is_cannibalized': is_cannibalized,
        'suggestion': suggestion,
    }


def _extract_keywords(text: str, top_n: int = 30) -> dict:
    """텍스트에서 키워드와 빈도를 추출합니다."""
    text = _strip_markdown(text)
    # 한국어 + 영문 단어 추출
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{3,}', text.lower())

    # 불용어 제거
    filtered = [w for w in words if w not in _STOPWORDS and len(w) >= _MIN_KEYWORD_LEN]

    counter = Counter(filtered)
    return dict(counter.most_common(top_n))


def _strip_markdown(text: str) -> str:
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text


def _find_conflicts(content_keywords: dict) -> list:
    """모든 콘텐츠 쌍에서 키워드 충돌을 감지합니다."""
    # 키워드 → 포함 콘텐츠 매핑
    keyword_map = {}
    for cid, data in content_keywords.items():
        for keyword, freq in data['keywords'].items():
            if keyword not in keyword_map:
                keyword_map[keyword] = []
            total_words = sum(data['keywords'].values())
            density = round(freq / total_words, 4) if total_words > 0 else 0.0
            keyword_map[keyword].append({
                'id': cid,
                'title': data['title'],
                'density': density,
                'frequency': freq,
            })

    conflicts = []
    for keyword, items in keyword_map.items():
        if len(items) < 2:
            continue

        # 빈도 3 이상인 콘텐츠가 2개 이상이면 충돌
        high_freq_items = [i for i in items if i['frequency'] >= 3]
        if len(high_freq_items) < 2:
            continue

        # 심각도 판정
        max_density = max(i['density'] for i in high_freq_items)
        if max_density > 0.05:
            severity = 'high'
        elif max_density > 0.02:
            severity = 'medium'
        else:
            severity = 'low'

        suggestion = _suggest_resolution(keyword, severity)

        conflicts.append({
            'keyword': keyword,
            'affected_contents': [
                {'id': i['id'], 'title': i['title'], 'density': i['density']}
                for i in high_freq_items
            ],
            'severity': severity,
            'suggestion': suggestion,
        })

    return conflicts


def _suggest_resolution(keyword: str, severity: str) -> str:
    if severity == 'high':
        return f'"{keyword}" 키워드가 여러 콘텐츠에서 높은 밀도로 사용됩니다. 대표 콘텐츠 하나를 정하고 나머지는 롱테일 키워드로 전환하세요.'
    elif severity == 'medium':
        return f'"{keyword}" 키워드 겹침이 있습니다. 각 콘텐츠의 관점이나 하위 주제를 차별화하세요.'
    else:
        return f'"{keyword}" 경미한 겹침. 현재 수준은 허용 범위입니다.'
