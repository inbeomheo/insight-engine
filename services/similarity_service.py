"""
콘텐츠 유사도 비교 서비스

TF-IDF 코사인 유사도 (외부 패키지 없이 순수 Python).
0.0(완전 다름) ~ 1.0(동일) 스코어 반환.
"""
import math
import re
import logging
from collections import Counter
from typing import Dict, List

logger = logging.getLogger(__name__)

# 불용어
_STOPWORDS = {
    '그', '이', '저', '것', '수', '등', '및', '더', '또', '를', '을', '에', '의', '가',
    '은', '는', '로', '으로', '와', '과', '에서', '까지', '부터', '하는', '한', '할',
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'and', 'or', 'but', 'in',
    'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'it', 'this',
    'that', 'not', 'no', 'so', 'if', 'as',
}


def _tokenize(text: str) -> List[str]:
    """텍스트를 토큰으로 분리 (2자 이상, 불용어 제외)."""
    words = re.findall(r'[가-힣a-zA-Z0-9]{2,}', text.lower())
    return [w for w in words if w not in _STOPWORDS]


def _build_tfidf_vectors(
    tokens1: List[str],
    tokens2: List[str],
) -> tuple:
    """두 문서의 TF-IDF 벡터를 생성합니다."""
    # TF 계산
    tf1 = Counter(tokens1)
    tf2 = Counter(tokens2)
    len1 = len(tokens1) or 1
    len2 = len(tokens2) or 1

    # 전체 어휘
    vocab = set(tf1.keys()) | set(tf2.keys())

    # IDF (2개 문서 기준, 스무딩 적용: log(1 + N/df))
    idf = {}
    for word in vocab:
        df = (1 if word in tf1 else 0) + (1 if word in tf2 else 0)
        idf[word] = math.log(1 + 2 / df)

    # TF-IDF 벡터
    v1 = {w: (tf1[w] / len1) * idf[w] for w in vocab}
    v2 = {w: (tf2[w] / len2) * idf[w] for w in vocab}

    return v1, v2


def compare_similarity(text1: str, text2: str) -> float:
    """두 텍스트의 코사인 유사도를 계산합니다.

    Args:
        text1: 첫 번째 텍스트
        text2: 두 번째 텍스트

    Returns:
        0.0 ~ 1.0 유사도 점수
    """
    if not text1 or not text2:
        return 0.0

    tokens1 = _tokenize(text1)
    tokens2 = _tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    v1, v2 = _build_tfidf_vectors(tokens1, tokens2)

    # 코사인 유사도
    dot = sum(v1[w] * v2[w] for w in v1)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0

    return round(dot / (mag1 * mag2), 4)
