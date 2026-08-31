"""
Corrective RAG (CRAG) — 검색 품질 자동 평가 및 교정 시스템

RAG 검색 결과의 품질을 LLM으로 평가하고,
기준 미달 시 쿼리를 재구성하여 재검색하거나 웹 검색으로 폴백합니다.

비용 영향:
  - 정상 품질(correct): 추가 LLM 호출 없음
  - 부분 품질(ambiguous): LLM 호출 +2 (품질 평가 + 쿼리 재구성)
  - 불량 품질(incorrect): LLM 호출 +1 (품질 평가) + 웹 검색 API 호출
"""
import json
import logging
import re
from typing import Dict, List, Any

import litellm

logger = logging.getLogger(__name__)

# 품질 평가 및 쿼리 재구성에 사용할 빠른 모델
_DEFAULT_MODEL = "cliproxy/gpt-5.6-sol"

# 품질 결정 임계값
_SCORE_CORRECT_THRESHOLD = 0.7    # 이상이면 correct
_SCORE_AMBIGUOUS_THRESHOLD = 0.4  # 이상이면 ambiguous, 미만이면 incorrect

# 품질 평가 프롬프트
_QUALITY_EVAL_PROMPT = """다음 쿼리에 대해 검색된 문서 청크들이 얼마나 관련성 있는지 평가하세요.

**쿼리**: {query}

**검색된 청크 목록**:
{chunks_text}

**평가 기준**:
- 각 청크에 대해 쿼리와의 관련도 점수(0.0~1.0)를 부여하세요
- 1.0: 쿼리에 완벽하게 답변하는 정보 포함
- 0.7~0.9: 쿼리와 높은 관련성, 유용한 정보 포함
- 0.4~0.6: 쿼리와 부분적으로 관련, 일부 유용한 정보
- 0.1~0.3: 쿼리와 약한 관련성, 간접 정보
- 0.0: 쿼리와 무관

**출력 형식 (JSON만, 다른 텍스트 없음)**:
{{"chunk_scores": [점수0, 점수1, ...], "feedback": "품질이 부족한 이유 한 문장 (관련 정보 없으면 작성)"}}

청크 개수({chunk_count}개)와 정확히 같은 수의 점수를 출력하세요."""

# 쿼리 재구성 프롬프트
_QUERY_REFORMULATE_PROMPT = """다음 쿼리로 검색했지만 관련 문서를 찾지 못했습니다.
더 나은 검색 결과를 위해 쿼리를 재구성해주세요.

**원본 쿼리**: {original_query}
**실패 피드백**: {feedback}

**재구성 원칙**:
- 더 구체적이거나 다른 각도로 접근
- 동의어나 관련 키워드 활용
- 지나치게 광범위하거나 모호한 표현 제거

**출력 형식 (JSON만)**:
{{"reformulated_query": "재구성된 쿼리 문자열"}}"""


def evaluate_retrieval_quality(
    query: str,
    chunks: List[Dict[str, Any]],
    model: str = None,
) -> Dict[str, Any]:
    """검색된 청크들의 쿼리 관련성을 LLM으로 평가합니다.

    Args:
        query: 사용자 쿼리
        chunks: 검색된 청크 목록. 각 항목은 {"text": str, "metadata": dict, ...} 형식
        model: 평가에 사용할 LLM 모델 ID (None이면 기본 모델 사용)

    Returns:
        {
            "overall_score": float (0~1) — 전체 품질 점수,
            "relevant_chunks": List[int] — 관련 청크 인덱스 목록,
            "irrelevant_chunks": List[int] — 비관련 청크 인덱스 목록,
            "decision": str — "correct" | "ambiguous" | "incorrect",
            "feedback": str — 품질 부족 이유 (관련성 낮을 때만),
        }
    """
    if not chunks:
        return {
            "overall_score": 0.0,
            "relevant_chunks": [],
            "irrelevant_chunks": [],
            "decision": "incorrect",
            "feedback": "검색된 청크가 없습니다.",
        }

    eval_model = model or _DEFAULT_MODEL

    # 청크 텍스트 포맷팅 (너무 길면 잘라냄)
    chunks_text_parts = []
    for i, chunk in enumerate(chunks):
        text = chunk.get("text", "")[:400]
        source = chunk.get("metadata", {}).get("filename", "문서")
        chunks_text_parts.append(f"[청크 {i} - {source}]: {text}")
    chunks_text = "\n\n".join(chunks_text_parts)

    prompt = _QUALITY_EVAL_PROMPT.format(
        query=query,
        chunks_text=chunks_text,
        chunk_count=len(chunks),
    )

    chunk_scores = []
    feedback = ""
    try:
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs(
            eval_model,
            prompt,
            style_id="summary",
            modifiers={"length": "short"},
        )
        kwargs["max_tokens"] = 300
        response = litellm.completion(**kwargs)
        raw = response.choices[0].message.content.strip()

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            chunk_scores = data.get("chunk_scores", [])
            feedback = data.get("feedback", "")

    except (json.JSONDecodeError, KeyError, IndexError, Exception) as e:
        logger.warning(f"CRAG 품질 평가 LLM 호출 실패, 중간 점수로 폴백: {e}")

    # 점수 수가 불일치하면 중간 점수로 채움
    if len(chunk_scores) != len(chunks):
        logger.warning(
            f"CRAG 점수 수 불일치 (기대: {len(chunks)}, 실제: {len(chunk_scores)}), "
            "0.5로 채움"
        )
        chunk_scores = [0.5] * len(chunks)

    # float 변환 (안전하게)
    safe_scores = []
    for s in chunk_scores:
        try:
            safe_scores.append(float(s))
        except (ValueError, TypeError):
            safe_scores.append(0.5)

    # 관련 / 비관련 청크 분류
    relevant_chunks = [i for i, s in enumerate(safe_scores) if s >= _SCORE_AMBIGUOUS_THRESHOLD]
    irrelevant_chunks = [i for i, s in enumerate(safe_scores) if s < _SCORE_AMBIGUOUS_THRESHOLD]

    # 전체 점수 = 관련 청크 비율 가중 평균
    overall_score = sum(safe_scores) / len(safe_scores) if safe_scores else 0.0

    # 결정
    if overall_score >= _SCORE_CORRECT_THRESHOLD:
        decision = "correct"
    elif overall_score >= _SCORE_AMBIGUOUS_THRESHOLD:
        decision = "ambiguous"
    else:
        decision = "incorrect"

    logger.info(
        f"CRAG 품질 평가: 점수={overall_score:.2f}, 결정={decision}, "
        f"관련={len(relevant_chunks)}/{len(chunks)}"
    )

    return {
        "overall_score": overall_score,
        "relevant_chunks": relevant_chunks,
        "irrelevant_chunks": irrelevant_chunks,
        "decision": decision,
        "feedback": feedback,
    }


def reformulate_query(
    original_query: str,
    feedback: str,
    model: str = None,
) -> str:
    """검색 피드백을 반영하여 쿼리를 재구성합니다.

    Args:
        original_query: 원본 사용자 쿼리
        feedback: 품질 평가에서 얻은 피드백 (실패 원인)
        model: 사용할 LLM 모델 ID

    Returns:
        재구성된 쿼리 문자열. 실패 시 원본 쿼리 반환.
    """
    reformat_model = model or _DEFAULT_MODEL

    prompt = _QUERY_REFORMULATE_PROMPT.format(
        original_query=original_query,
        feedback=feedback or "관련 문서를 찾지 못했습니다.",
    )

    try:
        from services.core.ai_service import _build_completion_kwargs
        kwargs = _build_completion_kwargs(
            reformat_model,
            prompt,
            style_id="summary",
            modifiers={"length": "short"},
        )
        kwargs["max_tokens"] = 150
        response = litellm.completion(**kwargs)
        raw = response.choices[0].message.content.strip()

        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
            reformulated = data.get("reformulated_query", "").strip()
            if reformulated:
                logger.info(f"CRAG 쿼리 재구성: '{original_query}' → '{reformulated}'")
                return reformulated

    except (json.JSONDecodeError, KeyError, Exception) as e:
        logger.warning(f"CRAG 쿼리 재구성 실패, 원본 쿼리 사용: {e}")

    return original_query


def web_search_fallback(
    query: str,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    """RAG 검색이 실패(incorrect)할 때 웹 검색으로 폴백합니다.

    Args:
        query: 검색할 쿼리
        max_results: 최대 검색 결과 수

    Returns:
        청크 형식으로 변환된 웹 검색 결과 목록.
        각 항목은 {"text": str, "metadata": dict, "distance": float, "source": "web"} 형식.
        웹 검색 불가(API 키 없음 등)이면 빈 리스트 반환.
    """
    try:
        from services.data import web_search_service
        results = web_search_service.search(query, max_results=max_results)
    except ImportError:
        try:
            import services.data.web_search_service as web_search_service
            results = web_search_service.search(query, max_results=max_results)
        except Exception as e:
            logger.warning(f"웹 검색 서비스 import 실패: {e}")
            return []
    except Exception as e:
        logger.warning(f"CRAG 웹 검색 폴백 실패: {e}")
        return []

    if not results:
        logger.info("CRAG 웹 검색 폴백: 결과 없음")
        return []

    # 웹 검색 결과를 RAG 청크 형식으로 변환
    chunks = []
    for r in results:
        title = r.get("title", "")
        url = r.get("url", "")
        content = r.get("content", "")
        score = r.get("score", 0.5)

        # 텍스트 구성: 제목 + 내용
        text_parts = []
        if title:
            text_parts.append(f"제목: {title}")
        if content:
            text_parts.append(content)
        text = "\n".join(text_parts) if text_parts else content

        chunks.append({
            "text": text,
            "metadata": {
                "filename": title or "웹 검색 결과",
                "source": "web",
                "url": url,
            },
            # 웹 검색 점수를 거리 역수로 변환 (높은 score → 낮은 distance)
            "distance": max(0.0, 1.0 - float(score)),
            "source": "web",  # 최상위에도 표시 (구분 편의)
        })

    logger.info(f"CRAG 웹 검색 폴백: {len(chunks)}개 결과 청크 변환 완료")
    return chunks


def _filter_relevant_chunks(
    chunks: List[Dict[str, Any]],
    eval_result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """평가 결과에서 관련 청크만 필터링합니다.

    ambiguous 판정 시 관련 청크만 남기고 비관련 청크를 제거하여
    최종 품질을 개선합니다.

    Args:
        chunks: 원본 청크 리스트
        eval_result: evaluate_retrieval_quality()의 결과

    Returns:
        관련 청크만 포함된 리스트 (비어있으면 원본 반환)
    """
    relevant_indices = eval_result.get("relevant_chunks", [])
    if not relevant_indices:
        return chunks

    filtered = [chunks[i] for i in relevant_indices if i < len(chunks)]
    return filtered if filtered else chunks


def corrective_search(
    query: str,
    chunks: List[Dict[str, Any]],
    vector_store: Any,
    user_id: str,
    top_k: int = 5,
    max_retries: int = 2,
    model: str = None,
) -> List[Dict[str, Any]]:
    """CRAG 강화 루프: 품질 평가 → 관련 청크 필터링 → 재검색 → 웹 폴백.

    v2 개선사항:
    - max_retries 기본값 1 → 2 (재시도 기회 증가)
    - ambiguous 시 관련 청크 필터링 적용
    - incorrect 시 웹 폴백 + 쿼리 재구성 후 재검색 순차 시도
    - 재검색 루프에서 correct 도달 시 관련 청크만 반환

    Args:
        query: 원본 쿼리
        chunks: 초기 검색 결과 청크 목록
        vector_store: ChromaDB 벡터 스토어 인스턴스
        user_id: 사용자 ID (벡터 스토어 검색에 필요)
        top_k: 최종 반환할 청크 수
        max_retries: 최대 재검색 횟수 (비용 폭증 방지, 기본 2)
        model: 품질 평가/쿼리 재구성에 사용할 LLM

    Returns:
        최종 청크 목록 (correct이면 원본, ambiguous이면 필터링+재검색 결과,
        incorrect이면 웹 검색+재검색 결과. 모두 실패하면 원본 반환).
    """
    eval_result = evaluate_retrieval_quality(query, chunks, model=model)
    decision = eval_result["decision"]

    if decision == "correct":
        logger.info("CRAG: 품질 correct, 원본 청크 사용")
        return chunks

    if decision == "incorrect":
        logger.info("CRAG: 품질 incorrect, 웹 검색 폴백 시도")

        # 1차: 웹 검색 폴백
        web_chunks = web_search_fallback(query, max_results=top_k)
        if web_chunks:
            return web_chunks

        # 2차: 쿼리 재구성 후 웹 검색 재시도
        feedback = eval_result.get("feedback", "")
        new_query = reformulate_query(query, feedback, model=model)
        if new_query != query:
            logger.info(f"CRAG: 재구성 쿼리로 웹 검색 재시도: '{new_query}'")
            web_chunks2 = web_search_fallback(new_query, max_results=top_k)
            if web_chunks2:
                return web_chunks2

            # 3차: 재구성 쿼리로 벡터 스토어 재검색
            try:
                new_chunks = vector_store.search(user_id, new_query, top_k)
                if new_chunks:
                    re_eval = evaluate_retrieval_quality(new_query, new_chunks, model=model)
                    if re_eval["decision"] != "incorrect":
                        return _filter_relevant_chunks(new_chunks, re_eval)
            except Exception as e:
                logger.warning(f"CRAG incorrect 재검색 실패: {e}")

        logger.warning("CRAG: 모든 폴백 실패, 원본 청크 반환")
        return chunks

    # decision == "ambiguous": 관련 청크 필터링 + 쿼리 재구성 후 재검색
    retry_count = 0
    current_chunks = _filter_relevant_chunks(chunks, eval_result)
    current_query = query
    feedback = eval_result.get("feedback", "")
    best_chunks = current_chunks
    best_score = eval_result.get("overall_score", 0.0)

    while retry_count < max_retries and decision == "ambiguous":
        logger.info(f"CRAG: 품질 ambiguous, 쿼리 재구성 후 재검색 (시도 {retry_count + 1}/{max_retries})")

        new_query = reformulate_query(current_query, feedback, model=model)

        try:
            new_chunks = vector_store.search(user_id, new_query, top_k)
        except Exception as e:
            logger.warning(f"CRAG 재검색 실패: {e}")
            break

        if not new_chunks:
            logger.info("CRAG 재검색: 결과 없음, 웹 폴백 시도")
            web_chunks = web_search_fallback(new_query, max_results=top_k)
            if web_chunks:
                return web_chunks
            break

        re_eval = evaluate_retrieval_quality(new_query, new_chunks, model=model)
        decision = re_eval["decision"]
        score = re_eval.get("overall_score", 0.0)

        # 더 좋은 결과가 나왔으면 업데이트
        if score > best_score:
            best_chunks = _filter_relevant_chunks(new_chunks, re_eval)
            best_score = score

        if decision == "correct":
            return _filter_relevant_chunks(new_chunks, re_eval)

        current_chunks = new_chunks
        feedback = re_eval.get("feedback", "")
        current_query = new_query
        retry_count += 1

    # 루프 종료 — 가장 좋은 결과 반환
    return best_chunks
