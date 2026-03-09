"""
노트 확장기 + CTA 생성기 서비스

짧은 노트의 장문 확장 가치를 판단하고,
튜토리얼 콘텐츠에서 구매 의도 지점을 포착하여 CTA 삽입 지점을 추천합니다.
"""
import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# 확장 가치 판단 기준
_MIN_NOTE_LENGTH = 5           # 최소 노트 길이 (자)
_SHORT_NOTE_THRESHOLD = 300    # 이 길이 이하면 확장 후보
_HIGH_ENGAGEMENT_VIEWS = 1000  # 높은 조회수 기준
_HIGH_ENGAGEMENT_LIKES = 50    # 높은 좋아요 기준

# 확장 가치가 높은 주제 키워드
_EXPANDABLE_TOPICS = [
    r'방법', r'가이드', r'팁', r'비교', r'추천', r'리뷰',
    r'원인', r'해결', r'분석', r'전략', r'사례', r'트렌드',
    r'how\s*to', r'guide', r'tips?', r'review', r'tutorial',
]

# 확장 가치가 낮은 패턴
_NON_EXPANDABLE_PATTERNS = [
    r'^(ㅋ|ㅎ|ㅠ|ㅜ)+$',         # 감탄사만
    r'^https?://',                # URL만
    r'^\d+$',                     # 숫자만
]

# CTA 유형 정의
_CTA_TYPES = {
    'tool': {
        'keywords': [r'도구', r'툴', r'소프트웨어', r'앱', r'프로그램', r'서비스',
                      r'tool', r'app', r'software', r'platform'],
        'cta_template': '지금 {keyword}을(를) 시작해 보세요',
    },
    'course': {
        'keywords': [r'강의', r'강좌', r'코스', r'수업', r'배우', r'학습',
                      r'course', r'class', r'learn', r'tutorial'],
        'cta_template': '{keyword} 과정을 확인해 보세요',
    },
    'product': {
        'keywords': [r'제품', r'상품', r'구매', r'구입', r'가격', r'할인',
                      r'product', r'buy', r'price', r'discount'],
        'cta_template': '{keyword} 상세 정보 확인하기',
    },
    'resource': {
        'keywords': [r'템플릿', r'자료', r'다운로드', r'무료', r'체크리스트', r'가이드',
                      r'template', r'resource', r'download', r'free', r'checklist'],
        'cta_template': '{keyword}을(를) 다운로드하세요',
    },
}

# 구매 의도 신호 키워드
_PURCHASE_INTENT_SIGNALS = [
    r'추천합니다', r'사용해\s*보', r'써\s*보', r'시작하',
    r'등록', r'가입', r'신청', r'설치',
    r'필수', r'꼭\s*필요', r'없으면\s*안',
    r'효과적', r'생산성', r'시간\s*절약', r'비용\s*절감',
]


@dataclass
class ExpansionCandidate:
    """노트 확장 후보 판단 결과"""
    original_note: str
    should_expand: bool
    reason: str
    expanded_outline: list[str] = field(default_factory=list)  # 확장 시 아웃라인
    estimated_length: int = 0   # 예상 확장 길이 (자)


def expand_note(
    short_note: str,
    performance: dict | None = None,
) -> ExpansionCandidate:
    """짧은 노트의 장문 확장 가치를 판단합니다.

    Args:
        short_note: 확장 대상 짧은 노트
        performance: 성과 데이터 (선택). 예: {"views": 5000, "likes": 200, "comments": 30}

    Returns:
        ExpansionCandidate 데이터클래스

    Raises:
        ValueError: 노트가 비어있을 때
    """
    if not short_note or not short_note.strip():
        raise ValueError("노트 내용이 비어 있습니다.")

    note = short_note.strip()

    # 확장 불가 패턴 체크
    for pattern in _NON_EXPANDABLE_PATTERNS:
        if re.match(pattern, note):
            return ExpansionCandidate(
                original_note=note,
                should_expand=False,
                reason="확장할 수 없는 형식입니다 (감탄사, URL, 숫자 등).",
            )

    # 최소 길이 미달
    if len(note) < _MIN_NOTE_LENGTH:
        return ExpansionCandidate(
            original_note=note,
            should_expand=False,
            reason=f"노트가 너무 짧습니다 (최소 {_MIN_NOTE_LENGTH}자 이상).",
        )

    # 확장 점수 계산
    score = _calculate_expansion_score(note, performance)

    should_expand = score >= 3
    reason = _build_reason(score, note, performance)

    if should_expand:
        outline = _generate_outline(note)
        estimated_length = _estimate_expanded_length(note, outline)
    else:
        outline = []
        estimated_length = 0

    return ExpansionCandidate(
        original_note=note,
        should_expand=should_expand,
        reason=reason,
        expanded_outline=outline,
        estimated_length=estimated_length,
    )


def generate_upsell_ctas(tutorial_content: str) -> list[dict]:
    """튜토리얼 콘텐츠에서 구매 의도 지점을 포착하여 CTA 삽입 지점을 추천합니다.

    Args:
        tutorial_content: 튜토리얼 콘텐츠 전문

    Returns:
        [{"position": 문단번호, "cta_text": "...", "cta_type": "...", "confidence": 0.0~1.0}]
        CTA 포인트 2개+ 반환

    Raises:
        ValueError: 콘텐츠가 비어있을 때
    """
    if not tutorial_content or not tutorial_content.strip():
        raise ValueError("튜토리얼 콘텐츠가 비어 있습니다.")

    content = tutorial_content.strip()
    paragraphs = _split_paragraphs(content)

    if not paragraphs:
        raise ValueError("분석할 문단이 없습니다.")

    cta_points = []

    for idx, paragraph in enumerate(paragraphs):
        # 각 문단의 CTA 적합도 분석
        cta_info = _analyze_paragraph_for_cta(paragraph, idx, len(paragraphs))
        if cta_info:
            cta_points.append(cta_info)

    # 점수 내림차순 정렬
    cta_points.sort(key=lambda x: x['confidence'], reverse=True)

    # 최소 2개 보장
    if len(cta_points) < 2:
        cta_points = _ensure_minimum_ctas(paragraphs, cta_points)

    return cta_points


def _calculate_expansion_score(note: str, performance: dict | None) -> int:
    """확장 가치 점수를 계산합니다 (0~10)."""
    score = 0

    # 1. 길이 기준 (짧을수록 확장 가치 높음)
    if len(note) <= _SHORT_NOTE_THRESHOLD:
        score += 2
    elif len(note) <= _SHORT_NOTE_THRESHOLD * 2:
        score += 1

    # 2. 확장 가능 주제 포함
    for pattern in _EXPANDABLE_TOPICS:
        if re.search(pattern, note, re.IGNORECASE):
            score += 2
            break

    # 3. 질문형 노트 (사용자 관심 높음)
    if re.search(r'[?？]', note) or re.search(r'(어떻게|무엇|왜|언제|어디)', note):
        score += 1

    # 4. 리스트/번호 포함 (구조화 가능)
    if re.search(r'(\d+[.)]\s|[-•]\s)', note):
        score += 1

    # 5. 성과 기반 판단
    if performance:
        views = performance.get('views', 0)
        likes = performance.get('likes', 0)
        comments = performance.get('comments', 0)

        if views >= _HIGH_ENGAGEMENT_VIEWS:
            score += 2
        elif views >= _HIGH_ENGAGEMENT_VIEWS // 2:
            score += 1

        if likes >= _HIGH_ENGAGEMENT_LIKES:
            score += 1

        # 댓글이 많으면 토론거리 = 확장 가치
        if comments >= 10:
            score += 1

    return min(score, 10)


def _build_reason(score: int, note: str, performance: dict | None) -> str:
    """확장 판단 사유를 생성합니다."""
    reasons = []

    if score >= 5:
        reasons.append("확장 가치가 매우 높습니다.")
    elif score >= 3:
        reasons.append("확장 가치가 있습니다.")
    else:
        reasons.append("현재 상태로 충분합니다.")

    if len(note) <= _SHORT_NOTE_THRESHOLD:
        reasons.append("짧은 노트로 장문 확장 여지가 큽니다.")

    # 확장 가능 주제 확인
    for pattern in _EXPANDABLE_TOPICS:
        if re.search(pattern, note, re.IGNORECASE):
            reasons.append("확장 가능한 주제 키워드가 포함되어 있습니다.")
            break

    if performance:
        views = performance.get('views', 0)
        if views >= _HIGH_ENGAGEMENT_VIEWS:
            reasons.append(f"높은 조회수({views})로 독자 관심이 확인되었습니다.")

    return " ".join(reasons)


def _generate_outline(note: str) -> list[str]:
    """노트 기반 확장 아웃라인을 생성합니다."""
    outline = []

    # 기본 구조
    outline.append("도입: 주제 소개 및 배경")

    # 주제 분석
    if re.search(r'(방법|가이드|how\s*to)', note, re.IGNORECASE):
        outline.append("준비 사항 및 전제 조건")
        outline.append("단계별 실행 방법")
        outline.append("주의사항 및 팁")
    elif re.search(r'(비교|추천|리뷰|review)', note, re.IGNORECASE):
        outline.append("비교 대상 소개")
        outline.append("항목별 상세 비교")
        outline.append("추천 및 선택 가이드")
    elif re.search(r'(원인|해결|문제)', note, re.IGNORECASE):
        outline.append("문제 현황 및 원인 분석")
        outline.append("해결 방안 제시")
        outline.append("예방 및 대응 전략")
    elif re.search(r'(분석|트렌드|전략)', note, re.IGNORECASE):
        outline.append("현황 데이터 분석")
        outline.append("핵심 인사이트")
        outline.append("향후 전망 및 전략 제안")
    else:
        outline.append("본론: 핵심 내용 전개")
        outline.append("사례 및 근거")

    outline.append("결론: 요약 및 다음 단계")

    return outline


def _estimate_expanded_length(note: str, outline: list[str]) -> int:
    """예상 확장 길이를 추산합니다 (자 단위)."""
    # 섹션당 평균 300~500자
    section_avg = 400
    base = len(outline) * section_avg

    # 원본 노트 길이에 비례하여 조정
    if len(note) > 200:
        base += len(note)

    return base


def _split_paragraphs(text: str) -> list[str]:
    """텍스트를 문단 단위로 분리합니다."""
    # 빈 줄 또는 마크다운 헤딩 기준
    raw = re.split(r'\n\s*\n|(?=^#{1,3}\s)', text, flags=re.MULTILINE)
    return [p.strip() for p in raw if len(p.strip()) >= 10]


def _analyze_paragraph_for_cta(
    paragraph: str,
    position: int,
    total_paragraphs: int,
) -> dict | None:
    """문단의 CTA 삽입 적합도를 분석합니다."""
    confidence = 0.0
    detected_type = None
    detected_keyword = None

    # 1. CTA 유형별 키워드 매칭
    for cta_type, config in _CTA_TYPES.items():
        for kw_pattern in config['keywords']:
            match = re.search(kw_pattern, paragraph, re.IGNORECASE)
            if match:
                confidence += 0.3
                detected_type = cta_type
                detected_keyword = match.group(0)
                break
        if detected_type:
            break

    # 2. 구매 의도 신호
    intent_count = 0
    for signal in _PURCHASE_INTENT_SIGNALS:
        if re.search(signal, paragraph):
            intent_count += 1
    confidence += min(intent_count * 0.15, 0.4)

    # 3. 위치 보너스 (중간~후반부가 CTA에 적합)
    if total_paragraphs > 1:
        ratio = position / (total_paragraphs - 1)
        if 0.4 <= ratio <= 0.8:
            confidence += 0.1  # 중간부
        elif ratio > 0.8:
            confidence += 0.15  # 후반부

    # 최소 신뢰도 미달 시 None
    if confidence < 0.2:
        return None

    confidence = min(round(confidence, 2), 1.0)

    # CTA 텍스트 생성
    if detected_type and detected_keyword:
        cta_text = _CTA_TYPES[detected_type]['cta_template'].format(
            keyword=detected_keyword
        )
    else:
        cta_text = "더 알아보기"
        detected_type = "general"

    return {
        "position": position,
        "cta_text": cta_text,
        "cta_type": detected_type,
        "confidence": confidence,
    }


def _ensure_minimum_ctas(
    paragraphs: list[str],
    existing: list[dict],
) -> list[dict]:
    """최소 2개의 CTA를 보장합니다."""
    result = list(existing)
    existing_positions = {c['position'] for c in result}

    # 기존에 없는 위치에 기본 CTA 추가
    # 중간 지점
    mid = len(paragraphs) // 2
    if mid not in existing_positions and len(result) < 2:
        result.append({
            "position": mid,
            "cta_text": "관련 내용을 더 확인해 보세요",
            "cta_type": "general",
            "confidence": 0.2,
        })

    # 마지막 문단
    last = len(paragraphs) - 1
    if last not in existing_positions and len(result) < 2:
        result.append({
            "position": last,
            "cta_text": "지금 바로 시작해 보세요",
            "cta_type": "general",
            "confidence": 0.25,
        })

    # 여전히 2개 미만이면 첫 번째 문단에도 추가
    if len(result) < 2:
        if 0 not in existing_positions:
            result.append({
                "position": 0,
                "cta_text": "자세한 내용을 확인하세요",
                "cta_type": "general",
                "confidence": 0.15,
            })

    return result
