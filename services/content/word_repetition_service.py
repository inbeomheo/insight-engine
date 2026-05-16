"""
단어 반복 감지 서비스

콘텐츠에서 과다 반복 단어를 감지하고
대체어를 제안합니다. 규칙 기반 즉시 처리.
"""
import logging
import re
from collections import Counter
from typing import List

logger = logging.getLogger(__name__)

_WORD_PATTERN = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)

# 한국어 불용어 (반복 감지에서 제외)
_STOPWORDS = frozenset([
    '이', '그', '저', '것', '수', '등', '및', '또는', '위한', '대한',
    '통해', '따라', '경우', '때문', '이후', '위해', '함께', '가장',
    '그리고', '하지만', '그러나', '따라서', '그래서', '또한', '매우',
    '정말', '너무', '아주', '다시', '이미', '바로', '현재', '최근',
])

# 한국어 유의어 사전 (간소화)
_SYNONYMS = {
    '중요': ['핵심적', '필수적', '결정적', '주요'],
    '좋은': ['우수한', '훌륭한', '양호한', '적절한'],
    '나쁜': ['부정적', '좋지 않은', '불리한', '미흡한'],
    '많은': ['다수의', '상당수의', '풍부한', '다양한'],
    '큰': ['대규모의', '상당한', '막대한', '광범위한'],
    '작은': ['소규모의', '미세한', '사소한', '미미한'],
    '빠른': ['신속한', '즉각적인', '민첩한', '효율적인'],
    '새로운': ['혁신적인', '참신한', '최신의', '독창적인'],
    '다양한': ['여러 가지', '다채로운', '폭넓은', '광범위한'],
    '필요한': ['요구되는', '불가결한', '필수적인', '긴요한'],
    '사용': ['활용', '이용', '적용', '운용'],
    '제공': ['공급', '지원', '전달', '부여'],
    '확인': ['검증', '점검', '검토', '파악'],
    '진행': ['수행', '실행', '추진', '시행'],
    '발생': ['초래', '야기', '출현', '등장'],
}


def detect_repetitions(content: str, threshold: int = 3) -> dict:
    """과다 반복 단어를 감지합니다.

    Args:
        content: 분석할 콘텐츠
        threshold: 반복 감지 임계값 (기본 3회 이상)

    Returns:
        {
            'repetitions': [{'word': str, 'count': int, 'density': float, 'suggestions': [str]}],
            'total_words': int,
            'unique_words': int,
            'vocabulary_richness': float,
            'top_repeated': int,
        }
    """
    if not content or not content.strip():
        return _empty_result()

    threshold = max(2, min(20, threshold))

    # 헤딩 제거 후 분석
    text = _HEADING_PATTERN.sub('', content)
    words = _WORD_PATTERN.findall(text)

    if not words:
        return _empty_result()

    total = len(words)
    word_counts = Counter(w.lower() for w in words if w.lower() not in _STOPWORDS)

    unique = len(word_counts)
    richness = round(unique / total, 4) if total > 0 else 0

    repetitions = []
    for word, count in word_counts.most_common():
        if count < threshold:
            break
        density = round(count / total, 4)
        suggestions = _get_suggestions(word)
        repetitions.append({
            'word': word,
            'count': count,
            'density': density,
            'suggestions': suggestions,
        })

    return {
        'repetitions': repetitions,
        'total_words': total,
        'unique_words': unique,
        'vocabulary_richness': richness,
        'top_repeated': len(repetitions),
    }


def _get_suggestions(word: str) -> List[str]:
    """단어의 대체어를 제안합니다."""
    lower = word.lower()
    if lower in _SYNONYMS:
        return _SYNONYMS[lower][:3]

    # 부분 매칭
    for key, syns in _SYNONYMS.items():
        if key in lower or lower in key:
            return syns[:2]

    return []


def _empty_result() -> dict:
    return {
        'repetitions': [],
        'total_words': 0,
        'unique_words': 0,
        'vocabulary_richness': 0.0,
        'top_repeated': 0,
    }
