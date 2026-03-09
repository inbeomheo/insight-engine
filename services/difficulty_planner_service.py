"""
난이도 플래닝 서비스

주제와 도메인에 따라 난이도별 학습 경로를 생성.
규칙 기반 (AI API 호출 없음).
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class DifficultyLevel:
    """단일 난이도 단계."""
    level: str             # "beginner", "intermediate", "advanced", "expert"
    name: str              # 한국어 표시명
    description: str       # 이 단계 설명
    prerequisites: List[str]
    estimated_time: str    # 예상 소요 시간


@dataclass
class DifficultyPlan:
    """난이도 플랜 전체."""
    topic: str
    domain: str
    levels: List[DifficultyLevel]
    recommended_start: str  # 권장 시작 레벨


# ── 레벨 메타데이터 ──
_LEVEL_ORDER = ['beginner', 'intermediate', 'advanced', 'expert']

_LEVEL_NAMES = {
    'beginner': '입문',
    'intermediate': '중급',
    'advanced': '고급',
    'expert': '전문가',
}

# ── 도메인별 커리큘럼 템플릿 ──
_DOMAIN_CURRICULA: Dict[str, Dict[str, dict]] = {
    'programming': {
        'beginner': {
            'description': '{topic}의 기본 개념과 문법을 학습합니다. 간단한 예제를 통해 핵심 원리를 이해합니다.',
            'prerequisites': [],
            'estimated_time': '2-4주',
        },
        'intermediate': {
            'description': '{topic}의 중급 패턴과 실무 활용법을 다룹니다. 프로젝트 구조와 모범 사례를 익힙니다.',
            'prerequisites': ['기본 문법 이해', '간단한 프로그램 작성 경험'],
            'estimated_time': '4-8주',
        },
        'advanced': {
            'description': '{topic}의 아키텍처 설계, 성능 최적화, 테스트 전략을 학습합니다.',
            'prerequisites': ['중급 패턴 숙지', '실무 프로젝트 경험'],
            'estimated_time': '8-12주',
        },
        'expert': {
            'description': '{topic}의 내부 구현 원리, 오픈소스 기여, 기술 리더십을 다룹니다.',
            'prerequisites': ['고급 아키텍처 설계 능력', '대규모 시스템 운영 경험'],
            'estimated_time': '12주 이상',
        },
    },
    'design': {
        'beginner': {
            'description': '{topic}의 기초 원리와 도구 사용법을 학습합니다.',
            'prerequisites': [],
            'estimated_time': '2-4주',
        },
        'intermediate': {
            'description': '{topic}의 디자인 시스템, 사용자 리서치, 프로토타이핑을 다룹니다.',
            'prerequisites': ['기본 도구 사용 능력', '디자인 원칙 이해'],
            'estimated_time': '4-8주',
        },
        'advanced': {
            'description': '{topic}의 고급 UX 전략, 접근성, 디자인 리더십을 학습합니다.',
            'prerequisites': ['중급 디자인 시스템 경험', '포트폴리오 보유'],
            'estimated_time': '8-12주',
        },
        'expert': {
            'description': '{topic}의 비즈니스 전략 연계, 디자인 조직 구축, 혁신 프레임워크를 다룹니다.',
            'prerequisites': ['고급 UX 전략 수립 능력', '팀 리딩 경험'],
            'estimated_time': '12주 이상',
        },
    },
    'marketing': {
        'beginner': {
            'description': '{topic}의 기본 개념과 채널별 특성을 학습합니다.',
            'prerequisites': [],
            'estimated_time': '1-3주',
        },
        'intermediate': {
            'description': '{topic}의 캠페인 기획, 데이터 분석, A/B 테스트를 다룹니다.',
            'prerequisites': ['마케팅 기초 이해', '기본 분석 도구 사용'],
            'estimated_time': '3-6주',
        },
        'advanced': {
            'description': '{topic}의 고급 전략 수립, 자동화, ROI 최적화를 학습합니다.',
            'prerequisites': ['캠페인 운영 경험', '데이터 분석 능력'],
            'estimated_time': '6-10주',
        },
        'expert': {
            'description': '{topic}의 조직 차원 전략, 브랜드 구축, 마켓 리더십을 다룹니다.',
            'prerequisites': ['고급 전략 수립 경험', '예산 관리 경험'],
            'estimated_time': '10주 이상',
        },
    },
    'general': {
        'beginner': {
            'description': '{topic}의 핵심 개념과 기초 원리를 학습합니다.',
            'prerequisites': [],
            'estimated_time': '2-4주',
        },
        'intermediate': {
            'description': '{topic}의 실무 활용법과 응용 기술을 다룹니다.',
            'prerequisites': ['기초 개념 이해'],
            'estimated_time': '4-8주',
        },
        'advanced': {
            'description': '{topic}의 심화 이론과 전문 영역을 학습합니다.',
            'prerequisites': ['실무 활용 경험', '중급 수준 이해'],
            'estimated_time': '8-12주',
        },
        'expert': {
            'description': '{topic}의 최신 연구, 리더십, 전문가 수준 기술을 다룹니다.',
            'prerequisites': ['심화 이론 숙지', '실전 프로젝트 다수 경험'],
            'estimated_time': '12주 이상',
        },
    },
}


def plan_difficulty(topic: str, domain: str = 'general') -> DifficultyPlan:
    """주제와 도메인에 따라 난이도별 학습 경로를 생성합니다.

    Args:
        topic: 학습 주제
        domain: 도메인 ("programming", "design", "marketing", "general")

    Returns:
        DifficultyPlan (4단계 난이도 포함)
    """
    if not topic or not topic.strip():
        topic = "미정"

    # 지원하지 않는 도메인은 general로 폴백
    effective_domain = domain if domain in _DOMAIN_CURRICULA else 'general'
    curriculum = _DOMAIN_CURRICULA[effective_domain]

    levels = []
    for level_key in _LEVEL_ORDER:
        template = curriculum[level_key]
        levels.append(DifficultyLevel(
            level=level_key,
            name=_LEVEL_NAMES[level_key],
            description=template['description'].format(topic=topic),
            prerequisites=list(template['prerequisites']),
            estimated_time=template['estimated_time'],
        ))

    # 권장 시작 레벨: 항상 beginner (규칙 기반)
    recommended = 'beginner'

    return DifficultyPlan(
        topic=topic,
        domain=effective_domain,
        levels=levels,
        recommended_start=recommended,
    )


def get_supported_domains() -> List[str]:
    """지원하는 도메인 목록을 반환합니다."""
    return sorted(_DOMAIN_CURRICULA.keys())


def get_level_by_name(plan: DifficultyPlan, level: str) -> Optional[DifficultyLevel]:
    """플랜에서 특정 레벨을 찾습니다.

    Args:
        plan: DifficultyPlan
        level: 레벨 키 ("beginner", "intermediate", "advanced", "expert")

    Returns:
        DifficultyLevel 또는 None
    """
    for dl in plan.levels:
        if dl.level == level:
            return dl
    return None


def estimate_total_time(plan: DifficultyPlan) -> str:
    """전체 학습 경로의 총 예상 시간을 계산합니다.

    각 레벨의 estimated_time에서 최소/최대 주 수를 추출하여 합산합니다.

    Args:
        plan: DifficultyPlan

    Returns:
        "N-M주" 형식 문자열
    """
    import re
    total_min = 0
    total_max = 0

    for level in plan.levels:
        # "2-4주", "12주 이상" 등에서 숫자 추출
        numbers = re.findall(r'\d+', level.estimated_time)
        if len(numbers) >= 2:
            total_min += int(numbers[0])
            total_max += int(numbers[1])
        elif len(numbers) == 1:
            val = int(numbers[0])
            total_min += val
            total_max += val + 4  # "이상"인 경우 +4주 여유

    return f"{total_min}-{total_max}주"
