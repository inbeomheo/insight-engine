"""
토픽 클러스터링 서비스

1) cluster_contents: TF-IDF 기반 키워드 추출 → 코사인 유사도 → 그리디 클러스터링.
2) map_topic_clusters: 규칙 기반 pillar-supporting 토픽 클러스터 맵 생성.
외부 NLP 패키지 없이 순수 Python으로 구현.
"""
import math
import re
import logging
from collections import Counter, defaultdict
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


# ---------------------------------------------------------------------------
# map_topic_clusters: pillar-supporting 구조 토픽 클러스터 맵
# ---------------------------------------------------------------------------

# 한국어 조사 패턴 (키워드 뒤에 붙는 조사 제거용)
_KO_JOSA_PATTERN = re.compile(
    r'(은|는|이|가|을|를|의|에|에서|으로|로|와|과|도|만|까지|부터|라|란|처럼|보다|마저|조차)$'
)

# 불용어 (map_topic_clusters 전용, 좀 더 포괄적)
_MAP_STOPWORDS = {
    # 한국어 기능어
    '그것', '이것', '저것', '여기', '거기', '어디', '무엇', '어떤',
    '하다', '되다', '있다', '없다', '같다', '대한', '통해', '위해',
    '이런', '그런', '저런', '모든', '어떻게', '그래서', '하지만', '그러나',
    '때문', '사실', '경우', '정도', '이후', '이전', '현재', '최근',
    # 영어 기능어
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'shall', 'can', 'and', 'or', 'but', 'in',
    'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'it', 'this',
    'that', 'not', 'no', 'so', 'if', 'as', 'its', 'into', 'about',
    'than', 'then', 'also', 'just', 'more', 'some', 'any', 'other',
    'very', 'when', 'where', 'how', 'what', 'which', 'who', 'whom',
    'there', 'here', 'these', 'those', 'such', 'only', 'own', 'same',
    'both', 'each', 'all', 'many', 'much', 'most', 'every', 'few',
}


def _strip_josa(word: str) -> str:
    """한국어 단어 끝의 조사를 제거합니다."""
    stripped = _KO_JOSA_PATTERN.sub('', word)
    # 조사 제거 후 2자 미만이면 원본 반환
    return stripped if len(stripped) >= 2 else word


def _extract_topic_keywords(text: str) -> Counter:
    """텍스트에서 토픽 키워드를 추출합니다 (빈도 카운터 반환).

    규칙:
    - 한국어 명사(2-8자) 2회 이상 등장
    - 영어 단어(3자 이상) 2회 이상 등장
    - 한국어 조사 제거
    - 불용어 제외
    """
    # 한국어 토큰 추출: 2-8자 한글
    ko_tokens = re.findall(r'[가-힣]{2,8}', text)
    # 조사 제거
    ko_tokens = [_strip_josa(w) for w in ko_tokens]
    # 2자 미만 필터링 + 불용어 제거
    ko_tokens = [w for w in ko_tokens if len(w) >= 2 and w not in _MAP_STOPWORDS]

    # 영어 토큰 추출: 3자 이상
    en_tokens = re.findall(r'[a-zA-Z]{3,}', text.lower())
    en_tokens = [w for w in en_tokens if w not in _MAP_STOPWORDS]

    # 전체 빈도 카운트
    counts = Counter(ko_tokens + en_tokens)

    # 2회 이상 등장 키워드만 유지
    return Counter({word: freq for word, freq in counts.items() if freq >= 2})


def _extract_all_keywords(
    contents: list,
) -> tuple:
    """콘텐츠 목록에서 키워드를 추출하고 토픽-콘텐츠 매핑을 생성합니다.

    Returns:
        (content_keywords, topic_to_contents, pillar_candidates)
    """
    content_keywords: Dict[str, Counter] = {}
    topic_to_contents: Dict[str, Dict[str, int]] = defaultdict(dict)

    for item in contents:
        cid = item.get("id", "")
        title = item.get("title", "")
        body = item.get("content", "")

        title_kw = _extract_topic_keywords(title + " " + title)
        body_kw = _extract_topic_keywords(body)
        content_keywords[cid] = body_kw + title_kw

    for cid, kw_counter in content_keywords.items():
        for keyword, freq in kw_counter.items():
            topic_to_contents[keyword][cid] = freq

    pillar_candidates = []
    for topic, cid_freq_map in topic_to_contents.items():
        if len(cid_freq_map) >= 2:
            pillar_candidates.append((topic, len(cid_freq_map), sum(cid_freq_map.values())))
    pillar_candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)

    return content_keywords, topic_to_contents, pillar_candidates


def _build_clusters_greedy(
    contents: list,
    content_keywords: Dict[str, Counter],
    topic_to_contents: Dict[str, Dict[str, int]],
    pillar_candidates: list,
) -> tuple:
    """그리디 방식으로 pillar-supporting 클러스터를 구성합니다.

    Returns:
        (clusters, clustered_content_ids)
    """
    clustered_content_ids: set = set()
    clusters = []

    for pillar_topic, _, _ in pillar_candidates:
        cid_freq_map = topic_to_contents[pillar_topic]
        available_cids = {cid: freq for cid, freq in cid_freq_map.items()
                         if cid not in clustered_content_ids}
        if len(available_cids) < 2:
            continue

        pillar_content_id = max(available_cids, key=available_cids.get)
        pillar_kws = set(content_keywords.get(pillar_content_id, {}).keys())

        supporting = []
        for cid, freq in available_cids.items():
            if cid == pillar_content_id:
                continue
            support_kws = set(content_keywords.get(cid, {}).keys())
            shared_kws = sorted(pillar_kws & support_kws)
            total_support_kws = len(support_kws) if support_kws else 1
            relevance = min(round(len(shared_kws) / total_support_kws, 2), 1.0)

            title = ""
            for item in contents:
                if item.get("id") == cid:
                    title = item.get("title", "")
                    break

            supporting.append({
                "id": cid, "title": title,
                "relevance": relevance, "shared_keywords": shared_kws,
            })

        # cluster_strength 계산
        all_shared_kws: set = set()
        for s in supporting:
            all_shared_kws.update(s["shared_keywords"])
        kw_score = min(len(all_shared_kws) * 10, 50)
        support_score = min(len(supporting) * 10, 30)

        title_bonus = 0
        for item in contents:
            if item.get("id") == pillar_content_id:
                if pillar_topic in item.get("title", ""):
                    title_bonus = 20
                break

        cluster_strength = max(min(kw_score + support_score + title_bonus, 100), 0)

        clusters.append({
            "pillar_topic": pillar_topic,
            "pillar_content_id": pillar_content_id,
            "supporting_contents": supporting,
            "cluster_strength": float(cluster_strength),
        })
        clustered_content_ids.add(pillar_content_id)
        for s in supporting:
            clustered_content_ids.add(s["id"])

    return clusters, clustered_content_ids


def _generate_cluster_suggestions(
    clusters: list,
    unclustered: list,
    coverage: float,
    total_count: int,
) -> list:
    """클러스터 분석 결과에 대한 개선 제안을 생성합니다."""
    suggestions = []

    if unclustered:
        suggestions.append(
            f"{len(unclustered)}개 콘텐츠가 클러스터에 속하지 않습니다. "
            f"관련 주제의 콘텐츠를 추가하면 클러스터 커버리지가 개선됩니다."
        )
    for cluster in clusters:
        if len(cluster["supporting_contents"]) < 2:
            suggestions.append(
                f"'{cluster['pillar_topic']}' 클러스터의 서포팅 콘텐츠가 부족합니다. "
                f"관련 콘텐츠를 추가하세요."
            )
    weak_clusters = [c for c in clusters if c["cluster_strength"] < 30]
    if weak_clusters:
        topics = ", ".join(c["pillar_topic"] for c in weak_clusters)
        suggestions.append(
            f"결합도가 낮은 클러스터가 있습니다 ({topics}). "
            f"공유 키워드를 늘려 내부 링크를 강화하세요."
        )
    if coverage < 50 and total_count >= 3:
        suggestions.append(
            f"전체 커버리지가 {coverage}%로 낮습니다. "
            f"공통 주제를 중심으로 콘텐츠 전략을 재구성하세요."
        )
    if not suggestions:
        suggestions.append("토픽 클러스터가 잘 구성되어 있습니다.")

    return suggestions


_EMPTY_CLUSTER_RESULT = {
    "clusters": [],
    "unclustered": [],
    "summary": {"total_clusters": 0, "avg_cluster_size": 0.0, "coverage": 0.0},
}


def map_topic_clusters(contents: list) -> dict:
    """여러 콘텐츠를 분석하여 pillar-supporting 구조의 토픽 클러스터 맵을 생성합니다.

    Args:
        contents: [{"id": str, "title": str, "content": str}, ...] 형태의 리스트.

    Returns:
        {
            "clusters": [...],
            "unclustered": [...],
            "summary": {"total_clusters": int, "avg_cluster_size": float, "coverage": float},
            "suggestions": [...]
        }
    """
    if not contents:
        return {**_EMPTY_CLUSTER_RESULT, "suggestions": ["콘텐츠를 추가하여 토픽 클러스터 분석을 시작하세요."]}

    total_count = len(contents)
    if total_count == 1:
        return {
            **_EMPTY_CLUSTER_RESULT,
            "unclustered": [contents[0].get("id", "0")],
            "suggestions": ["최소 2개 이상의 콘텐츠가 있어야 클러스터를 형성할 수 있습니다."],
        }

    content_keywords, topic_to_contents, pillar_candidates = _extract_all_keywords(contents)
    clusters, clustered_ids = _build_clusters_greedy(
        contents, content_keywords, topic_to_contents, pillar_candidates,
    )

    all_ids = [item.get("id", "") for item in contents]
    unclustered = [cid for cid in all_ids if cid not in clustered_ids]

    total_clusters = len(clusters)
    cluster_sizes = [1 + len(c["supporting_contents"]) for c in clusters]
    avg_cluster_size = round(sum(cluster_sizes) / total_clusters, 2) if total_clusters > 0 else 0.0
    coverage = round((len(clustered_ids) / total_count) * 100, 2) if total_count > 0 else 0.0

    suggestions = _generate_cluster_suggestions(clusters, unclustered, coverage, total_count)

    return {
        "clusters": clusters,
        "unclustered": unclustered,
        "summary": {
            "total_clusters": total_clusters,
            "avg_cluster_size": avg_cluster_size,
            "coverage": coverage,
        },
        "suggestions": suggestions,
    }
