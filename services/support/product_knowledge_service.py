"""Product knowledge answers for the in-app support assistant."""
from __future__ import annotations

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
        "keywords": ["모델", "chatmock", "gpt", "프로바이더", "provider"],
        "title": "모델/프로바이더",
        "answer": "현재 생성 모델은 ChatMock(OpenAI 호환 로컬 프록시) 기준으로 단순화했어. 터미널에서 `chatmock login` 후 `chatmock serve`를 실행하고, `.env`의 `CHATMOCK_BASE_URL`이 `http://127.0.0.1:8000/v1`인지 확인하면 돼.",
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

    return {
        "answer": (
            "인사이트 엔진 기능에 대한 질문이면 내가 바로 설명해줄게. "
            "버그나 불편사항이면 접수해서 GitHub 이슈로 넘길 수 있어."
        ),
        "matched_topic": "general",
        "confidence": 0.35,
    }
