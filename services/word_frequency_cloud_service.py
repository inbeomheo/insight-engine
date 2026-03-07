"""
Word Frequency Cloud Generator 서비스

콘텐츠에서 단어 빈도를 분석하여 워드 클라우드 데이터를 생성합니다.
불용어(stopwords) 제외, 명사/키워드 중심 빈도 산출.
규칙 기반 (AI API 호출 없음).
"""
import re
from collections import Counter
from typing import List, Dict

# 한국어 불용어
_KO_STOPWORDS = {
    '이', '그', '저', '것', '수', '등', '및', '또', '더', '매우',
    '있다', '없다', '하다', '되다', '이다', '않다', '같다', '보다',
    '있는', '없는', '하는', '되는', '않는', '같은', '위한', '대한',
    '통해', '따라', '위해', '때문', '의해', '대해', '관한', '있을',
    '합니다', '입니다', '됩니다', '있습니다', '없습니다', '했습니다',
    '하세요', '해요', '이에요', '인데요', '거든요', '잖아요',
    '그리고', '하지만', '그러나', '또는', '그래서', '따라서', '그런데',
    '에서', '으로', '에게', '까지', '부터', '처럼', '만큼',
}

# 영어 불용어
_EN_STOPWORDS = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'shall', 'must', 'need',
    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her',
    'us', 'them', 'my', 'your', 'his', 'its', 'our', 'their',
    'this', 'that', 'these', 'those', 'what', 'which', 'who', 'whom',
    'and', 'or', 'but', 'if', 'then', 'so', 'because', 'as', 'while',
    'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from', 'about',
    'not', 'no', 'nor', 'very', 'just', 'also', 'more', 'most', 'too',
    'how', 'when', 'where', 'why', 'all', 'each', 'every', 'both',
}

_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_MD_LINK_RE = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_HTML_TAG_RE = re.compile(r'<[^>]+>')
_KO_WORD_RE = re.compile(r'[가-힣]{2,}')
_EN_WORD_RE = re.compile(r'[A-Za-z]{3,}')


def generate_word_frequency(content: str, top_n: int = 30) -> dict:
    """단어 빈도를 분석하여 워드 클라우드 데이터를 생성합니다.

    Args:
        content: 분석할 콘텐츠
        top_n: 상위 N개 단어 반환 (기본 30)

    Returns:
        word_cloud, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'word_cloud': [],
            'summary': {'total_words': 0, 'unique_words': 0,
                        'diversity_ratio': 0.0, 'dominant_language': ''},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    # 전처리
    cleaned = _HEADING_RE.sub('', content)
    cleaned = _MD_LINK_RE.sub(r'\1', cleaned)
    cleaned = _HTML_TAG_RE.sub('', cleaned)

    # 한국어 단어 추출
    ko_words = _KO_WORD_RE.findall(cleaned)
    ko_filtered = [w for w in ko_words if w not in _KO_STOPWORDS]

    # 영어 단어 추출
    en_words = [w.lower() for w in _EN_WORD_RE.findall(cleaned)]
    en_filtered = [w for w in en_words if w not in _EN_STOPWORDS]

    all_words = ko_filtered + en_filtered

    if not all_words:
        return {
            'word_cloud': [],
            'summary': {'total_words': 0, 'unique_words': 0,
                        'diversity_ratio': 0.0, 'dominant_language': ''},
            'score': 50.0,
            'suggestions': ['분석 가능한 키워드가 부족합니다.'],
        }

    # 빈도 계산
    counter = Counter(all_words)
    total = len(all_words)
    unique = len(counter)

    # 상위 N개
    top_words = counter.most_common(top_n)
    max_count = top_words[0][1] if top_words else 1

    word_cloud = []
    for word, count in top_words:
        word_cloud.append({
            'word': word,
            'count': count,
            'frequency': round(count / total * 100, 2),
            'weight': round(count / max_count, 2),
        })

    # 다양성 비율
    diversity = round(unique / total * 100, 1) if total > 0 else 0.0

    # 지배 언어
    dominant = 'ko' if len(ko_filtered) >= len(en_filtered) else 'en'

    # 점수: 다양성 기반 (30-70% 최적)
    if 30 <= diversity <= 70:
        score = 100.0
    elif diversity < 30:
        score = max(30.0, diversity * 3.3)
    else:
        score = max(50.0, 100.0 - (diversity - 70) * 1.5)
    score = round(min(100.0, score), 1)

    suggestions = _generate_suggestions(word_cloud, diversity, total)

    return {
        'word_cloud': word_cloud,
        'summary': {
            'total_words': total,
            'unique_words': unique,
            'diversity_ratio': diversity,
            'dominant_language': dominant,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(cloud: List[Dict], diversity: float, total: int) -> List[str]:
    suggestions = []

    if diversity < 30:
        suggestions.append(
            f'단어 다양성 {diversity}%로 낮습니다. '
            f'동의어나 관련 키워드를 추가하세요.'
        )
    elif diversity > 70:
        suggestions.append(
            f'단어 다양성 {diversity}%로 높습니다. '
            f'핵심 키워드를 반복하면 SEO에 유리합니다.'
        )
    else:
        suggestions.append(f'단어 다양성 {diversity}%로 적정합니다.')

    if cloud and cloud[0]['frequency'] > 10:
        suggestions.append(
            f'최빈 단어 "{cloud[0]["word"]}" 빈도 {cloud[0]["frequency"]}%: '
            f'과도한 반복은 자연스러움을 떨어뜨립니다.'
        )

    return suggestions
