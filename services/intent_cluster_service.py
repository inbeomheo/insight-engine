"""Intent Cluster Miner — 댓글 의도별 군집화 서비스 (규칙 기반).

댓글 목록을 분석하여 AI API 호출 없이
키워드 매칭 기반으로 의도(intent)별 군집을 5개 이상 생성한다.
"""

import re
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# 인텐트 클러스터 데이터 클래스
# ---------------------------------------------------------------------------


@dataclass
class IntentCluster:
    """의도별 댓글 군집."""

    intent: str  # 의도 라벨 (예: "질문", "칭찬", "불만")
    keywords: list[str] = field(default_factory=list)  # 대표 키워드
    examples: list[str] = field(default_factory=list)  # 해당 의도의 댓글 예시
    size: int = 0  # 군집 크기 (댓글 수)
    proportion: float = 0.0  # 전체 대비 비율 (0~1)


# ---------------------------------------------------------------------------
# 의도 분류 사전 — 의도 라벨 → (키워드 목록, 정규식 패턴 목록)
# ---------------------------------------------------------------------------

_INTENT_DEFINITIONS: dict[str, dict] = {
    "질문": {
        "keywords": [
            "어떻게", "왜", "뭐", "무엇", "언제", "어디", "알려", "궁금",
            "질문", "방법", "가능", "되나요", "할까요", "인가요", "건가요",
            "how", "why", "what", "when", "where", "?",
        ],
        "patterns": [
            r"\?$", r"\?{2,}", r"인가요", r"할까요", r"되나요", r"건가요",
            r"은가요", r"나요\??$", r"ㅂ니까", r"습니까",
        ],
    },
    "칭찬/감사": {
        "keywords": [
            "감사", "고마워", "좋아요", "좋은", "최고", "대박", "잘했",
            "멋져", "짱", "훌륭", "유익", "도움", "추천", "사랑",
            "thank", "thanks", "good", "great", "best", "love", "awesome",
        ],
        "patterns": [
            r"감사합니다", r"고맙습니다", r"좋아요{1,}", r"최고{1,}",
            r"[👍❤️🎉💯🔥✨♥]", r"ㅋ{3,}",
        ],
    },
    "불만/비판": {
        "keywords": [
            "별로", "실망", "아쉬", "문제", "불편", "짜증", "화나",
            "거짓", "사기", "안됨", "왜이래", "최악", "싫어",
            "bad", "worst", "terrible", "hate", "disappointed",
        ],
        "patterns": [
            r"ㅡㅡ", r"-_-", r"ㅠ{2,}", r"ㅜ{2,}", r"실망", r"별로",
            r"[😡😤😠💢]",
        ],
    },
    "요청/제안": {
        "keywords": [
            "해주세요", "부탁", "요청", "원해요", "바랍니다", "제안",
            "추가", "개선", "만들어", "필요", "다뤄", "다루어",
            "please", "request", "suggest", "need", "want",
        ],
        "patterns": [
            r"해주세요", r"해줘요", r"부탁", r"요청", r"바랍니다",
            r"으면\s*좋겠", r"면\s*좋겠", r"해주실",
        ],
    },
    "정보 공유": {
        "keywords": [
            "참고로", "사실", "실제로", "경험", "제가", "저는",
            "알려드리", "공유", "팁", "노하우", "정보",
            "fyi", "actually", "tip", "info",
        ],
        "patterns": [
            r"참고로", r"제\s*경험", r"저는\s", r"저도\s", r"사실\s",
            r"알려드", r"공유",
        ],
    },
    "공감/동의": {
        "keywords": [
            "맞아", "동의", "공감", "그렇죠", "인정", "ㅇㅇ", "ㄹㅇ",
            "진짜", "정말", "exactly", "agree", "true", "right",
        ],
        "patterns": [
            r"맞아요", r"동의합니다", r"공감", r"인정{1,}", r"그렇죠",
            r"ㅇㅇ{1,}", r"ㄹㅇ{1,}",
        ],
    },
    "반론/의문": {
        "keywords": [
            "그런데", "하지만", "그래도", "반대", "아닌데", "틀린",
            "과연", "정말로", "의문", "논란",
            "but", "however", "disagree", "wrong",
        ],
        "patterns": [
            r"그런데\s", r"하지만\s", r"근데\s", r"반대", r"아닌데",
            r"틀린\s", r"과연\s",
        ],
    },
    "유머/밈": {
        "keywords": [
            "ㅋㅋ", "ㅎㅎ", "웃겨", "빵", "개웃", "꿀잼", "레전드",
            "ㄱㅇㄷ", "미쳤", "lol", "lmao", "rofl", "haha",
        ],
        "patterns": [
            r"ㅋ{2,}", r"ㅎ{2,}", r"ㅋㅋㅋ", r"ㅎㅎㅎ",
            r"[🤣😂😆]", r"lol", r"lmao",
        ],
    },
    "구독/팔로우": {
        "keywords": [
            "구독", "알림", "좋아요", "팔로우", "채널", "영상",
            "subscribe", "follow", "bell", "notification",
        ],
        "patterns": [
            r"구독", r"알림\s*설정", r"좋아요\s*눌", r"팔로우",
            r"[🔔🔕]",
        ],
    },
    "기타": {
        "keywords": [],
        "patterns": [],
    },
}

# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------


def _classify_comment(comment: str) -> tuple[str, list[str]]:
    """단일 댓글의 의도를 분류하고 매칭된 키워드를 반환한다.

    Returns:
        (intent_label, matched_keywords)
    """
    lower = comment.lower().strip()
    if not lower:
        return "기타", []

    best_intent = "기타"
    best_score = 0
    best_keywords: list[str] = []

    for intent_label, definition in _INTENT_DEFINITIONS.items():
        if intent_label == "기타":
            continue

        score = 0
        matched: list[str] = []

        # 키워드 매칭
        for kw in definition["keywords"]:
            if kw.lower() in lower:
                score += 1
                matched.append(kw)

        # 정규식 패턴 매칭 (가중치 2)
        for pat in definition["patterns"]:
            if re.search(pat, comment, re.IGNORECASE):
                score += 2
                # 패턴 자체를 키워드로 기록하지 않음 (이미 키워드에서 커버)

        if score > best_score:
            best_score = score
            best_intent = intent_label
            best_keywords = matched

    return best_intent, best_keywords


def _deduplicate_keywords(keywords: list[str], max_count: int = 10) -> list[str]:
    """키워드 중복 제거 및 상위 N개 반환."""
    seen: set[str] = set()
    result: list[str] = []
    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower not in seen:
            seen.add(kw_lower)
            result.append(kw)
        if len(result) >= max_count:
            break
    return result


# ---------------------------------------------------------------------------
# 공개 API
# ---------------------------------------------------------------------------


def mine_intent_clusters(comments: list[str]) -> list[IntentCluster]:
    """댓글에서 의도별 군집화를 수행한다 (5개 이상 그룹, 규칙 기반 키워드 매칭).

    Args:
        comments: 분석할 댓글 목록

    Returns:
        5개 이상의 IntentCluster 리스트 (size 내림차순 정렬)
    """
    if not comments:
        return _empty_clusters()

    # 유효한 댓글만 필터링
    valid_comments = [c.strip() for c in comments if c and c.strip()]
    if not valid_comments:
        return _empty_clusters()

    total = len(valid_comments)

    # 각 댓글을 분류
    clusters_data: dict[str, dict] = {}
    for intent_label in _INTENT_DEFINITIONS:
        clusters_data[intent_label] = {
            "keywords": [],
            "examples": [],
            "size": 0,
        }

    for comment in valid_comments:
        intent, matched_kws = _classify_comment(comment)
        clusters_data[intent]["keywords"].extend(matched_kws)
        clusters_data[intent]["size"] += 1
        # 예시는 최대 5개까지 수집
        if len(clusters_data[intent]["examples"]) < 5:
            # 댓글이 너무 길면 100자로 잘라서 저장
            truncated = comment[:100] + "..." if len(comment) > 100 else comment
            clusters_data[intent]["examples"].append(truncated)

    # IntentCluster 객체 생성
    clusters: list[IntentCluster] = []
    for intent_label, data in clusters_data.items():
        if data["size"] == 0 and intent_label != "기타":
            continue

        clusters.append(IntentCluster(
            intent=intent_label,
            keywords=_deduplicate_keywords(data["keywords"]),
            examples=data["examples"],
            size=data["size"],
            proportion=round(data["size"] / total, 4) if total > 0 else 0.0,
        ))

    # 5개 미만이면 비어있는 의도도 포함하여 보충
    clusters = _ensure_minimum_clusters(clusters, min_count=5)

    # size 내림차순 정렬
    clusters.sort(key=lambda c: c.size, reverse=True)

    return clusters


def _ensure_minimum_clusters(
    clusters: list[IntentCluster],
    min_count: int = 5,
) -> list[IntentCluster]:
    """군집이 min_count 미만이면 비어있는 의도 클러스터를 추가한다."""
    if len(clusters) >= min_count:
        return clusters

    existing_intents = {c.intent for c in clusters}

    for intent_label in _INTENT_DEFINITIONS:
        if len(clusters) >= min_count:
            break
        if intent_label in existing_intents:
            continue
        clusters.append(IntentCluster(
            intent=intent_label,
            keywords=[],
            examples=[],
            size=0,
            proportion=0.0,
        ))

    return clusters


def _empty_clusters() -> list[IntentCluster]:
    """빈 댓글 목록에 대한 기본 클러스터 5개를 반환한다."""
    default_intents = ["질문", "칭찬/감사", "불만/비판", "요청/제안", "정보 공유"]
    return [
        IntentCluster(
            intent=intent,
            keywords=[],
            examples=[],
            size=0,
            proportion=0.0,
        )
        for intent in default_intents
    ]
