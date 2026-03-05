"""
자동 내부 링크 네트워크 서비스 (F10-19)
콘텐츠 간 의미적 연관성을 분석하여 내부 링크 자동 추천
"""
import logging
import math
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _extract_keywords(text: str, top_n: int = 20) -> List[str]:
    """간단한 TF 기반 키워드 추출 (형태소 분석기 없이)"""
    # 한글 단어 추출 (2자 이상)
    words = re.findall(r'[가-힣]{2,}', text)
    # 영문 단어 추출 (4자 이상)
    words += re.findall(r'[a-zA-Z]{4,}', text.lower())

    # 불용어
    stopwords = {'있다', '이다', '하다', '되다', '것이', '수있', '때문', '위해', '통해',
                 'that', 'this', 'with', 'from', 'have', 'will', 'been', 'they'}

    freq: Dict[str, int] = {}
    for w in words:
        if w not in stopwords:
            freq[w] = freq.get(w, 0) + 1

    # 빈도순 정렬
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:top_n]]


def _tf_idf_similarity(doc_a_keywords: List[str], doc_b_keywords: List[str]) -> float:
    """두 키워드 집합 간 자카드 유사도"""
    set_a = set(doc_a_keywords)
    set_b = set(doc_b_keywords)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


class LinkNetworkService:
    """
    내부 링크 네트워크 서비스

    사용법:
        service = LinkNetworkService()
        service.add_document('doc-1', '제목', '내용...')
        service.add_document('doc-2', '제목2', '내용2...')
        links = service.get_recommendations('doc-1', top_k=5)
    """

    def __init__(self, similarity_threshold: float = 0.1):
        self.documents: Dict[str, Dict[str, Any]] = {}
        self.keywords_cache: Dict[str, List[str]] = {}
        self.threshold = similarity_threshold

    def add_document(
        self,
        doc_id: str,
        title: str,
        content: str,
        url: str = '',
        tags: Optional[List[str]] = None,
    ) -> None:
        """문서 추가"""
        keywords = _extract_keywords(content)
        # 제목 키워드 가중치 (3배)
        title_keywords = _extract_keywords(title) * 3
        all_keywords = title_keywords + keywords

        self.documents[doc_id] = {
            'id': doc_id,
            'title': title,
            'url': url,
            'tags': tags or [],
            'word_count': len(content.split()),
        }
        self.keywords_cache[doc_id] = all_keywords

    def add_documents_batch(self, documents: List[Dict[str, Any]]) -> int:
        """배치 문서 추가"""
        added = 0
        for doc in documents:
            self.add_document(
                doc_id=doc.get('id', ''),
                title=doc.get('title', ''),
                content=doc.get('content', ''),
                url=doc.get('url', ''),
                tags=doc.get('tags', []),
            )
            added += 1
        return added

    def get_recommendations(
        self,
        doc_id: str,
        top_k: int = 5,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        특정 문서에 대한 내부 링크 추천

        Args:
            doc_id: 대상 문서 ID
            top_k: 추천 수
            exclude_ids: 제외할 문서 ID 목록

        Returns:
            추천 문서 목록 (유사도 순)
        """
        if doc_id not in self.keywords_cache:
            return []

        source_keywords = self.keywords_cache[doc_id]
        exclude = set(exclude_ids or []) | {doc_id}

        similarities = []
        for other_id, other_keywords in self.keywords_cache.items():
            if other_id in exclude:
                continue
            score = _tf_idf_similarity(source_keywords, other_keywords)
            if score >= self.threshold:
                similarities.append((other_id, score))

        # 유사도 순 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)

        results = []
        for other_id, score in similarities[:top_k]:
            doc = self.documents.get(other_id, {})
            results.append({
                'doc_id': other_id,
                'title': doc.get('title', ''),
                'url': doc.get('url', ''),
                'similarity_score': round(score, 3),
                'common_keywords': list(
                    set(source_keywords) & set(self.keywords_cache[other_id])
                )[:5],
            })

        return results

    def build_link_graph(self, top_k_per_doc: int = 3) -> Dict[str, List[str]]:
        """
        전체 문서 링크 그래프 구축

        Returns:
            {doc_id: [linked_doc_id, ...]} 형태의 인접 리스트
        """
        graph: Dict[str, List[str]] = {}
        for doc_id in self.documents:
            recs = self.get_recommendations(doc_id, top_k=top_k_per_doc)
            graph[doc_id] = [r['doc_id'] for r in recs]
        return graph

    def suggest_link_anchors(
        self,
        source_content: str,
        target_title: str,
        target_url: str,
    ) -> List[Dict[str, str]]:
        """
        콘텐츠 내에서 링크 삽입 위치 및 앵커 텍스트 제안

        Returns:
            [{'anchor_text': str, 'context': str, 'position': int}]
        """
        target_keywords = _extract_keywords(target_title)
        suggestions = []

        sentences = re.split(r'[.!?。]\s+', source_content)
        for sentence in sentences:
            sentence_keywords = _extract_keywords(sentence)
            if not sentence_keywords:
                continue

            common = set(target_keywords[:10]) & set(sentence_keywords[:20])
            if common:
                anchor = min(common, key=len)  # 가장 짧은 공통 키워드를 앵커로
                pos = source_content.find(sentence)
                suggestions.append({
                    'anchor_text': anchor,
                    'context': sentence[:100],
                    'target_url': target_url,
                    'target_title': target_title,
                    'position': pos,
                })

        return suggestions[:3]  # 최대 3개 제안

    def get_stats(self) -> Dict[str, Any]:
        """링크 네트워크 통계"""
        graph = self.build_link_graph()
        total_links = sum(len(v) for v in graph.values())
        return {
            'document_count': len(self.documents),
            'total_links': total_links,
            'avg_links_per_doc': round(total_links / max(1, len(self.documents)), 1),
            'isolated_docs': sum(1 for v in graph.values() if not v),
        }
