"""Product knowledge answers for the in-app support assistant.

The assistant uses the configured OPEN AI/ChatMock model for natural answers and
keeps the small FAQ table as grounding + fallback, not as the primary response
engine.
"""
from __future__ import annotations

import os
from typing import Any

FAQ_ITEMS = [
    {
        "keywords": ["퓨전", "fusion", "교차", "여러", "비교"],
        "title": "퓨전 분석",
        "answer": "퓨전 분석은 2~5개 URL을 한 번에 넣고 공통점·차이점·충돌하는 주장까지 묶어서 하나의 분석 문서로 만드는 기능이야. 단순히 이어붙이는 통합 생성보다 비교/교차분석 성격이 강해.",
    },
    {
        "keywords": ["통합", "합쳐", "combined", "개별"],
        "title": "개별/통합 생성 차이",
        "answer": "개별은 URL마다 결과 카드를 따로 만들고, 통합은 여러 URL을 하나의 문서로 합쳐. 퓨전은 통합보다 한 단계 더 나아가 관점 비교와 인사이트 추출을 강조해.",
    },
    {
        "keywords": ["캘린더", "예약", "발행", "안 보여"],
        "title": "캘린더/예약 발행",
        "answer": "예약 발행과 캘린더 기능은 학습 엔진으로의 방향 전환 과정에서 제거됐어. 지금은 URL/텍스트를 넣어 바로 콘텐츠를 생성하고 학습하는 흐름에 집중하고 있어.",
    },
    {
        "keywords": ["모델", "openrouter", "gpt", "키미", "kimi", "프로바이더", "open ai", "openai", "챗목", "chatmock"],
        "title": "모델/프로바이더",
        "answer": "현재 배포판은 모델 선택 혼선을 줄이기 위해 OPEN AI 하나만 노출해. 내부적으로는 ChatMock sidecar가 GPT-5.3 Codex Spark를 OpenAI 호환 방식으로 호출하는 구조야.",
    },
    {
        "keywords": ["스타일", "출력", "요약", "qna", "q&a", "퀴즈", "quiz", "리텐션"],
        "title": "출력 스타일",
        "answer": "출력 스타일은 요약, Q&A, 퀴즈, 리텐션 카드 4개로 단순화했어. 생성 결과는 바로 학습 노트로 저장해 핵심 개념·태그·인용·관련 노트로 쌓아갈 수 있어.",
    },
    {
        "keywords": ["공유", "링크", "복사", "url"],
        "title": "공유 링크",
        "answer": "공유는 결과 카드의 실제 share URL을 생성해서 복사하는 흐름이야. 복사가 안 되면 브라우저 권한, HTTPS/Basic Auth, 또는 서버의 share page 생성 API 상태를 같이 확인해야 해.",
    },
]


def _completion(**kwargs):
    """Lazy LiteLLM import so local support tests don't require full AI deps."""
    from litellm import completion as litellm_completion

    return litellm_completion(**kwargs)


def _match_faq(message: str) -> tuple[dict[str, Any] | None, float]:
    text = (message or "").lower()
    matched = []
    for item in FAQ_ITEMS:
        score = sum(1 for keyword in item["keywords"] if keyword.lower() in text)
        if score:
            matched.append((score, item))

    if not matched:
        return None, 0.35
    matched.sort(key=lambda pair: pair[0], reverse=True)
    return matched[0][1], min(0.95, 0.55 + 0.15 * matched[0][0])


def _fallback_answer(message: str) -> dict[str, Any]:
    item, confidence = _match_faq(message)
    if item:
        return {
            "answer": item["answer"],
            "matched_topic": item["title"],
            "confidence": confidence,
            "llm_used": False,
            "fallback_used": True,
        }

    return {
        "answer": (
            "인사이트 엔진 기능에 대한 질문이면 내가 바로 설명해줄게. "
            "버그나 불편사항이면 어떤 화면에서 어떤 동작이 문제인지 적어주면 접수해서 GitHub 이슈로 넘길 수 있어."
        ),
        "matched_topic": "general",
        "confidence": 0.35,
        "llm_used": False,
        "fallback_used": True,
    }


def _build_support_prompt(message: str, context: dict[str, Any] | None, matched_item: dict[str, Any] | None) -> str:
    route = (context or {}).get("route") or "/"
    viewport = (context or {}).get("viewport") or {}
    faq_lines = "\n".join(f"- {item['title']}: {item['answer']}" for item in FAQ_ITEMS)
    matched = matched_item["answer"] if matched_item else "관련 FAQ 직접 매칭 없음"

    return f"""너는 Insight Engine 앱 안의 Support Assistant야.
한국어 반말로, 사용자가 이해하기 쉽게 2~5문장으로 답해.

중요 정책:
- 현재 배포판의 AI 프로바이더 표시는 OPEN AI 하나만이다.
- OPEN AI는 내부적으로 ChatMock sidecar를 통해 GPT-5.3 Codex Spark를 호출한다.
- DeepSeek/Ollama/GLM/OpenRouter는 현재 사용자 선택지로 노출하지 않는다.
- 모르면 지어내지 말고, 확인이 필요하다고 말한 뒤 불편사항 접수를 안내해.
- 버그/불편 제보가 섞여 있으면, 답변 뒤에 "원하면 이 내용으로 불편사항 접수도 도와줄게"라고 덧붙여.

현재 화면 경로: {route}
현재 뷰포트: {viewport}

제품 FAQ 참고:
{faq_lines}

가장 가까운 기존 FAQ 답변:
{matched}

사용자 질문:
{message}

응답:"""


def answer_product_question(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Answer a support question with OPEN AI, falling back to FAQ on failure."""
    fallback = _fallback_answer(message)

    if os.getenv("SUPPORT_ASSISTANT_LLM_ENABLED", "true").lower() in {"0", "false", "no"}:
        return fallback

    try:
        from config import AGENT_DEFAULT_MODEL
        from services.core.ai_service import _build_completion_kwargs

        model = os.getenv("SUPPORT_ASSISTANT_MODEL", AGENT_DEFAULT_MODEL or "chatmock/gpt-5.3-codex-spark")
        matched_item, confidence = _match_faq(message)
        prompt = _build_support_prompt(message, context, matched_item)
        kwargs = _build_completion_kwargs(
            model,
            prompt,
            style_id="summary",
            modifiers={"length": "short"},
            detail_level="brief",
        )
        kwargs["max_tokens"] = min(int(kwargs.get("max_tokens", 700)), 700)

        response = _completion(**kwargs)
        answer = (response.choices[0].message.content or "").strip()
        if not answer:
            return fallback

        return {
            "answer": answer[:1800],
            "matched_topic": matched_item["title"] if matched_item else "llm",
            "confidence": max(confidence, 0.7),
            "llm_used": True,
            "fallback_used": False,
            "model": model,
        }
    except Exception as exc:
        fallback["llm_error"] = str(exc)[:300]
        return fallback
