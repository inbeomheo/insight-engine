"""
바이럴 댓글 선점 + 제목 실험 서비스 (T6.3)

제목 변형 CTR 예측(규칙 기반) 및 브랜드 톤에 맞는 바이럴 댓글 초안 생성.
외부 AI 호출 없이 순수 Python 로직으로 동작.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CTR 예측 규칙 가중치
# ---------------------------------------------------------------------------

# 제목 길이 최적 구간 (글자 수 기준)
_OPTIMAL_LENGTH_MIN = 15
_OPTIMAL_LENGTH_MAX = 40

# CTR에 긍정적으로 작용하는 패턴과 점수
_POSITIVE_PATTERNS: List[tuple] = [
    (r'\d+', 0.08, '숫자 포함'),           # 리스트형 ("5가지 방법")
    (r'[?？]', 0.06, '질문형'),             # 질문형 제목
    (r'[!！]', 0.03, '감탄형'),             # 감탄형 제목
    (r'방법|팁|비결|비밀|노하우', 0.07, '솔루션 키워드'),
    (r'왜|어떻게|무엇|언제', 0.05, '호기심 키워드'),
    (r'무료|공짜|혜택|할인', 0.06, '혜택 키워드'),
    (r'최신|최고|최초|유일', 0.04, '최상급 키워드'),
    (r'\[.*?\]|【.*?】', 0.03, '대괄호 태그'),  # [필독], 【꿀팁】
]

# CTR에 부정적으로 작용하는 패턴과 감점
_NEGATIVE_PATTERNS: List[tuple] = [
    (r'광고|협찬|스폰서', -0.05, '광고 표시'),
    (r'\.{3,}', -0.02, '과도한 줄임표'),
    (r'[!！]{2,}', -0.03, '과도한 느낌표'),
    (r'[A-Z]{5,}', -0.02, '대문자 남용'),
]

# 기본 CTR 베이스라인 (유튜브 평균 약 2-10%)
_BASE_CTR = 0.05

# ---------------------------------------------------------------------------
# 댓글 톤 템플릿
# ---------------------------------------------------------------------------

_TONE_TEMPLATES: Dict[str, List[str]] = {
    'friendly': [
        '와, {topic} 정말 유익하네요! {hook}',
        '{topic}에 대해 이렇게 정리해주시다니 감사합니다. {hook}',
        '오 이건 몰랐어요! {topic} 관련해서 {hook}',
    ],
    'professional': [
        '{topic} 분석이 정확합니다. {hook}',
        '업계에서 {topic}은(는) 핵심 이슈죠. {hook}',
        '{topic} 관점에서 보면, {hook}',
    ],
    'humorous': [
        '{topic} 보고 커피 쏟을 뻔했어요 ㅋㅋ {hook}',
        '와 {topic} 이거 실화입니까 ㅎㅎ {hook}',
        '{topic} 때문에 잠이 안 옵니다 (좋은 의미로) {hook}',
    ],
    'curious': [
        '{topic} 관련해서 궁금한 게 있는데요, {hook}',
        '혹시 {topic} 다음 편도 예정이신가요? {hook}',
        '{topic}의 반대 사례도 궁금합니다. {hook}',
    ],
}

# 기본 톤 (매핑 없는 경우)
_DEFAULT_TONE = 'friendly'

# 이모지 스타일별 매핑
_EMOJI_STYLES: Dict[str, List[str]] = {
    'minimal': [],
    'moderate': ['👍', '🔥', '💡'],
    'heavy': ['🔥', '💯', '🎯', '👏', '💡', '✨', '🚀'],
}

# 참여 유도 후크(engagement hook) 템플릿
_ENGAGEMENT_HOOKS: List[str] = [
    '여러분은 어떻게 생각하세요?',
    '비슷한 경험 있으신 분?',
    '다음 영상도 기대됩니다!',
    '이 부분 진짜 공감합니다.',
    '저도 해봐야겠어요!',
    '이건 저장 필수!',
    '주변에 공유하고 싶은 내용이네요.',
]


# ---------------------------------------------------------------------------
# 데이터 클래스
# ---------------------------------------------------------------------------

@dataclass
class ExperimentResult:
    """제목 실험 결과"""
    video_id: str
    variants: List[Dict]           # [{"title": "...", "predicted_ctr": 0.0~1.0, "scores": {...}}]
    winner: str                    # 승자 제목 텍스트
    winner_reason: str             # 승자 선정 사유
    confidence: float              # 신뢰도 0~1


@dataclass
class CommentDraft:
    """바이럴 댓글 초안"""
    post_url: str
    comment_text: str
    tone: str
    hashtags: List[str]
    engagement_hooks: List[str]


# ---------------------------------------------------------------------------
# CTR 예측 (규칙 기반)
# ---------------------------------------------------------------------------

def _score_title(title: str) -> Dict:
    """
    제목의 CTR 예측 점수 산출 (규칙 기반).

    Returns:
        {"predicted_ctr": float, "scores": {"길이": ..., "숫자 포함": ..., ...}}
    """
    scores: Dict[str, float] = {}
    total = _BASE_CTR

    # 1. 길이 점수
    length = len(title)
    if _OPTIMAL_LENGTH_MIN <= length <= _OPTIMAL_LENGTH_MAX:
        length_score = 0.05
    elif length < _OPTIMAL_LENGTH_MIN:
        # 너무 짧으면 감점 (정보 부족)
        length_score = -0.02
    else:
        # 너무 길면 감점 (가독성 저하)
        length_score = -0.03
    scores['길이'] = round(length_score, 4)
    total += length_score

    # 2. 긍정 패턴 매칭
    for pattern, weight, label in _POSITIVE_PATTERNS:
        if re.search(pattern, title):
            scores[label] = round(weight, 4)
            total += weight

    # 3. 부정 패턴 매칭
    for pattern, weight, label in _NEGATIVE_PATTERNS:
        if re.search(pattern, title):
            scores[label] = round(weight, 4)
            total += weight

    # 4. 범위 제한 (0.01 ~ 0.99)
    predicted_ctr = max(0.01, min(0.99, round(total, 4)))

    return {
        'predicted_ctr': predicted_ctr,
        'scores': scores,
    }


def run_title_experiment(video_id: str, variants: List[str]) -> ExperimentResult:
    """
    제목 변형 실험 — CTR 예측 기반 승자 선정 (규칙 기반).

    Args:
        video_id: YouTube 영상 ID
        variants: 제목 변형 리스트 (최소 2개)

    Returns:
        ExperimentResult (승자 제목, 사유, 신뢰도)

    Raises:
        ValueError: 변형이 2개 미만이면 실험 불가
    """
    if len(variants) < 2:
        raise ValueError('실험에는 최소 2개의 제목 변형이 필요합니다.')

    # 빈 문자열 필터링
    cleaned = [v.strip() for v in variants if v.strip()]
    if len(cleaned) < 2:
        raise ValueError('유효한 제목 변형이 2개 미만입니다.')

    # 각 변형 점수 산출
    scored_variants: List[Dict] = []
    for title in cleaned:
        result = _score_title(title)
        scored_variants.append({
            'title': title,
            'predicted_ctr': result['predicted_ctr'],
            'scores': result['scores'],
        })

    # CTR 내림차순 정렬
    scored_variants.sort(key=lambda v: v['predicted_ctr'], reverse=True)

    winner = scored_variants[0]
    runner_up = scored_variants[1]

    # 신뢰도 산출: 1위와 2위 CTR 차이 기반
    ctr_gap = winner['predicted_ctr'] - runner_up['predicted_ctr']
    # 차이가 0.05 이상이면 신뢰도 1.0, 0이면 0.5 (동점)
    confidence = min(1.0, 0.5 + ctr_gap * 10)
    confidence = round(max(0.0, confidence), 4)

    # 승자 사유 생성
    top_factors = sorted(
        winner['scores'].items(),
        key=lambda x: abs(x[1]),
        reverse=True,
    )[:3]
    factor_strs = [f'{k}(+{v})' if v > 0 else f'{k}({v})' for k, v in top_factors]
    reason = f"CTR {winner['predicted_ctr']:.1%} 예측. 주요 요인: {', '.join(factor_strs)}"

    logger.info(
        "제목 실험 완료: video_id=%s, 승자='%s', CTR=%.1f%%, 신뢰도=%.0f%%",
        video_id, winner['title'], winner['predicted_ctr'] * 100, confidence * 100,
    )

    return ExperimentResult(
        video_id=video_id,
        variants=scored_variants,
        winner=winner['title'],
        winner_reason=reason,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# 바이럴 댓글 초안 생성
# ---------------------------------------------------------------------------

def _select_template(tone: str, index: int = 0) -> str:
    """톤에 맞는 템플릿 선택"""
    templates = _TONE_TEMPLATES.get(tone, _TONE_TEMPLATES[_DEFAULT_TONE])
    return templates[index % len(templates)]


def _build_hashtags(topic: str, brand_keywords: List[str]) -> List[str]:
    """주제와 브랜드 키워드에서 해시태그 생성"""
    tags = []

    # 주제에서 핵심 단어 추출 (2글자 이상 한글/영문)
    words = re.findall(r'[가-힣a-zA-Z]{2,}', topic)
    for w in words[:3]:
        tags.append(f'#{w}')

    # 브랜드 키워드 추가
    for kw in brand_keywords[:3]:
        tag = f'#{kw.strip().replace(" ", "")}'
        if tag not in tags:
            tags.append(tag)

    return tags[:5]  # 최대 5개


def _select_hooks(count: int = 2) -> List[str]:
    """참여 유도 후크 선택 (순환)"""
    return _ENGAGEMENT_HOOKS[:count]


def _apply_emojis(text: str, emoji_style: str) -> str:
    """이모지 스타일에 따라 이모지 삽입"""
    emojis = _EMOJI_STYLES.get(emoji_style, _EMOJI_STYLES['minimal'])
    if not emojis:
        return text
    # 텍스트 끝에 이모지 1~2개 추가
    selected = emojis[:min(2, len(emojis))]
    return f"{text} {''.join(selected)}"


def draft_viral_comment(
    post_url: str,
    brand_voice: Dict,
    topic: str = "",
) -> CommentDraft:
    """
    브랜드 톤에 맞는 바이럴 댓글 초안 생성.

    Args:
        post_url: 댓글을 달 게시물 URL
        brand_voice: 브랜드 보이스 설정
            - tone: str — 톤 ("friendly", "professional", "humorous", "curious")
            - keywords: list[str] — 브랜드 키워드
            - emoji_style: str — 이모지 스타일 ("minimal", "moderate", "heavy")
        topic: 주제 (빈 문자열이면 URL에서 추론 시도)

    Returns:
        CommentDraft (댓글 텍스트, 톤, 해시태그, 참여 유도 후크)

    Raises:
        ValueError: post_url이 빈 문자열이면 에러
    """
    if not post_url or not post_url.strip():
        raise ValueError('post_url은 필수입니다.')

    # 브랜드 보이스 파싱
    tone = brand_voice.get('tone', _DEFAULT_TONE)
    keywords = brand_voice.get('keywords', [])
    emoji_style = brand_voice.get('emoji_style', 'minimal')

    # 톤 유효성 검사 — 미지원 톤이면 기본 톤 사용
    if tone not in _TONE_TEMPLATES:
        logger.warning("미지원 톤 '%s', 기본 톤 '%s' 사용", tone, _DEFAULT_TONE)
        tone = _DEFAULT_TONE

    # 주제가 없으면 URL에서 간단 추출
    effective_topic = topic.strip() if topic else _extract_topic_from_url(post_url)

    # 참여 유도 후크 선택
    hooks = _select_hooks(count=2)

    # 템플릿 기반 댓글 생성
    template = _select_template(tone)
    comment_text = template.format(
        topic=effective_topic,
        hook=hooks[0],
    )

    # 이모지 적용
    comment_text = _apply_emojis(comment_text, emoji_style)

    # 해시태그 생성
    hashtags = _build_hashtags(effective_topic, keywords)

    logger.info(
        "바이럴 댓글 초안 생성: url=%s, tone=%s, topic='%s'",
        post_url, tone, effective_topic,
    )

    return CommentDraft(
        post_url=post_url,
        comment_text=comment_text,
        tone=tone,
        hashtags=hashtags,
        engagement_hooks=hooks,
    )


def _extract_topic_from_url(url: str) -> str:
    """URL에서 주제 키워드를 간단 추출 (최후 수단)"""
    # YouTube video ID 패턴
    yt_match = re.search(r'(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})', url)
    if yt_match:
        return '영상 콘텐츠'

    # 일반 URL에서 경로의 마지막 세그먼트
    path_match = re.search(r'https?://[^/]+/(.+?)/?$', url)
    if path_match:
        segment = path_match.group(1).split('/')[-1]
        # URL 인코딩된 한글이나 영문 그대로 반환
        cleaned = re.sub(r'[-_]', ' ', segment)
        if cleaned.strip():
            return cleaned.strip()

    return '콘텐츠'
