"""
팟캐스트 메모리 서비스 (T12.4)
에피소드 콘텐츠를 인메모리 저장소에 저장하고 키워드 매칭 기반으로 검색합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# 검색 결과 최대 개수
MAX_SEARCH_RESULTS = 10

# 최소 키워드 길이
MIN_KEYWORD_LENGTH = 2

# 불용어 (검색/키워드 추출 시 제외)
STOP_WORDS_KO = {
    '이', '그', '저', '것', '수', '등', '더', '또', '및', '의', '에', '를',
    '은', '는', '이', '가', '에서', '으로', '하는', '있는', '하고', '되는',
}

STOP_WORDS_EN = {
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'can', 'and', 'or', 'but', 'in', 'on', 'at',
    'to', 'for', 'of', 'with', 'by', 'from', 'it', 'this', 'that',
}

STOP_WORDS = STOP_WORDS_KO | STOP_WORDS_EN


@dataclass
class EpisodeMemory:
    """에피소드 메모리 — 저장된 에피소드 정보"""
    episode_id: str
    content: str
    sentences: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    stored_at: str = ''
    metadata: dict = field(default_factory=dict)


@dataclass
class MemoryResult:
    """검색 결과 — 매칭된 에피소드 정보"""
    episode_id: str
    matched_text: str
    relevance: float
    context: str


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분할합니다."""
    if not text or not text.strip():
        return []

    # 문장 부호 기준 분할
    sentences = re.split(r'(?<=[.!?。！？])\s*', text.strip())
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


def _extract_keywords(text: str) -> list[str]:
    """텍스트에서 키워드를 추출합니다 (불용어 제외)."""
    if not text:
        return []

    words = re.findall(r'[a-zA-Z가-힣0-9]+', text.lower())
    keywords = []
    seen = set()
    for w in words:
        if (
            len(w) >= MIN_KEYWORD_LENGTH
            and w not in STOP_WORDS
            and w not in seen
        ):
            seen.add(w)
            keywords.append(w)
    return keywords


class PodcastMemoryService:
    """에피소드 콘텐츠 인메모리 저장 + 키워드 매칭 검색"""

    def __init__(self):
        # episode_id → EpisodeMemory
        self._store: dict[str, EpisodeMemory] = {}

    def store_episode(
        self,
        episode_id: str,
        content: str,
        metadata: dict = None,
    ) -> EpisodeMemory:
        """에피소드를 메모리에 저장합니다.

        Args:
            episode_id: 에피소드 고유 ID
            content: 에피소드 전체 텍스트
            metadata: 추가 메타데이터 (제목, 날짜 등)

        Returns:
            EpisodeMemory: 저장된 에피소드 메모리

        Raises:
            ValueError: episode_id나 content가 비어있을 때
        """
        if not episode_id or not episode_id.strip():
            raise ValueError("episode_id는 필수입니다")

        if not content or not content.strip():
            raise ValueError("content는 필수입니다")

        sentences = _split_sentences(content)
        keywords = _extract_keywords(content)

        memory = EpisodeMemory(
            episode_id=episode_id.strip(),
            content=content.strip(),
            sentences=sentences,
            keywords=keywords,
            stored_at=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
        )

        self._store[episode_id.strip()] = memory
        logger.info(
            f"에피소드 저장: id={episode_id}, "
            f"문장={len(sentences)}개, 키워드={len(keywords)}개"
        )
        return memory

    def search_podcast_memory(self, query: str) -> list[MemoryResult]:
        """저장된 에피소드에서 키워드 매칭 기반으로 검색합니다.

        Args:
            query: 검색 쿼리 텍스트

        Returns:
            MemoryResult 리스트 (관련도 내림차순, 최대 MAX_SEARCH_RESULTS개)

        Raises:
            ValueError: query가 비어있을 때
        """
        if not query or not query.strip():
            raise ValueError("query는 필수입니다")

        query_keywords = _extract_keywords(query)
        if not query_keywords:
            return []

        results = []

        for episode_id, memory in self._store.items():
            # 키워드 매칭 점수 계산 (부분 매칭 — 조사 등 접미사 허용)
            content_lower = memory.content.lower()
            matching_keywords = [
                kw for kw in query_keywords if kw in content_lower
            ]

            if not matching_keywords:
                continue

            # 관련도: 매칭된 키워드 비율
            relevance = round(
                len(matching_keywords) / len(query_keywords), 2
            )

            # 가장 관련 있는 문장 찾기
            matched_text, context = self._find_best_match(
                memory.sentences, matching_keywords
            )

            results.append(MemoryResult(
                episode_id=episode_id,
                matched_text=matched_text,
                relevance=relevance,
                context=context,
            ))

        # 관련도 내림차순 정렬
        results.sort(key=lambda r: r.relevance, reverse=True)
        return results[:MAX_SEARCH_RESULTS]

    def _find_best_match(
        self,
        sentences: list[str],
        keywords: list[str],
    ) -> tuple[str, str]:
        """문장들 중 키워드와 가장 잘 매칭되는 문장을 찾습니다."""
        if not sentences:
            return '', ''

        best_sentence = ''
        best_score = 0
        best_index = 0

        for i, sentence in enumerate(sentences):
            sentence_lower = sentence.lower()
            score = sum(1 for kw in keywords if kw in sentence_lower)
            if score > best_score:
                best_score = score
                best_sentence = sentence
                best_index = i

        # 컨텍스트: 앞뒤 문장 포함
        context_parts = []
        if best_index > 0:
            context_parts.append(sentences[best_index - 1])
        context_parts.append(best_sentence)
        if best_index < len(sentences) - 1:
            context_parts.append(sentences[best_index + 1])

        context = ' '.join(context_parts)
        return best_sentence or sentences[0], context

    def get_episode(self, episode_id: str) -> EpisodeMemory | None:
        """특정 에피소드 메모리를 반환합니다."""
        return self._store.get(episode_id)

    def list_episodes(self) -> list[str]:
        """저장된 에피소드 ID 목록을 반환합니다."""
        return list(self._store.keys())

    def delete_episode(self, episode_id: str) -> bool:
        """에피소드를 삭제합니다."""
        if episode_id in self._store:
            del self._store[episode_id]
            logger.info(f"에피소드 삭제: id={episode_id}")
            return True
        return False

    def clear(self) -> int:
        """모든 에피소드를 삭제합니다."""
        count = len(self._store)
        self._store.clear()
        logger.info(f"메모리 초기화: {count}개 삭제")
        return count


# 싱글턴 인스턴스
podcast_memory_service = PodcastMemoryService()
