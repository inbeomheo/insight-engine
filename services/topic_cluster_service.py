"""
토픽 클러스터링 서비스

TF-IDF 기반 키워드 추출 → 코사인 유사도 → 그리디 클러스터링.
외부 NLP 패키지 없이 순수 Python으로 구현.
"""
import math
import re
import logging
from collections import Counter
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# 클러스터링 유사도 임계값 (이 값 이상이면 같은 클러스터)
SIMILARITY_THRESHOLD = 0.15

# 불용어 (한국어 + 영어 기본)
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


def _compute_tf(tokens: List[str]) -> Dict[str, float]:
    """단어 빈도(TF) 계산."""
    counts = Counter(tokens)
    total = len(tokens) or 1
    return {word: count / total for word, count in counts.items()}


def _compute_idf(docs_tokens: List[List[str]]) -> Dict[str, float]:
    """역문서 빈도(IDF) 계산."""
    n = len(docs_tokens)
    if n == 0:
        return {}

    # 각 단어가 등장하는 문서 수
    df = Counter()
    for tokens in docs_tokens:
        unique = set(tokens)
        for word in unique:
            df[word] += 1

    return {word: math.log(n / count) for word, count in df.items()}


def _tfidf_vector(tf: Dict[str, float], idf: Dict[str, float]) -> Dict[str, float]:
    """TF-IDF 벡터 생성."""
    return {word: score * idf.get(word, 0) for word, score in tf.items()}


def _cosine_similarity(v1: Dict[str, float], v2: Dict[str, float]) -> float:
    """두 벡터의 코사인 유사도."""
    common = set(v1.keys()) & set(v2.keys())
    if not common:
        return 0.0

    dot = sum(v1[k] * v2[k] for k in common)
    mag1 = math.sqrt(sum(v ** 2 for v in v1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in v2.values()))

    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def cluster_contents(
    contents: List[Dict[str, Any]],
    threshold: float = SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """콘텐츠 목록을 토픽별로 클러스터링합니다.

    Args:
        contents: [{"id": str, "title": str, "content": str}, ...] 형태의 리스트.
                  id가 없으면 인덱스를 사용.
        threshold: 같은 클러스터로 묶을 최소 코사인 유사도 (기본 0.15)

    Returns:
        [{"topic": str, "content_ids": list, "keywords": list}, ...] 형태의 리스트.
    """
    if not contents:
        return []

    # 1. 토큰화 + TF-IDF 계산
    docs_tokens = []
    doc_ids = []
    for i, item in enumerate(contents):
        text = f"{item.get('title', '')} {item.get('content', '')}"
        tokens = _tokenize(text)
        docs_tokens.append(tokens)
        doc_ids.append(item.get('id', str(i)))

    idf = _compute_idf(docs_tokens)

    vectors = []
    for tokens in docs_tokens:
        tf = _compute_tf(tokens)
        vectors.append(_tfidf_vector(tf, idf))

    # 2. 그리디 클러스터링
    assigned = [False] * len(contents)
    clusters = []

    for i in range(len(contents)):
        if assigned[i]:
            continue

        cluster_indices = [i]
        assigned[i] = True

        for j in range(i + 1, len(contents)):
            if assigned[j]:
                continue
            sim = _cosine_similarity(vectors[i], vectors[j])
            if sim >= threshold:
                cluster_indices.append(j)
                assigned[j] = True

        # 클러스터 키워드 추출 (TF-IDF 상위 5개)
        merged_vector: Dict[str, float] = {}
        for idx in cluster_indices:
            for word, score in vectors[idx].items():
                merged_vector[word] = merged_vector.get(word, 0) + score

        top_keywords = sorted(merged_vector, key=merged_vector.get, reverse=True)[:5]

        # 토픽명: 상위 키워드 조합
        topic_name = ', '.join(top_keywords[:3]) if top_keywords else '기타'

        clusters.append({
            'topic': topic_name,
            'content_ids': [doc_ids[idx] for idx in cluster_indices],
            'keywords': top_keywords,
        })

    return clusters
