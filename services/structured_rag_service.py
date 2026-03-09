"""Structured RAG 서비스

구조화된 검색-증강 생성(RAG) 파이프라인을 제공합니다.
문서 청킹, 키워드 검색, 컨텍스트 빌드, 응답 포맷 기능을 포함합니다.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class RAGChunk:
    """문서 청크"""
    chunk_id: str                       # 청크 고유 ID
    content: str                        # 청크 텍스트
    metadata: dict = field(default_factory=dict)  # 메타데이터
    embedding_hint: str = ''            # 키워드 기반 의사 임베딩


@dataclass
class RAGContext:
    """RAG 컨텍스트"""
    query: str                          # 검색 질의
    chunks: list[RAGChunk] = field(default_factory=list)  # 선택된 청크
    total_tokens: int = 0               # 총 토큰 수 (추정)


@dataclass
class RAGResponse:
    """RAG 응답"""
    answer: str                         # 생성된 답변
    sources: list[str] = field(default_factory=list)  # 출처 목록
    confidence: float = 0.0            # 신뢰도 (0~1)


# ── 문장 구분 패턴 ───────────────────────────────────────────
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?。！？])\s+')

# ── 토큰 수 추정 (한국어 ~2~3토큰/자, 영어 ~1.3토큰/단어) ──
def _estimate_tokens(text: str) -> int:
    """텍스트의 토큰 수 추정"""
    if not text:
        return 0
    # 간단 추정: 글자 수 기준 (한국어 평균 ~2토큰/자)
    return max(1, len(text.split()) + len(text) // 3)


def _extract_keywords(text: str) -> list[str]:
    """텍스트에서 키워드 추출 (2자 이상 토큰)"""
    tokens = re.findall(r'[\w가-힣]+', text.lower())
    return [t for t in tokens if len(t) >= 2]


def chunk_document(
    text: str,
    chunk_size: int = 200,
    overlap: int = 50,
) -> list[RAGChunk]:
    """문서를 청크로 분할

    문장 단위로 분할하되, chunk_size(글자 수)를 초과하지 않도록 합니다.
    인접 청크 간 overlap 글자만큼 겹침을 유지합니다.

    Args:
        text: 원본 문서 텍스트
        chunk_size: 청크 최대 글자 수
        overlap: 청크 간 겹침 글자 수

    Returns:
        RAGChunk 목록
    """
    if not text or not text.strip():
        return []

    # 문장 단위 분리
    sentences = _SENTENCE_SPLIT.split(text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    chunks: list[RAGChunk] = []
    current_text = ''
    sentence_idx = 0

    while sentence_idx < len(sentences):
        sentence = sentences[sentence_idx]

        # 현재 청크에 추가해도 chunk_size를 넘지 않는 경우
        if not current_text:
            current_text = sentence
            sentence_idx += 1
        elif len(current_text) + len(sentence) + 1 <= chunk_size:
            current_text += ' ' + sentence
            sentence_idx += 1
        else:
            # 현재 청크 저장
            keywords = _extract_keywords(current_text)
            chunks.append(RAGChunk(
                chunk_id=uuid.uuid4().hex[:8],
                content=current_text,
                metadata={'chunk_index': len(chunks), 'char_count': len(current_text)},
                embedding_hint=' '.join(keywords[:10]),
            ))

            # 오버랩 처리: 마지막 overlap 글자만큼 유지
            if overlap > 0 and len(current_text) > overlap:
                current_text = current_text[-overlap:]
            else:
                current_text = ''
            # sentence_idx는 증가하지 않음 (현재 문장 다시 시도)

    # 마지막 청크 저장
    if current_text:
        keywords = _extract_keywords(current_text)
        chunks.append(RAGChunk(
            chunk_id=uuid.uuid4().hex[:8],
            content=current_text,
            metadata={'chunk_index': len(chunks), 'char_count': len(current_text)},
            embedding_hint=' '.join(keywords[:10]),
        ))

    return chunks


def search_chunks(
    chunks: list[RAGChunk],
    query: str,
    top_k: int = 5,
) -> list[RAGChunk]:
    """키워드 매칭 기반 청크 검색

    Args:
        chunks: 검색 대상 청크 목록
        query: 검색 질의
        top_k: 상위 K개 반환

    Returns:
        관련성 높은 청크 목록
    """
    if not chunks or not query:
        return []

    query_keywords = set(_extract_keywords(query))
    if not query_keywords:
        return chunks[:top_k]

    # 각 청크의 키워드 매칭 점수 계산
    scored: list[tuple[float, RAGChunk]] = []
    for chunk in chunks:
        chunk_keywords = set(_extract_keywords(chunk.content))
        if not chunk_keywords:
            scored.append((0.0, chunk))
            continue

        # Jaccard 유사도 변형: 교집합 / 쿼리 키워드 수
        intersection = query_keywords & chunk_keywords
        score = len(intersection) / len(query_keywords) if query_keywords else 0.0
        scored.append((score, chunk))

    # 점수 내림차순 정렬
    scored.sort(key=lambda x: x[0], reverse=True)

    return [chunk for _, chunk in scored[:top_k]]


def build_context(
    chunks: list[RAGChunk],
    max_tokens: int = 4000,
) -> RAGContext:
    """청크로부터 RAG 컨텍스트 빌드

    토큰 제한 내에서 최대한 많은 청크를 포함합니다.

    Args:
        chunks: 선택된 청크 목록
        max_tokens: 최대 토큰 수

    Returns:
        빌드된 RAGContext
    """
    selected: list[RAGChunk] = []
    total_tokens = 0

    for chunk in chunks:
        chunk_tokens = _estimate_tokens(chunk.content)
        if total_tokens + chunk_tokens > max_tokens:
            break
        selected.append(chunk)
        total_tokens += chunk_tokens

    return RAGContext(
        query='',
        chunks=selected,
        total_tokens=total_tokens,
    )


def format_response(
    context: RAGContext,
    answer_text: str,
) -> RAGResponse:
    """RAG 응답 포맷

    컨텍스트의 출처를 자동으로 첨부하고 신뢰도를 계산합니다.

    Args:
        context: RAG 컨텍스트
        answer_text: 생성된 답변 텍스트

    Returns:
        포맷된 RAGResponse
    """
    # 출처 추출 (청크 메타데이터 또는 청크 ID)
    sources: list[str] = []
    for chunk in context.chunks:
        source = chunk.metadata.get('source', '')
        if source:
            sources.append(source)
        else:
            sources.append(f'chunk:{chunk.chunk_id}')

    # 신뢰도: 청크 수 기반 (많을수록 높음, 최대 1.0)
    confidence = min(1.0, len(context.chunks) * 0.2) if context.chunks else 0.0

    return RAGResponse(
        answer=answer_text,
        sources=sources,
        confidence=round(confidence, 2),
    )
