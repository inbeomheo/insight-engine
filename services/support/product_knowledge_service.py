"""Product knowledge answers for the in-app support assistant."""
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
        "answer": "캘린더는 발행 기능 플래그가 켜져 있을 때만 보여. 현재 환경에서 `NEXT_PUBLIC_PUBLISHING_ENABLED=true`가 아니면 UI에서 숨겨지고, 백엔드 발행 API도 비활성 상태로 두는 게 안전해.",
    },
    {
        "keywords": ["모델", "openrouter", "gpt", "키미", "kimi", "프로바이더"],
        "title": "모델/프로바이더",
        "answer": "모델 목록은 백엔드 `/api/providers` 응답과 환경변수/API 키 상태에 따라 달라져. GPT 계열은 ChatMock 또는 OpenAI/OpenRouter 설정이 연결돼야 보이고, Kimi는 OpenRouter 모델로 노출되는 구조가 일반적이야.",
    },
    {
        "keywords": ["스타일", "출력", "blog", "seo", "shorts", "geo"],
        "title": "출력 스타일",
        "answer": "출력 스타일은 Blog+SEO, 요약, 튜토리얼, Q&A, 앱 아이디어, 요즘IT, 브런치, 네이버, SNS, 뉴스레터, 쇼노트, Shorts, GEO, AI 코스 같은 목적별 프롬프트 프리셋이야.",
    },
    {
        "keywords": ["공유", "링크", "복사", "url"],
        "title": "공유 링크",
        "answer": "공유는 결과 카드의 실제 share URL을 생성해서 복사하는 흐름이야. 복사가 안 되면 브라우저 권한, HTTPS/Basic Auth, 또는 서버의 share page 생성 API 상태를 같이 확인해야 해.",
    },
]


def answer_product_question(message: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    text = (message or "").lower()
    matched = []
    for item in FAQ_ITEMS:
        score = sum(1 for keyword in item["keywords"] if keyword in text)
        if score:
            matched.append((score, item))

    if matched:
        matched.sort(key=lambda pair: pair[0], reverse=True)
        item = matched[0][1]
        return {
            "answer": item["answer"],
            "matched_topic": item["title"],
            "confidence": min(0.95, 0.55 + 0.15 * matched[0][0]),
        }

    publishing = os.getenv("NEXT_PUBLIC_PUBLISHING_ENABLED", "false").lower() == "true"
    return {
        "answer": (
            "인사이트 엔진 기능에 대한 질문이면 내가 바로 설명해줄게. "
            "버그나 불편사항이면 접수해서 GitHub 이슈로 넘길 수 있어. "
            f"참고로 현재 예약 발행 UI는 {'켜져 있어' if publishing else '비활성화되어 있어'}."
        ),
        "matched_topic": "general",
        "confidence": 0.35,
    }
