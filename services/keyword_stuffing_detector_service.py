"""
Keyword Stuffing Detector 서비스

콘텐츠에서 특정 키워드의 과잉 삽입(keyword stuffing)을 감지합니다.
SEO 스팸 판정 기준으로 키워드 밀도를 분석합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List, Dict

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_HTML_TAG_RE = re.compile(r'<[^>]+>')

# 한국어 단어 추출 (2자 이상)
_KO_WORD_RE = re.compile(r'[가-힣]{2,}')
# 영어 단어 추출 (3자 이상)
_EN_WORD_RE = re.compile(r'[A-Za-z]{3,}')

# 한국어 불용어
_STOPWORDS = {
    '있는', '없는', '하는', '되는', '않는', '같은', '위한', '대한',
    '합니다', '입니다', '됩니다', '있습니다', '없습니다', '했습니다',
    '그리고', '하지만', '그러나', '또는', '그래서', '따라서',
    'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all',
    'can', 'had', 'her', 'was', 'one', 'our', 'out',
}

# 과잉 밀도 임계값 (%)
_STUFFING_THRESHOLD = 3.0  # 단일 키워드 3% 이상
_WARNING_THRESHOLD = 2.0   # 2% 이상 경고


def detect_keyword_stuffing(content: str) -> dict:
    """키워드 과잉 삽입을 감지합니다.

    Returns:
        keyword_density, stuffed_keywords, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'keyword_density': [],
            'stuffed_keywords': [],
            'summary': {'total_words': 0, 'unique_keywords': 0,
                        'max_density': 0.0, 'stuffing_detected': False},
            'score': 100.0,
            'suggestions': [],
        }

    # 전처리
    cleaned = _HEADING_RE.sub('', content)
    cleaned = _MD_LINK_RE.sub(r'\1', cleaned)
    cleaned = _HTML_TAG_RE.sub('', cleaned)

    # 단어 추출
    ko_words = [w for w in _KO_WORD_RE.findall(cleaned) if w not in _STOPWORDS]
    en_words = [w.lower() for w in _EN_WORD_RE.findall(cleaned) if w.lower() not in _STOPWORDS]
    all_words = ko_words + en_words

    if not all_words:
        return {
            'keyword_density': [],
            'stuffed_keywords': [],
            'summary': {'total_words': 0, 'unique_keywords': 0,
                        'max_density': 0.0, 'stuffing_detected': False},
            'score': 100.0,
            'suggestions': [],
        }

    total = len(all_words)
    counter = Counter(all_words)

    # 밀도 계산 (상위 20개)
    keyword_density = []
    for word, count in counter.most_common(20):
        density = round(count / total * 100, 2)
        keyword_density.append({
            'keyword': word,
            'count': count,
            'density': density,
        })

    # 과잉 키워드 감지 (최소 50단어 이상에서만 판정)
    stuffed = []
    warned = []
    if total >= 50:
        for kd in keyword_density:
            if kd['density'] >= _STUFFING_THRESHOLD:
                stuffed.append(kd)
            elif kd['density'] >= _WARNING_THRESHOLD:
                warned.append(kd)

    max_density = keyword_density[0]['density'] if keyword_density else 0.0
    stuffing_detected = len(stuffed) > 0

    # 점수 계산
    score = 100.0
    for s in stuffed:
        score -= (s['density'] - _STUFFING_THRESHOLD) * 10 + 10
    for w in warned:
        score -= 5.0
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(stuffed, warned, max_density)

    return {
        'keyword_density': keyword_density,
        'stuffed_keywords': stuffed,
        'summary': {
            'total_words': total,
            'unique_keywords': len(counter),
            'max_density': max_density,
            'stuffing_detected': stuffing_detected,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(stuffed: List[Dict], warned: List[Dict],
                           max_density: float) -> List[str]:
    suggestions = []

    if stuffed:
        names = ', '.join(f'"{s["keyword"]}" ({s["density"]}%)' for s in stuffed[:3])
        suggestions.append(
            f'키워드 과잉 감지: {names}. '
            f'검색엔진 페널티를 받을 수 있습니다. 동의어로 대체하세요.'
        )
    elif warned:
        names = ', '.join(f'"{w["keyword"]}" ({w["density"]}%)' for w in warned[:3])
        suggestions.append(f'키워드 밀도 주의: {names}. 과잉 기준에 근접합니다.')
    else:
        suggestions.append(f'키워드 밀도가 적정합니다 (최대 {max_density}%).')

    if max_density > 5.0:
        suggestions.append(
            '단일 키워드 밀도 5% 이상은 스팸으로 판정될 위험이 높습니다.'
        )

    return suggestions
