"""AI 프롬프트 선택 컨텍스트(RAG/웹/메모리) 빌더."""
import concurrent.futures
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def build_optional_prompt_contexts(
    content: str,
    user_id: Optional[str] = None,
    web_search: bool = False,
) -> Tuple[Optional[str], Optional[str], list, Optional[str], Optional[str]]:
    """create_content와 streaming 경로가 공유하는 선택 컨텍스트를 구성합니다."""
    from config import RAG_ENABLED, RAG_TOP_K, WEB_SEARCH_ENABLED

    def _build_rag():
        if not (RAG_ENABLED and user_id):
            return None
        from services.rag import context_builder
        return context_builder.build_context(user_id, content[:500], top_k=RAG_TOP_K)

    def _build_web():
        if not (web_search or WEB_SEARCH_ENABLED):
            return None, []
        from services.data.web_search_service import extract_grounding_context
        grounding = extract_grounding_context(content[:300])
        if grounding['enabled']:
            return grounding['context_text'], grounding['results']
        return None, []

    def _build_style_memory():
        if not user_id:
            return None
        from services.data.style_memory_service import get_profile, build_style_context
        profile = get_profile(user_id)
        return build_style_context(profile) or None

    def _build_ai_memory():
        if not user_id:
            return None
        from services.data.memory_service import memory_service as _mem_svc
        return _mem_svc.build_prompt_context(user_id) or None

    rag_context = None
    web_context = None
    web_sources = []
    style_memory_context = None
    memory_context = None

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ctx_executor:
        rag_f = ctx_executor.submit(_build_rag)
        web_f = ctx_executor.submit(_build_web)
        sm_f = ctx_executor.submit(_build_style_memory)
        mem_f = ctx_executor.submit(_build_ai_memory)

        try:
            rag_context = rag_f.result()
        except Exception as rag_err:
            logger.warning(f"RAG 컨텍스트 빌드 실패 (무시): {rag_err}")
        try:
            web_context, web_sources = web_f.result()
            if web_sources:
                logger.info(f"웹 검색 보강: {len(web_sources)}개 결과 주입")
        except Exception as ws_err:
            logger.warning(f"웹 검색 보강 실패 (무시): {ws_err}")
        try:
            style_memory_context = sm_f.result()
        except Exception as sm_err:
            logger.warning(f"스타일 메모리 컨텍스트 빌드 실패 (무시): {sm_err}")
        try:
            memory_context = mem_f.result()
        except Exception as mem_err:
            logger.warning(f"메모리 컨텍스트 빌드 실패 (무시): {mem_err}")

    return rag_context, web_context, web_sources, style_memory_context, memory_context
