"""
SERP Feature Opportunity Analyzer 서비스

콘텐츠가 Google SERP의 특수 기능(Featured Snippet, PAA, Video Carousel,
List/Table Snippet, How-to, FAQ Rich Result)에 노출될 가능성을
규칙 기반으로 분석하고 최적 레이아웃을 추천한다. AI API 호출 없음.
"""
import re
import logging

logger = logging.getLogger(__name__)

# === 패턴 정의 ===

# 정의형 문장 ("~은/는 ~이다", "~란 ~를 말한다" 등)
_DEFINITION_PATTERNS = [
    re.compile(r'.{2,}(?:은|는|이란|란)\s+.{2,}(?:이다|입니다|[을를] 말한다|[을를] 의미한다|[을를] 뜻한다)'),
    re.compile(r'.{2,}(?:이란|란)\s+.{2,}(?:것이다|것입니다|개념이다|개념입니다)'),
]

# 질문형 헤딩 패턴 ("~인가요?", "~할까요?", "~인가?", "~일까?" 등)
_QUESTION_HEADING_PATTERN = re.compile(
    r'^#{1,6}\s+.+(?:\?|인가요\??|할까요\??|인가\??|일까\??|인지\??|는지\??|나요\??|까요\??|ㄹ까\??)$',
    re.MULTILINE,
)

# 순서 있는 목록 (1., 2., 3.)
_ORDERED_LIST_PATTERN = re.compile(r'^\s*\d+\.\s+.+', re.MULTILINE)

# 순서 없는 목록 (-, *)
_UNORDERED_LIST_PATTERN = re.compile(r'^\s*[-*]\s+.+', re.MULTILINE)

# 목록 관련 키워드
_LIST_KEYWORDS = ['TOP', 'top', 'Top', '최고', '추천', '베스트', '순위']

# 마크다운 테이블 패턴 (| col1 | col2 |)
_TABLE_ROW_PATTERN = re.compile(r'^\s*\|.+\|', re.MULTILINE)

# 비교 키워드
_COMPARISON_KEYWORDS = ['비교', '차이', 'vs', 'VS', '대', '장단점', '장점', '단점']

# 가격/스펙 키워드
_SPEC_KEYWORDS = ['가격', '스펙', '사양', '비교표', '요금', '플랜', '요금제']

# 비디오 링크 패턴
_VIDEO_LINK_PATTERN = re.compile(r'(?:youtube\.com|youtu\.be)[/\w?&=%-]*')

# 비디오 키워드
_VIDEO_KEYWORDS = ['영상', '동영상', '비디오', 'video', 'Video']

# 비디오 임베드 패턴
_VIDEO_EMBED_PATTERN = re.compile(r'<(?:iframe|video)\b', re.IGNORECASE)

# 단계별 설명 패턴
_STEP_PATTERNS = [
    re.compile(r'(?:\d+\s*단계|Step\s*\d+|STEP\s*\d+)', re.IGNORECASE),
    re.compile(r'(?:첫째|둘째|셋째|넷째|다섯째)'),
]

# How-to 키워드
_HOWTO_KEYWORDS = ['방법', '가이드', '튜토리얼', '하는 법', '따라하기', 'how to', 'How to']

# Q&A 패턴 ("Q:", "A:", "질문:", "답변:")
_QA_PAIR_PATTERN = re.compile(
    r'(?:^|\n)\s*(?:Q|q|질문)\s*[:.]\s*.+[\s\S]*?(?:^|\n)\s*(?:A|a|답변|답)\s*[:.]\s*.+',
    re.MULTILINE,
)
_QA_QUESTION_PATTERN = re.compile(r'(?:^|\n)\s*(?:Q|q|질문)\s*[:.]\s*.+', re.MULTILINE)

# FAQ 섹션 헤딩
_FAQ_HEADING_PATTERN = re.compile(r'^#{1,6}\s+.*(?:FAQ|faq|자주\s*묻는\s*질문|Q\s*&\s*A)', re.MULTILINE)

# 마크다운 헤딩
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+.+', re.MULTILINE)


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """값을 lo~hi 범위로 제한한다."""
    return max(lo, min(hi, value))


def _probability_label(readiness: float) -> str:
    """readiness 점수에 따른 확률 라벨을 반환한다."""
    if readiness >= 70:
        return "high"
    elif readiness >= 40:
        return "medium"
    return "low"


def _analyze_featured_snippet(content: str, sentences: list[str]) -> dict:
    """Featured Snippet 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 정의형 문장 40-60자 → +40
    has_definition = False
    for pattern in _DEFINITION_PATTERNS:
        for match in pattern.finditer(content):
            matched_text = match.group()
            if 40 <= len(matched_text) <= 60:
                has_definition = True
                break
        if has_definition:
            break

    if has_definition:
        readiness += 40
    else:
        optimizations.append("40-60자 길이의 정의형 문장(~은/는 ~이다)을 추가하세요")

    # 첫 2문장 내 핵심 답변 → +30
    first_two = sentences[:2]
    has_early_answer = False
    if first_two:
        combined = ' '.join(first_two)
        for pattern in _DEFINITION_PATTERNS:
            if pattern.search(combined):
                has_early_answer = True
                break
    if has_early_answer:
        readiness += 30
    else:
        optimizations.append("첫 2문장 내에 핵심 답변을 배치하세요")

    # 헤딩 + 바로 아래 짧은 답변 구조 → +30
    has_heading_answer = False
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if _HEADING_PATTERN.match(line) and i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if next_line and 20 <= len(next_line) <= 80:
                has_heading_answer = True
                break
    if has_heading_answer:
        readiness += 30
    else:
        optimizations.append("헤딩 바로 아래에 짧은 답변(20-80자)을 배치하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "featured_snippet",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_paa(content: str) -> dict:
    """People Also Ask (PAA) 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 질문형 헤딩 2개+ → +40
    question_headings = _QUESTION_HEADING_PATTERN.findall(content)
    if len(question_headings) >= 2:
        readiness += 40
    else:
        optimizations.append("질문형 헤딩(~인가요?, ~할까요?)을 2개 이상 추가하세요")

    # 질문 후 2-3문장 답변 구조 → +30
    # 질문형 헤딩 아래에 짧은 답변이 오는지 확인
    lines = content.split('\n')
    qa_structure_count = 0
    for i, line in enumerate(lines):
        if _QUESTION_HEADING_PATTERN.match(line):
            # 다음 2-3줄이 비어있지 않은 답변인지 확인
            answer_lines = 0
            for j in range(i + 1, min(i + 4, len(lines))):
                stripped = lines[j].strip()
                if stripped and not _HEADING_PATTERN.match(stripped):
                    answer_lines += 1
                elif _HEADING_PATTERN.match(stripped):
                    break
            if 2 <= answer_lines <= 3:
                qa_structure_count += 1
    if qa_structure_count >= 1:
        readiness += 30
    else:
        optimizations.append("질문 헤딩 아래에 2-3문장의 간결한 답변을 작성하세요")

    # FAQ 형식 → +30
    has_faq = bool(_FAQ_HEADING_PATTERN.search(content))
    if has_faq:
        readiness += 30
    else:
        optimizations.append("FAQ 섹션을 추가하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "people_also_ask",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_list_snippet(content: str) -> dict:
    """List Snippet 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 순서 있는 목록 3개+ → +40
    ordered_items = _ORDERED_LIST_PATTERN.findall(content)
    if len(ordered_items) >= 3:
        readiness += 40
    else:
        optimizations.append("순서 있는 목록(1., 2., 3.)을 3개 이상 포함하세요")

    # 순서 없는 목록 5개+ → +30
    unordered_items = _UNORDERED_LIST_PATTERN.findall(content)
    if len(unordered_items) >= 5:
        readiness += 30
    else:
        optimizations.append("순서 없는 목록(-, *)을 5개 이상 포함하세요")

    # "TOP", "최고", "추천" + 목록 → +30
    has_list_keywords = any(kw in content for kw in _LIST_KEYWORDS)
    has_any_list = len(ordered_items) > 0 or len(unordered_items) > 0
    if has_list_keywords and has_any_list:
        readiness += 30
    else:
        optimizations.append("'TOP', '추천', '최고' 등의 키워드와 함께 목록을 구성하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "list_snippet",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_table_snippet(content: str) -> dict:
    """Table Snippet 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 마크다운 테이블 (| 패턴) → +50
    table_rows = _TABLE_ROW_PATTERN.findall(content)
    if len(table_rows) >= 2:
        readiness += 50
    else:
        optimizations.append("마크다운 테이블(| 열1 | 열2 |)을 추가하세요")

    # 비교 키워드 + 구조화된 데이터 → +30
    has_comparison = any(kw in content for kw in _COMPARISON_KEYWORDS)
    has_structured = len(table_rows) >= 2 or len(_ORDERED_LIST_PATTERN.findall(content)) >= 3
    if has_comparison and has_structured:
        readiness += 30
    else:
        optimizations.append("비교 키워드(비교, 차이, vs)와 구조화된 데이터를 함께 사용하세요")

    # 가격/스펙/비교표 → +20
    has_spec = any(kw in content for kw in _SPEC_KEYWORDS)
    if has_spec:
        readiness += 20
    else:
        optimizations.append("가격, 스펙, 비교표 등의 키워드를 포함하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "table_snippet",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_video_carousel(content: str) -> dict:
    """Video Carousel 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 비디오 링크 (youtube.com, youtu.be) → +40
    if _VIDEO_LINK_PATTERN.search(content):
        readiness += 40
    else:
        optimizations.append("YouTube 동영상 링크를 포함하세요")

    # "영상", "동영상", "비디오" 키워드 → +30
    if any(kw in content for kw in _VIDEO_KEYWORDS):
        readiness += 30
    else:
        optimizations.append("'영상', '동영상', '비디오' 등의 키워드를 추가하세요")

    # 임베드 코드 (<iframe, <video) → +30
    if _VIDEO_EMBED_PATTERN.search(content):
        readiness += 30
    else:
        optimizations.append("동영상 임베드 코드(<iframe>, <video>)를 추가하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "video_carousel",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_how_to(content: str) -> dict:
    """How-to Rich Result 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # 단계별 설명 ("1단계", "Step 1", "첫째") → +40
    step_count = 0
    for pattern in _STEP_PATTERNS:
        step_count += len(pattern.findall(content))
    if step_count >= 2:
        readiness += 40
    else:
        optimizations.append("단계별 설명(1단계, Step 1, 첫째/둘째)을 추가하세요")

    # "방법", "가이드", "튜토리얼" 키워드 → +30
    if any(kw in content for kw in _HOWTO_KEYWORDS):
        readiness += 30
    else:
        optimizations.append("'방법', '가이드', '튜토리얼' 등의 키워드를 추가하세요")

    # 각 단계에 설명 포함 → +30
    # 단계 패턴 다음에 설명 텍스트가 있는지 확인
    lines = content.split('\n')
    steps_with_desc = 0
    for i, line in enumerate(lines):
        is_step = False
        for pattern in _STEP_PATTERNS:
            if pattern.search(line):
                is_step = True
                break
        if is_step:
            # 같은 줄에 설명이 있거나, 다음 줄에 설명이 있는 경우
            step_text = line.strip()
            if len(step_text) > 15:
                steps_with_desc += 1
            elif i + 1 < len(lines) and lines[i + 1].strip():
                steps_with_desc += 1
    if steps_with_desc >= 2:
        readiness += 30
    else:
        optimizations.append("각 단계마다 구체적인 설명을 포함하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "how_to_rich_result",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_faq(content: str) -> dict:
    """FAQ Rich Result 기회를 분석한다."""
    readiness = 0.0
    optimizations = []

    # Q&A 패턴 ("Q:", "A:", "질문:", "답변:") → +40
    qa_pairs = _QA_PAIR_PATTERN.findall(content)
    if len(qa_pairs) >= 1:
        readiness += 40
    else:
        optimizations.append("Q&A 패턴(Q: 질문 / A: 답변)을 추가하세요")

    # 질문-답변 쌍 3개+ → +30
    qa_questions = _QA_QUESTION_PATTERN.findall(content)
    if len(qa_questions) >= 3:
        readiness += 30
    else:
        optimizations.append("질문-답변 쌍을 3개 이상 포함하세요")

    # FAQ 섹션 헤딩 → +30
    if _FAQ_HEADING_PATTERN.search(content):
        readiness += 30
    else:
        optimizations.append("FAQ 섹션 헤딩(## FAQ, ## 자주 묻는 질문)을 추가하세요")

    readiness = _clamp(readiness)
    return {
        "feature": "faq_rich_result",
        "probability": _probability_label(readiness),
        "current_readiness": readiness,
        "optimizations": optimizations,
    }


def _analyze_content_format(content: str) -> dict:
    """콘텐츠 형식 분석 불리언 결과를 반환한다."""
    has_definition = False
    for pattern in _DEFINITION_PATTERNS:
        if pattern.search(content):
            has_definition = True
            break

    has_lists = bool(
        _ORDERED_LIST_PATTERN.search(content)
        or _UNORDERED_LIST_PATTERN.search(content)
    )
    has_tables = len(_TABLE_ROW_PATTERN.findall(content)) >= 2
    has_steps = any(
        pattern.search(content) for pattern in _STEP_PATTERNS
    )
    has_faq = bool(
        _FAQ_HEADING_PATTERN.search(content)
        or _QA_PAIR_PATTERN.search(content)
    )
    has_how_to = any(kw in content for kw in _HOWTO_KEYWORDS)

    return {
        "has_definition": has_definition,
        "has_lists": has_lists,
        "has_tables": has_tables,
        "has_steps": has_steps,
        "has_faq": has_faq,
        "has_how_to": has_how_to,
    }


def _generate_suggestions(opportunities: list[dict], format_analysis: dict) -> list[str]:
    """분석 결과를 기반으로 종합 제안을 생성한다."""
    suggestions = []

    # 모든 기회에서 가장 높은 readiness 찾기
    best = max(opportunities, key=lambda o: o["current_readiness"])
    if best["current_readiness"] < 40:
        suggestions.append("전반적인 SERP 노출 가능성이 낮습니다. 콘텐츠 구조를 개선하세요.")

    # 형식별 제안
    if not format_analysis["has_definition"]:
        suggestions.append("정의형 문장을 추가하면 Featured Snippet 노출 가능성이 높아집니다.")
    if not format_analysis["has_lists"]:
        suggestions.append("목록을 추가하면 List Snippet 노출 가능성이 높아집니다.")
    if not format_analysis["has_tables"]:
        suggestions.append("비교 테이블을 추가하면 Table Snippet 노출 가능성이 높아집니다.")
    if not format_analysis["has_steps"]:
        suggestions.append("단계별 가이드를 추가하면 How-to Rich Result 노출 가능성이 높아집니다.")
    if not format_analysis["has_faq"]:
        suggestions.append("FAQ 섹션을 추가하면 FAQ Rich Result 노출 가능성이 높아집니다.")

    # 이미 잘 되어 있는 경우
    high_opps = [o for o in opportunities if o["probability"] == "high"]
    if high_opps:
        features = ', '.join(o["feature"] for o in high_opps)
        suggestions.append(f"현재 {features}에 대한 준비도가 높습니다.")

    return suggestions


_EMPTY_FORMAT = {
    "has_definition": False,
    "has_lists": False,
    "has_tables": False,
    "has_steps": False,
    "has_faq": False,
    "has_how_to": False,
}

_EMPTY_RESULT = {
    "opportunities": [],
    "overall_serp_score": 0.0,
    "best_opportunity": "",
    "content_format_analysis": _EMPTY_FORMAT,
    "suggestions": ["콘텐츠가 비어 있습니다. 분석할 내용을 입력하세요."],
}


def _compute_serp_summary(opportunities: list[dict]) -> tuple:
    """SERP 기회 목록에서 전체 점수와 최적 기회를 계산합니다.

    Returns:
        (overall_score, best_opportunity)
    """
    readiness_values = [o["current_readiness"] for o in opportunities]
    overall_score = sum(readiness_values) / len(readiness_values) if readiness_values else 0.0
    overall_score = round(_clamp(overall_score), 1)

    best_opp = max(opportunities, key=lambda o: o["current_readiness"])
    return overall_score, best_opp["feature"]


def analyze_serp_features(content: str, target_keyword: str = '') -> dict:
    """콘텐츠의 SERP Feature 노출 가능성을 분석한다."""
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    content = content.strip()
    sentences = [s.strip() for s in re.split(r'[.!?]\s+', content) if s.strip()]

    opportunities = [
        _analyze_featured_snippet(content, sentences),
        _analyze_paa(content),
        _analyze_list_snippet(content),
        _analyze_table_snippet(content),
        _analyze_video_carousel(content),
        _analyze_how_to(content),
        _analyze_faq(content),
    ]

    overall_score, best_opportunity = _compute_serp_summary(opportunities)
    format_analysis = _analyze_content_format(content)
    suggestions = _generate_suggestions(opportunities, format_analysis)

    logger.debug(
        "SERP 분석 완료: overall_score=%.1f, best=%s, keyword='%s'",
        overall_score, best_opportunity, target_keyword,
    )

    return {
        "opportunities": opportunities,
        "overall_serp_score": overall_score,
        "best_opportunity": best_opportunity,
        "content_format_analysis": format_analysis,
        "suggestions": suggestions,
    }
