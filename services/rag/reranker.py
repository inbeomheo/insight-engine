"""
LLM 기반 리랭커 — 검색된 청크들을 쿼리와의 관련도로 재정렬
CrossEncoder ML 모델 없이 LLM을 활용하여 무거운 의존성 회피
"""
import json
import logging
import re

import litellm

logger = logging.getLogger(__name__)

# 리랭킹용 모델 (빠른 응답 우선)
_DEFAULT_MODEL = "cliproxy/gpt-5.6-sol"

_RERANK_PROMPT = """다음 쿼리에 대해 각 문서 청크의 관련도 점수(0~10)를 평가하세요.

**쿼리**: {query}

**문서 청크 목록**:
{chunks_text}

**평가 기준**:
- 10: 쿼리에 완벽하게 답변하는 정보 포함
- 7~9: 쿼리와 높은 관련성, 유용한 정보 포함
- 4~6: 쿼리와 부분적으로 관련, 일부 유용한 정보
- 1~3: 쿼리와 약한 관련성, 간접 정보
- 0: 쿼리와 무관

**출력 형식 (JSON만, 다른 텍스트 없음)**:
{{"scores": [점수0, 점수1, ...]}}

청크 개수와 정확히 같은 수의 점수를 출력하세요."""


def rerank(query: str, chunks: list[dict], top_k: int = 5, model: str = _DEFAULT_MODEL) -> list[dict]:
    """LLM을 사용하여 청크를 쿼리 관련도로 재정렬합니다.

    Args:
        query: 사용자 쿼리
        chunks: 재정렬할 청크 목록. 각 청크는 {"text": str, ...} 형식
        top_k: 상위 몇 개를 반환할지
        model: 사용할 LLM 모델 ID

    Returns:
        관련도 순으로 정렬된 청크 목록 (top_k 개). 각 청크에 "rerank_score" 필드 추가
    """
    if not chunks:
        return []

    # top_k가 청크 수보다 크면 전체 반환
    if len(chunks) <= top_k:
        for chunk in chunks:
            chunk.setdefault("rerank_score", 5.0)
        return chunks

    # 청크 텍스트 포맷팅 (너무 길면 잘라냄)
    chunks_text_parts = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")[:500]  # 최대 500자
        chunks_text_parts.append(f"[청크 {i}]: {text}")
    chunks_text = "\n\n".join(chunks_text_parts)

    prompt = _RERANK_PROMPT.format(query=query, chunks_text=chunks_text)

    try:
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs(
            model,
            prompt,
            style_id="summary",
            modifiers={"length": "short"},
        )
        kwargs["max_tokens"] = 200
        response = litellm.completion(**kwargs)
        raw = response.choices[0].message.content.strip()

        # JSON 추출
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            scores = data.get("scores", [])
        else:
            scores = []

    except (json.JSONDecodeError, KeyError, IndexError, Exception) as e:
        logger.warning(f"리랭킹 LLM 호출 실패, 원본 순서 반환: {e}")
        scores = []

    # 점수 적용
    if len(scores) == len(chunks):
        scored_chunks = []
        for chunk, score in zip(chunks, scores):
            chunk_copy = dict(chunk)
            try:
                chunk_copy["rerank_score"] = float(score)
            except (ValueError, TypeError):
                chunk_copy["rerank_score"] = 5.0
            scored_chunks.append(chunk_copy)

        # 점수 내림차순 정렬
        scored_chunks.sort(key=lambda c: c["rerank_score"], reverse=True)
        logger.info(f"리랭킹 완료: {len(chunks)}개 → 상위 {top_k}개 선택")
        return scored_chunks[:top_k]
    else:
        # 점수 수가 맞지 않으면 원본 순서 유지 후 top_k 반환
        logger.warning(f"리랭킹 점수 수 불일치 (기대: {len(chunks)}, 실제: {len(scores)}), 원본 순서 사용")
        for chunk in chunks:
            chunk.setdefault("rerank_score", 5.0)
        return chunks[:top_k]


def rerank_with_fallback(
    query: str,
    chunks: list[dict],
    top_k: int = 5,
    model: str = _DEFAULT_MODEL,
) -> list[dict]:
    """리랭킹을 시도하고 실패 시 거리 기반 정렬로 폴백합니다.

    Args:
        query: 사용자 쿼리
        chunks: 재정렬할 청크 목록
        top_k: 반환할 상위 청크 수
        model: 사용할 LLM 모델 ID

    Returns:
        재정렬된 청크 목록
    """
    try:
        return rerank(query, chunks, top_k, model)
    except Exception as e:
        logger.warning(f"리랭킹 전체 실패, 거리 기반 폴백: {e}")
        # 벡터 거리 기반 정렬 (distance가 낮을수록 관련성 높음)
        sorted_chunks = sorted(chunks, key=lambda c: c.get("distance", 0.5))
        for chunk in sorted_chunks:
            chunk.setdefault("rerank_score", 5.0)
        return sorted_chunks[:top_k]
