"""
YouTube 영상 Q&A 서비스

영상 자막을 ChromaDB에 벡터화하여 저장하고,
질문에 대해 RAG 기반으로 답변을 생성합니다.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# ChromaDB는 선택적 의존성 — 없으면 기능 비활성화
try:
    import chromadb
    _CHROMA_AVAILABLE = True
except ImportError:
    _CHROMA_AVAILABLE = False
    logger.warning("chromadb가 설치되지 않아 영상 Q&A 기능이 비활성화됩니다.")

# LiteLLM 호출
try:
    from litellm import completion as litellm_completion
    _LITELLM_AVAILABLE = True
except ImportError:
    _LITELLM_AVAILABLE = False
    logger.warning("litellm이 설치되지 않아 영상 Q&A 기능이 비활성화됩니다.")

from services.rag.chunker import chunk_text

# 설정 기본값
DEFAULT_CHUNK_SIZE = 600
DEFAULT_CHUNK_OVERLAP = 80
DEFAULT_TOP_K = 5
MAX_HISTORY_MESSAGES = 10  # 대화 히스토리 최대 보관 수

# 영상 Q&A 전용 ChromaDB 컬렉션 접두사
VIDEO_COLLECTION_PREFIX = "video_qa_"

# LiteLLM 기본 모델 (답변 생성용)
DEFAULT_QA_MODEL = "zhipuai/GLM-4.5-Air"


def _get_chroma_client() -> Optional[Any]:
    """ChromaDB PersistentClient를 반환합니다. 사용 불가 시 None."""
    if not _CHROMA_AVAILABLE:
        return None
    db_path = os.environ.get("CHROMA_DB_PATH", "./data/chroma_db")
    os.makedirs(db_path, exist_ok=True)
    return chromadb.PersistentClient(path=db_path)


def _get_video_collection(client: Any, video_id: str):
    """영상 ID에 해당하는 ChromaDB 컬렉션을 반환합니다."""
    collection_name = f"{VIDEO_COLLECTION_PREFIX}{video_id}"
    return client.get_or_create_collection(name=collection_name)


def is_video_indexed(video_id: str) -> bool:
    """해당 영상 자막이 ChromaDB에 이미 인덱싱되어 있는지 확인합니다."""
    if not _CHROMA_AVAILABLE:
        return False
    try:
        client = _get_chroma_client()
        if client is None:
            return False
        collection = _get_video_collection(client, video_id)
        return collection.count() > 0
    except Exception as e:
        logger.error(f"영상 인덱싱 확인 실패 (video_id={video_id}): {e}")
        return False


def index_video_transcript(video_id: str, transcript: str) -> bool:
    """
    영상 자막을 청킹하여 ChromaDB에 저장합니다.

    Args:
        video_id: YouTube 영상 ID
        transcript: 전체 자막 텍스트

    Returns:
        성공 여부
    """
    if not _CHROMA_AVAILABLE:
        logger.warning("chromadb가 없어 인덱싱을 건너뜁니다.")
        return False

    if not transcript or not transcript.strip():
        logger.warning(f"빈 자막으로 인덱싱 불가 (video_id={video_id})")
        return False

    try:
        client = _get_chroma_client()
        if client is None:
            return False

        collection = _get_video_collection(client, video_id)

        # 기존 데이터가 있으면 삭제 후 재인덱싱
        if collection.count() > 0:
            all_ids = collection.get()["ids"]
            if all_ids:
                collection.delete(ids=all_ids)
            logger.info(f"기존 인덱스 삭제 후 재인덱싱 (video_id={video_id})")

        # 자막 청킹
        chunks = chunk_text(
            transcript,
            chunk_size=DEFAULT_CHUNK_SIZE,
            overlap=DEFAULT_CHUNK_OVERLAP,
        )

        if not chunks:
            logger.warning(f"청크 생성 실패 (video_id={video_id})")
            return False

        # ChromaDB에 저장
        ids = [f"{video_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "video_id": video_id,
                "chunk_index": i,
                "timestamp_start": 0.0,  # 타임스탬프 정보가 없을 경우 0
            }
            for i in range(len(chunks))
        ]

        collection.add(documents=chunks, ids=ids, metadatas=metadatas)
        logger.info(f"영상 인덱싱 완료 (video_id={video_id}, chunks={len(chunks)})")
        return True

    except Exception as e:
        logger.error(f"영상 인덱싱 실패 (video_id={video_id}): {e}")
        return False


def search_relevant_chunks(
    video_id: str,
    question: str,
    top_k: int = DEFAULT_TOP_K,
) -> List[Dict[str, Any]]:
    """
    질문과 관련된 자막 청크를 ChromaDB에서 검색합니다.

    Args:
        video_id: YouTube 영상 ID
        question: 사용자 질문
        top_k: 반환할 최대 청크 수

    Returns:
        관련 청크 목록 [{"text": str, "chunk_index": int, "distance": float}]
    """
    if not _CHROMA_AVAILABLE:
        return []

    try:
        client = _get_chroma_client()
        if client is None:
            return []

        collection = _get_video_collection(client, video_id)
        count = collection.count()
        if count == 0:
            return []

        results = collection.query(
            query_texts=[question],
            n_results=min(top_k, count),
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            chunks.append({
                "text": doc,
                "chunk_index": meta.get("chunk_index", 0),
                "distance": dist,
            })

        return chunks

    except Exception as e:
        logger.error(f"청크 검색 실패 (video_id={video_id}): {e}")
        return []


def answer_question(
    video_id: str,
    question: str,
    history: Optional[List[Dict[str, str]]] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    영상 자막 기반으로 질문에 답변을 생성합니다.

    Args:
        video_id: YouTube 영상 ID
        question: 사용자 질문
        history: 대화 히스토리 [{"role": "user"|"assistant", "content": str}]
        model: LiteLLM 모델 ID (없으면 기본값 사용)

    Returns:
        {"answer": str, "sources": [{"text": str, "relevance": float}]}
    """
    if not _LITELLM_AVAILABLE:
        return {
            "answer": "AI 서비스를 사용할 수 없습니다. litellm 설치를 확인해주세요.",
            "sources": [],
        }

    # 관련 청크 검색
    top_k = int(os.environ.get("RAG_TOP_K", DEFAULT_TOP_K))
    relevant_chunks = search_relevant_chunks(video_id, question, top_k=top_k)

    # 청크가 없으면 인덱싱이 안 된 상태
    if not relevant_chunks:
        return {
            "answer": "영상 자막 데이터를 찾을 수 없습니다. 먼저 영상을 분석해주세요.",
            "sources": [],
        }

    # 컨텍스트 구성
    context_parts = []
    for i, chunk in enumerate(relevant_chunks, 1):
        context_parts.append(f"[자막 구간 {i}]\n{chunk['text']}")
    context_text = "\n\n".join(context_parts)

    # 시스템 프롬프트
    system_prompt = (
        "당신은 YouTube 영상 내용 전문가입니다.\n"
        "아래에 제공된 영상 자막 내용만을 바탕으로 사용자 질문에 답변하세요.\n"
        "자막에 없는 내용은 '영상에서 해당 내용을 찾을 수 없습니다'라고 명확하게 답하세요.\n"
        "추측하거나 자막 외 정보를 추가하지 마세요.\n\n"
        f"[영상 자막 내용]\n{context_text}"
    )

    # 대화 히스토리 구성 (최대 MAX_HISTORY_MESSAGES개)
    messages = [{"role": "system", "content": system_prompt}]

    if history:
        trimmed_history = history[-(MAX_HISTORY_MESSAGES):]
        for msg in trimmed_history:
            if msg.get("role") in ("user", "assistant") and msg.get("content"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    # LiteLLM 호출
    qa_model = model or DEFAULT_QA_MODEL
    try:
        # Zhipu AI 모델은 별도 api_base 필요
        kwargs: Dict[str, Any] = {
            "model": qa_model,
            "messages": messages,
            "max_tokens": 1024,
            "temperature": 0.3,
        }
        if qa_model.startswith("zhipuai/"):
            kwargs["api_base"] = "https://open.bigmodel.cn/api/paas/v4/"
            api_key = os.environ.get("ZHIPUAI_API_KEY", "")
            if api_key:
                kwargs["api_key"] = api_key

        response = litellm_completion(**kwargs)
        answer = response.choices[0].message.content or ""

    except Exception as e:
        logger.error(f"Q&A 답변 생성 실패 (video_id={video_id}): {e}")
        return {
            "answer": "답변 생성 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
            "sources": [],
        }

    # 소스 정보 구성 (거리가 낮을수록 더 관련성 높음)
    sources = [
        {
            "text": chunk["text"][:200],  # 미리보기용 200자 잘라내기
            "relevance": round(1.0 - min(chunk["distance"], 1.0), 3),
        }
        for chunk in relevant_chunks
    ]

    return {"answer": answer.strip(), "sources": sources}
