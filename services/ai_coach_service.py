"""
AI 코칭 서비스

채널 데이터 + 질문을 기반으로 규칙 기반 분석/추천/액션 플랜 생성.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CoachResponse:
    """코칭 응답."""
    question: str
    analysis: str
    recommendations: List[str]
    action_plan: List[str]
    confidence: float       # 0.0 ~ 1.0


# ── 콘텐츠 유형별 기본 조언 ──
_CONTENT_TYPE_ADVICE: Dict[str, Dict] = {
    'tutorial': {
        'strength': '교육 콘텐츠는 검색 유입과 장기 조회에 유리합니다.',
        'tips': [
            '시리즈물로 구성하여 시청 지속률을 높이세요',
            '챕터(타임스탬프)를 활용해 검색 노출을 개선하세요',
            '실습 예제를 포함하여 시청자 참여를 유도하세요',
        ],
    },
    'vlog': {
        'strength': '브이로그는 구독자와의 친밀감 형성에 효과적입니다.',
        'tips': [
            '일상 속 스토리텔링으로 감정적 연결을 만드세요',
            '정기 업로드로 시청 습관을 형성하세요',
            '커뮤니티 탭을 활용해 시청자와 소통하세요',
        ],
    },
    'review': {
        'strength': '리뷰 콘텐츠는 구매 의사결정에 영향을 미쳐 높은 광고 수익을 기대할 수 있습니다.',
        'tips': [
            '비교 리뷰로 검색 키워드를 넓히세요',
            '솔직한 단점 언급으로 신뢰도를 높이세요',
            '제품 링크와 할인 코드로 수익을 다각화하세요',
        ],
    },
    'entertainment': {
        'strength': '엔터테인먼트 콘텐츠는 공유와 바이럴에 유리합니다.',
        'tips': [
            '첫 3초 훅으로 이탈률을 줄이세요',
            'Shorts를 활용해 신규 구독자를 유입하세요',
            '트렌드를 빠르게 반영하세요',
        ],
    },
}

# 기본(알 수 없는 유형) 조언
_DEFAULT_ADVICE = {
    'strength': '다양한 콘텐츠를 시도하며 채널 정체성을 찾아가세요.',
    'tips': [
        '시청자 반응이 좋은 콘텐츠 유형을 파악하세요',
        '꾸준한 업로드 일정을 유지하세요',
        '유사 채널을 벤치마킹하세요',
    ],
}

# ── 게시 빈도별 조언 ──
_FREQUENCY_ADVICE = {
    'daily': '매일 업로드는 채널 성장에 강력하지만 번아웃에 주의하세요. 배치 촬영/편집을 권장합니다.',
    'weekly': '주 1회는 안정적인 성장 빈도입니다. 요일과 시간을 고정하면 시청 습관이 형성됩니다.',
    'biweekly': '2주 1회는 품질을 유지하기 좋지만, 알고리즘 노출이 줄어들 수 있습니다. Shorts로 빈도를 보완하세요.',
    'monthly': '월 1회는 채널 성장이 느릴 수 있습니다. 가능하면 빈도를 높이거나 긴 형식 콘텐츠에 집중하세요.',
}


def _analyze_engagement_ratio(subscribers: int, avg_views: int) -> Dict:
    """구독자 대비 평균 조회수 비율을 분석합니다."""
    if subscribers <= 0:
        return {
            'ratio': 0.0,
            'rating': 'unknown',
            'message': '구독자 정보가 없어 비율을 계산할 수 없습니다.',
        }

    ratio = avg_views / subscribers
    if ratio >= 0.3:
        rating = 'excellent'
        message = f'조회수/구독자 비율 {ratio:.1%}로 매우 우수합니다. 충성도 높은 시청자 기반입니다.'
    elif ratio >= 0.1:
        rating = 'good'
        message = f'조회수/구독자 비율 {ratio:.1%}로 양호합니다. 꾸준한 시청 참여가 있습니다.'
    elif ratio >= 0.03:
        rating = 'average'
        message = f'조회수/구독자 비율 {ratio:.1%}로 평균 수준입니다. 썸네일과 제목 최적화를 검토하세요.'
    else:
        rating = 'low'
        message = f'조회수/구독자 비율 {ratio:.1%}로 낮습니다. 알림 설정 유도와 콘텐츠 방향 재검토가 필요합니다.'

    return {'ratio': round(ratio, 4), 'rating': rating, 'message': message}


def _analyze_channel_size(subscribers: int) -> Dict:
    """채널 규모에 따른 성장 전략을 제안합니다."""
    if subscribers < 1000:
        return {
            'tier': 'starter',
            'message': '초기 성장 단계입니다.',
            'strategy': '니치 주제에 집중하고 커뮤니티를 구축하세요. 검색 최적화(SEO)에 집중하세요.',
        }
    elif subscribers < 10000:
        return {
            'tier': 'growing',
            'message': '성장 중인 채널입니다.',
            'strategy': '핵심 시청자층을 파악하고 시리즈 콘텐츠를 기획하세요. 협업을 시작하세요.',
        }
    elif subscribers < 100000:
        return {
            'tier': 'established',
            'message': '안정적인 채널입니다.',
            'strategy': '수익 모델을 다각화하고 팀을 구성하세요. 브랜드 파트너십을 적극 활용하세요.',
        }
    else:
        return {
            'tier': 'major',
            'message': '대형 채널입니다.',
            'strategy': '콘텐츠 품질 유지에 집중하고, 멀티 플랫폼 전략을 실행하세요.',
        }


def _calculate_confidence(channel_data: dict) -> float:
    """입력 데이터 완성도에 따른 신뢰도 점수를 계산합니다."""
    score = 0.0
    max_score = 4.0

    if channel_data.get('subscribers', 0) > 0:
        score += 1.0
    if channel_data.get('avg_views', 0) > 0:
        score += 1.0
    if channel_data.get('content_type', ''):
        score += 1.0
    if channel_data.get('frequency', ''):
        score += 1.0

    return round(score / max_score, 2)


def coach_session(channel_data: dict, question: str) -> CoachResponse:
    """채널 데이터와 질문을 기반으로 AI 코칭을 제공합니다.

    Args:
        channel_data: {
            "subscribers": N,      # 구독자 수
            "avg_views": N,        # 평균 조회수
            "content_type": "...", # 콘텐츠 유형 (tutorial/vlog/review/entertainment)
            "frequency": "..."     # 게시 빈도 (daily/weekly/biweekly/monthly)
        }
        question: 사용자 질문

    Returns:
        CoachResponse
    """
    if not channel_data:
        channel_data = {}

    subscribers = channel_data.get('subscribers', 0)
    avg_views = channel_data.get('avg_views', 0)
    content_type = channel_data.get('content_type', '')
    frequency = channel_data.get('frequency', '')

    # 분석 조합
    engagement = _analyze_engagement_ratio(subscribers, avg_views)
    size_analysis = _analyze_channel_size(subscribers)
    content_advice = _CONTENT_TYPE_ADVICE.get(content_type, _DEFAULT_ADVICE)
    freq_advice = _FREQUENCY_ADVICE.get(frequency, '게시 빈도 정보가 없습니다. 최소 주 1회 업로드를 권장합니다.')

    # 분석 텍스트 조합
    analysis_parts = [
        f"[채널 규모] {size_analysis['message']} {size_analysis['strategy']}",
        f"[참여도] {engagement['message']}",
        f"[콘텐츠] {content_advice['strength']}",
        f"[게시 빈도] {freq_advice}",
    ]
    analysis = '\n'.join(analysis_parts)

    # 추천 사항 조합
    recommendations = list(content_advice['tips'])

    # 참여도에 따른 추가 추천
    if engagement['rating'] == 'low':
        recommendations.append('썸네일 A/B 테스트를 실시하세요')
        recommendations.append('제목에 구체적인 숫자나 키워드를 포함하세요')
    elif engagement['rating'] == 'excellent':
        recommendations.append('현재 전략이 잘 작동하고 있습니다. 일관성을 유지하세요')

    # 액션 플랜 생성
    action_plan = _generate_action_plan(size_analysis['tier'], engagement['rating'], content_type)

    confidence = _calculate_confidence(channel_data)

    return CoachResponse(
        question=question or "",
        analysis=analysis,
        recommendations=recommendations,
        action_plan=action_plan,
        confidence=confidence,
    )


def _generate_action_plan(tier: str, engagement_rating: str, content_type: str) -> List[str]:
    """채널 상태에 맞는 액션 플랜을 생성합니다."""
    plan = []

    # 1단계: 공통
    plan.append('1단계: 최근 10개 영상의 성과 데이터를 분석하세요 (조회수, 시청 지속률, CTR)')

    # 2단계: 참여도 기반
    if engagement_rating in ('low', 'average'):
        plan.append('2단계: 상위 3개 영상의 공통 요소를 파악하고 다음 5개 영상에 적용하세요')
    else:
        plan.append('2단계: 현재 성공 공식을 문서화하고 일관되게 적용하세요')

    # 3단계: 규모 기반
    if tier == 'starter':
        plan.append('3단계: 주제 관련 키워드 리서치로 검색 유입을 최적화하세요')
    elif tier == 'growing':
        plan.append('3단계: 유사 채널 3개와 협업 또는 반응 영상을 기획하세요')
    elif tier == 'established':
        plan.append('3단계: 멤버십, 후원, 제휴 등 수익 모델을 1개 이상 추가하세요')
    else:
        plan.append('3단계: 팀 구성을 강화하고 콘텐츠 제작 파이프라인을 체계화하세요')

    # 4단계: 콘텐츠 유형 기반
    if content_type == 'tutorial':
        plan.append('4단계: 시리즈물 3부작을 기획하여 시청 지속률을 높이세요')
    elif content_type == 'entertainment':
        plan.append('4단계: Shorts 3개를 제작하여 신규 시청자 유입을 테스트하세요')
    else:
        plan.append('4단계: 다음 2주간 계획한 콘텐츠를 미리 촬영하세요')

    return plan


def get_channel_health_score(channel_data: dict) -> Dict:
    """채널 건강 점수를 0~100으로 계산합니다.

    Args:
        channel_data: coach_session과 동일한 형식

    Returns:
        {"score": int, "grade": str, "breakdown": dict}
    """
    subscribers = channel_data.get('subscribers', 0)
    avg_views = channel_data.get('avg_views', 0)
    content_type = channel_data.get('content_type', '')
    frequency = channel_data.get('frequency', '')

    breakdown = {}
    total = 0

    # 참여도 점수 (40점 만점)
    if subscribers > 0:
        ratio = avg_views / subscribers
        if ratio >= 0.3:
            engagement_score = 40
        elif ratio >= 0.1:
            engagement_score = 30
        elif ratio >= 0.03:
            engagement_score = 20
        else:
            engagement_score = 10
    else:
        engagement_score = 0
    breakdown['engagement'] = engagement_score
    total += engagement_score

    # 게시 빈도 점수 (30점 만점)
    freq_scores = {'daily': 30, 'weekly': 25, 'biweekly': 15, 'monthly': 10}
    freq_score = freq_scores.get(frequency, 5)
    breakdown['frequency'] = freq_score
    total += freq_score

    # 콘텐츠 전략 점수 (30점 만점) — 유형이 명확할수록 높음
    if content_type in _CONTENT_TYPE_ADVICE:
        strategy_score = 25
    elif content_type:
        strategy_score = 15
    else:
        strategy_score = 5
    breakdown['strategy'] = strategy_score
    total += strategy_score

    # 등급 산정
    if total >= 80:
        grade = 'A'
    elif total >= 60:
        grade = 'B'
    elif total >= 40:
        grade = 'C'
    else:
        grade = 'D'

    return {'score': total, 'grade': grade, 'breakdown': breakdown}
