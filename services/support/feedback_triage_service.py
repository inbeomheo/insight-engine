"""Rule-based triage for product support feedback."""
from __future__ import annotations

import re
from typing import Any

_KIND_KEYWORDS = {
    "bug": ["안돼", "안 돼", "안됨", "안되", "안 되", "생성 안", "작동 안", "오류", "에러", "버그", "깨져", "멈춰", "실패", "안보여", "안 보여"],
    "usability": ["불편", "헷갈", "찌그러", "이상해", "어색", "작아", "잘려", "취소", "눌러도", "보기 싫", "폰트", "글씨"],
    "feature": ["넣어", "추가", "만들", "지원", "가능", "되게", "원해", "하고싶", "구조", "기능"],
    "question": ["뭐야", "무엇", "어떻게", "왜", "차이", "설명", "알려", "궁금", "사용법", "어디"],
}

_PRIORITY_BY_SEVERITY = {
    "critical": "critical",
    "high": "high",
    "medium": "medium",
    "low": "low",
}

_FILE_HINTS = [
    (re.compile(r"요약|전체|타임라인|뷰\s*모드|글씨|폰트"), ["frontend/components/result/ViewModeSelector.tsx"]),
    (re.compile(r"모바일|아래\s*탭|bottom|앱"), ["frontend/components/mobile/MobileAppShell.tsx", "frontend/app/page.tsx"]),
    (re.compile(r"스타일|출력\s*스타일|취소|선택"), ["frontend/app/page.tsx", "frontend/components/mobile/MobileAppShell.tsx", "frontend/lib/constants.ts"]),
    (re.compile(r"공유|링크|복사"), ["frontend/components/result/ResultCard.tsx", "routes/utility/share_pages.py", "services/content/share_page_service.py"]),
    (re.compile(r"모델|openrouter|gpt|키미|kimi|provider|프로바이더"), ["config.py", "frontend/hooks/useProviders.ts", "routes/utility/operations.py"]),
    (re.compile(r"캘린더|예약|발행"), ["frontend/app/page.tsx", "services/data/schedule_service.py", "routes/advanced_routes.py"]),
    (re.compile(r"챗봇|피드백|문의|불편사항"), ["services/support/", "frontend/components/support/"]),
]


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def classify_message(message: str) -> dict[str, Any]:
    text = (message or "").strip().lower()
    scores = {kind: 0 for kind in _KIND_KEYWORDS}
    for kind, words in _KIND_KEYWORDS.items():
        scores[kind] = sum(1 for word in words if word in text)

    # Bug/usability signals should beat a generic "가능해?" feature wording.
    if scores["bug"] or scores["usability"]:
        kind = "bug" if scores["bug"] >= scores["usability"] + 1 else "usability"
    else:
        kind = max(scores.items(), key=lambda item: item[1])[0] if max(scores.values()) > 0 else "question"

    severity = "medium"
    if _contains_any(text, ["배포", "접속", "로그인", "생성 안", "먹통", "critical", "긴급"]):
        severity = "high"
    if _contains_any(text, ["보안", "secret", "password", "토큰", "결제", "데이터 삭제"]):
        severity = "critical"
    if kind == "question":
        severity = "low"
    priority = _PRIORITY_BY_SEVERITY.get(severity, "medium")

    related_files: list[str] = []
    for pattern, files in _FILE_HINTS:
        if pattern.search(text):
            related_files.extend(files)
    # Deduplicate while preserving order.
    related_files = list(dict.fromkeys(related_files))

    labels = ["support-feedback", kind]
    if kind in {"bug", "usability", "feature"}:
        labels.append("needs-agent")
    labels.append(f"priority:{priority}")
    labels = list(dict.fromkeys(labels))

    title = build_title(message, kind)
    suggested_fix = build_suggested_fix(kind, related_files)

    return {
        "kind": kind,
        "severity": severity,
        "priority": priority,
        "title": title,
        "labels": labels,
        "related_files": related_files,
        "suggested_fix": suggested_fix,
        "confidence": min(0.95, 0.45 + 0.12 * max(scores.values()) + (0.15 if related_files else 0)),
    }


def build_title(message: str, kind: str) -> str:
    normalized = re.sub(r"\s+", " ", (message or "").strip())
    prefix = {
        "bug": "[Bug]",
        "usability": "[UX]",
        "feature": "[Feature]",
        "question": "[Question]",
        "ops": "[Ops]",
    }.get(kind, "[Feedback]")
    if not normalized:
        return f"{prefix} 사용자 피드백"
    return f"{prefix} {normalized[:90]}"


def build_suggested_fix(kind: str, related_files: list[str]) -> str:
    if kind == "question":
        return "제품 지식 답변으로 처리하고, 반복 질문이면 FAQ/온보딩 문구 개선을 검토합니다."
    if related_files:
        return "관련 파일 후보를 먼저 확인하고, 재현 테스트 또는 UI smoke test를 추가한 뒤 최소 수정으로 해결합니다."
    return "재현 정보와 화면/환경 정보를 보강한 뒤 관련 컴포넌트 또는 API 경계를 추적합니다."
