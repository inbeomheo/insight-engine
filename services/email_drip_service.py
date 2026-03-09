"""
이메일 드립 캠페인 서비스

주제를 기반으로 N개의 연속 이메일(드립 시퀀스)을 자동 설계합니다.
외부 API 없이 템플릿 기반으로 구조화된 이메일 시퀀스를 생성합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class DripEmail:
    """드립 캠페인 개별 이메일"""
    day: int         # 발송일 (1일차부터)
    subject: str     # 이메일 제목
    body: str        # 본문 텍스트
    cta: str         # Call-to-Action 문구


@dataclass
class DripCampaign:
    """드립 캠페인 전체"""
    topic: str
    emails: List[DripEmail] = field(default_factory=list)
    total_emails: int = 0
    estimated_days: int = 0


# 이메일 시퀀스 단계별 역할
_SEQUENCE_ROLES = [
    {
        'role': '환영/소개',
        'subject_template': '{topic} 시작하기 — 환영합니다!',
        'body_template': (
            '안녕하세요!\n\n'
            '{topic}에 관심을 가져주셔서 감사합니다.\n\n'
            '이 시리즈에서는 {topic}의 핵심을 단계별로 알려드리겠습니다.\n'
            '오늘은 간단한 소개와 함께 앞으로의 여정을 안내해 드릴게요.\n\n'
            '준비되셨나요? 다음 이메일에서 본격적으로 시작합니다.'
        ),
        'cta': '시리즈 전체 보기',
        'day_offset': 0,
    },
    {
        'role': '핵심 가치 전달',
        'subject_template': '{topic}의 핵심 — 이것만은 알아두세요',
        'body_template': (
            '{topic}에서 가장 중요한 포인트를 정리했습니다.\n\n'
            '1. 기본 개념 이해하기\n'
            '2. 흔한 실수 피하기\n'
            '3. 첫 번째 실천 단계\n\n'
            '이 세 가지를 숙지하면 {topic}의 80%를 이해한 것입니다.'
        ),
        'cta': '더 자세히 알아보기',
        'day_offset': 2,
    },
    {
        'role': '심화 콘텐츠',
        'subject_template': '{topic} 심화 — 한 단계 더 나아가기',
        'body_template': (
            '기본을 익히셨다면 이제 한 단계 더 깊이 들어가 봅시다.\n\n'
            '{topic}의 고급 전략과 실전 팁을 소개합니다.\n\n'
            '이번 이메일에서 다루는 내용:\n'
            '• 실전에서 바로 적용할 수 있는 기법\n'
            '• 전문가들이 추천하는 도구와 방법\n'
            '• 흔히 간과하는 핵심 포인트'
        ),
        'cta': '실전 가이드 다운로드',
        'day_offset': 4,
    },
    {
        'role': '사례/증거',
        'subject_template': '{topic} 성공 사례 — 실제로 이렇게 했습니다',
        'body_template': (
            '이론만으로는 부족하죠. 실제 사례를 살펴보겠습니다.\n\n'
            '{topic}을 활용하여 성과를 낸 구체적인 예시를 공유합니다.\n\n'
            '핵심 교훈:\n'
            '• 작게 시작하되 일관성을 유지\n'
            '• 데이터를 기반으로 개선\n'
            '• 피드백을 빠르게 반영'
        ),
        'cta': '사례 모음 보기',
        'day_offset': 7,
    },
    {
        'role': '행동 유도',
        'subject_template': '{topic} — 지금 바로 시작하세요',
        'body_template': (
            '시리즈의 마지막 이메일입니다.\n\n'
            '{topic}에 대해 충분히 알아보셨으니 이제 실행할 차례입니다.\n\n'
            '오늘 바로 할 수 있는 3가지:\n'
            '1. 목표를 구체적으로 설정하기\n'
            '2. 첫 번째 작은 행동 실행하기\n'
            '3. 결과를 기록하고 다음 단계 계획하기\n\n'
            '함께해서 감사했습니다. 궁금한 점이 있으면 언제든 연락주세요!'
        ),
        'cta': '무료 상담 신청하기',
        'day_offset': 10,
    },
    {
        'role': '리마인더',
        'subject_template': '{topic} 리마인더 — 놓치신 건 없으신가요?',
        'body_template': (
            '혹시 이전 이메일을 놓치셨을까 봐 핵심 내용을 다시 정리합니다.\n\n'
            '{topic}에서 꼭 기억해야 할 포인트:\n'
            '• 기본에 충실하기\n'
            '• 꾸준히 실천하기\n'
            '• 결과를 측정하기\n\n'
            '아직 시작하지 않으셨다면 지금이 가장 좋은 때입니다.'
        ),
        'cta': '다시 시작하기',
        'day_offset': 14,
    },
    {
        'role': '특별 제안',
        'subject_template': '{topic} 특별 안내 — 한정 기회',
        'body_template': (
            '{topic}에 대한 여정을 이어가실 분들을 위해\n'
            '특별한 기회를 준비했습니다.\n\n'
            '더 깊이 배우고 싶으시다면 이 기회를 놓치지 마세요.'
        ),
        'cta': '특별 제안 확인하기',
        'day_offset': 17,
    },
    {
        'role': '마무리/감사',
        'subject_template': '{topic} 시리즈를 마치며 — 감사합니다',
        'body_template': (
            '긴 여정을 함께해 주셔서 진심으로 감사드립니다.\n\n'
            '{topic}에 대해 더 궁금한 점이 있으시면\n'
            '언제든지 답장해 주세요.\n\n'
            '앞으로도 유용한 콘텐츠를 준비하겠습니다.\n'
            '좋은 하루 보내세요!'
        ),
        'cta': '뉴스레터 구독 유지하기',
        'day_offset': 21,
    },
]


def _calculate_day_schedule(num_emails: int) -> list:
    """이메일 수에 맞는 발송 일정을 계산합니다."""
    if num_emails <= 0:
        return []
    if num_emails <= len(_SEQUENCE_ROLES):
        return [_SEQUENCE_ROLES[i]['day_offset'] + 1 for i in range(num_emails)]

    # 기본 역할 수보다 많으면 균등 분배
    days = []
    total_span = max(num_emails * 3, 21)
    interval = total_span / num_emails
    for i in range(num_emails):
        days.append(int(i * interval) + 1)
    return days


def design_drip(topic: str, num_emails: int = 5) -> DripCampaign:
    """주제 기반 드립 이메일 캠페인을 설계합니다.

    Args:
        topic: 캠페인 주제 (예: 'SEO 최적화', 'Python 입문')
        num_emails: 생성할 이메일 수 (기본 5, 최대 20)

    Returns:
        DripCampaign
    """
    if not topic or not topic.strip():
        return DripCampaign(
            topic='(주제 없음)',
            emails=[],
            total_emails=0,
            estimated_days=0,
        )

    topic = topic.strip()
    num_emails = max(1, min(num_emails, 20))
    days = _calculate_day_schedule(num_emails)

    emails = []
    for i in range(num_emails):
        # 역할 템플릿 순환 사용
        role = _SEQUENCE_ROLES[i % len(_SEQUENCE_ROLES)]
        day = days[i]

        # 순환 시 제목/본문 약간 변형
        cycle = i // len(_SEQUENCE_ROLES)
        suffix = f" (Part {cycle + 1})" if cycle > 0 else ""

        subject = role['subject_template'].format(topic=topic) + suffix
        body = role['body_template'].format(topic=topic)
        cta = role['cta']

        emails.append(DripEmail(
            day=day,
            subject=subject,
            body=body,
            cta=cta,
        ))

    estimated_days = days[-1] if days else 0

    return DripCampaign(
        topic=topic,
        emails=emails,
        total_emails=len(emails),
        estimated_days=estimated_days,
    )
