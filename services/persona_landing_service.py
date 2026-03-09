"""
페르소나 랜딩 페이지 서비스

주제와 페르소나(대상 사용자 유형)에 따라
맞춤형 랜딩 페이지 구조를 생성합니다.
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# 지원되는 페르소나 목록
SUPPORTED_PERSONAS = ('developer', 'marketer', 'executive', 'student', 'creator')


@dataclass
class LandingSection:
    """랜딩 페이지의 개별 섹션"""
    title: str
    content: str
    section_type: str  # hero, features, benefits, social_proof, faq, pricing, cta


@dataclass
class LandingPage:
    """페르소나별 맞춤 랜딩 페이지 전체 구조"""
    persona: str
    topic: str
    headline: str
    subheadline: str
    sections: List[LandingSection]
    cta_text: str
    tone: str  # technical, persuasive, formal, friendly, creative


# 페르소나별 설정: 톤, 관심 키워드, CTA 템플릿, 섹션 구성
_PERSONA_CONFIGS = {
    'developer': {
        'tone': 'technical',
        'interests': ['성능', '확장성', 'API', '코드 품질', '개발 생산성', '문서화'],
        'cta_template': '{topic} 시작하기 — 무료 API 키 발급',
        'headline_template': '{topic}: 개발자를 위한 기술 가이드',
        'subheadline_template': '빠른 통합, 풍부한 문서, 검증된 성능으로 개발 시간을 단축하세요.',
        'section_types': ['hero', 'features', 'benefits', 'faq', 'cta'],
        'section_focus': {
            'features': '기술 스펙과 API 인터페이스 중심으로 핵심 기능을 설명합니다.',
            'benefits': '개발 생산성 향상, 코드 품질 개선, 유지보수 비용 절감 효과를 제시합니다.',
            'faq': '통합 방법, 지원 언어/프레임워크, 성능 벤치마크 등 기술 FAQ를 다룹니다.',
        },
    },
    'marketer': {
        'tone': 'persuasive',
        'interests': ['ROI', '전환율', '고객 확보', '브랜드', '데이터 분석', '캠페인'],
        'cta_template': '{topic}로 마케팅 성과 높이기',
        'headline_template': '{topic}: 마케팅 성과를 바꾸는 솔루션',
        'subheadline_template': '데이터 기반 인사이트로 캠페인 ROI를 극대화하세요.',
        'section_types': ['hero', 'benefits', 'social_proof', 'features', 'cta'],
        'section_focus': {
            'benefits': 'ROI 향상, 전환율 개선, 고객 인사이트 확보 등 비즈니스 성과를 강조합니다.',
            'social_proof': '성공 사례, 고객 후기, 주요 지표 개선 수치를 제시합니다.',
            'features': '캠페인 관리, 분석 대시보드, A/B 테스트 등 마케터 친화 기능을 소개합니다.',
        },
    },
    'executive': {
        'tone': 'formal',
        'interests': ['비용 절감', '시장 경쟁력', '리스크 관리', '전략', '성장', '효율'],
        'cta_template': '{topic} 도입 상담 예약',
        'headline_template': '{topic}: 비즈니스 성장을 위한 전략적 선택',
        'subheadline_template': '검증된 솔루션으로 운영 효율을 높이고 경쟁 우위를 확보하세요.',
        'section_types': ['hero', 'benefits', 'social_proof', 'pricing', 'cta'],
        'section_focus': {
            'benefits': '비용 절감, 운영 효율화, 리스크 감소 등 경영진 관점의 가치를 제시합니다.',
            'social_proof': '업계 리더 기업의 도입 사례와 정량적 성과 지표를 보여줍니다.',
            'pricing': '도입 비용 대비 기대 ROI와 단계별 도입 옵션을 안내합니다.',
        },
    },
    'student': {
        'tone': 'friendly',
        'interests': ['학습', '실습', '포트폴리오', '무료', '커뮤니티', '취업'],
        'cta_template': '{topic} 무료로 배우기',
        'headline_template': '{topic}: 쉽게 시작하는 학습 가이드',
        'subheadline_template': '단계별 튜토리얼과 실습 예제로 빠르게 역량을 키우세요.',
        'section_types': ['hero', 'features', 'benefits', 'faq', 'cta'],
        'section_focus': {
            'features': '단계별 학습 경로, 실습 환경, 예제 프로젝트 등 교육 콘텐츠를 소개합니다.',
            'benefits': '포트폴리오 구축, 실무 역량 강화, 취업 경쟁력 확보 효과를 설명합니다.',
            'faq': '선수 지식, 학습 시간, 수료 인증, 커뮤니티 지원 등 학생 FAQ를 다룹니다.',
        },
    },
    'creator': {
        'tone': 'creative',
        'interests': ['콘텐츠', '크리에이티브', '수익화', '팔로워', '브랜딩', '협업'],
        'cta_template': '{topic}로 콘텐츠 제작 시작하기',
        'headline_template': '{topic}: 크리에이터를 위한 제작 도구',
        'subheadline_template': '아이디어를 콘텐츠로, 콘텐츠를 수익으로 전환하세요.',
        'section_types': ['hero', 'features', 'social_proof', 'benefits', 'cta'],
        'section_focus': {
            'features': '콘텐츠 제작 도구, 템플릿, AI 어시스턴트 등 크리에이터 친화 기능을 소개합니다.',
            'social_proof': '인기 크리에이터의 활용 사례, 팔로워 성장 스토리를 공유합니다.',
            'benefits': '제작 시간 단축, 콘텐츠 품질 향상, 수익화 기회 확대 효과를 강조합니다.',
        },
    },
}


def _build_section(
    section_type: str,
    topic: str,
    config: dict,
) -> LandingSection:
    """페르소나 설정에 따라 개별 섹션을 생성합니다."""
    focus = config.get('section_focus', {})
    interests = config.get('interests', [])
    interests_text = ', '.join(interests[:3])

    # 섹션 유형별 기본 콘텐츠 생성
    section_templates = {
        'hero': {
            'title': f'{topic} 소개',
            'content': f'{topic}에 대한 핵심 가치를 한눈에 전달합니다. '
                       f'주요 관심사: {interests_text}.',
        },
        'features': {
            'title': '주요 기능',
            'content': focus.get('features',
                                 f'{topic}의 핵심 기능을 소개합니다.'),
        },
        'benefits': {
            'title': '도입 효과',
            'content': focus.get('benefits',
                                 f'{topic} 도입으로 얻을 수 있는 이점을 설명합니다.'),
        },
        'social_proof': {
            'title': '성공 사례',
            'content': focus.get('social_proof',
                                 f'{topic}을 활용한 성공 사례와 고객 후기를 공유합니다.'),
        },
        'faq': {
            'title': '자주 묻는 질문',
            'content': focus.get('faq',
                                 f'{topic}에 대해 자주 묻는 질문과 답변을 제공합니다.'),
        },
        'pricing': {
            'title': '가격 안내',
            'content': focus.get('pricing',
                                 f'{topic} 도입 비용과 플랜을 안내합니다.'),
        },
        'cta': {
            'title': '지금 시작하세요',
            'content': f'{config["cta_template"].format(topic=topic)} — '
                       f'지금 바로 {topic}을 경험해보세요.',
        },
    }

    template = section_templates.get(section_type, {
        'title': section_type,
        'content': f'{topic} 관련 콘텐츠입니다.',
    })

    return LandingSection(
        title=template['title'],
        content=template['content'],
        section_type=section_type,
    )


def generate_landing(topic: str, persona: str) -> LandingPage:
    """페르소나별 맞춤 랜딩 페이지를 생성합니다.

    Args:
        topic: 랜딩 페이지 주제 (예: "AI 코드 리뷰 도구")
        persona: 대상 사용자 유형
            "developer", "marketer", "executive", "student", "creator"

    Returns:
        LandingPage 데이터클래스 인스턴스

    Raises:
        ValueError: 지원하지 않는 페르소나일 때
    """
    if not topic or not topic.strip():
        raise ValueError("topic은 빈 문자열일 수 없습니다.")

    persona = persona.strip().lower()
    if persona not in SUPPORTED_PERSONAS:
        raise ValueError(
            f"지원하지 않는 페르소나: '{persona}'. "
            f"지원 목록: {', '.join(SUPPORTED_PERSONAS)}"
        )

    config = _PERSONA_CONFIGS[persona]
    topic = topic.strip()

    # 헤드라인/서브헤드라인 생성
    headline = config['headline_template'].format(topic=topic)
    subheadline = config['subheadline_template'].format(topic=topic)
    cta_text = config['cta_template'].format(topic=topic)
    tone = config['tone']

    # 섹션 빌드
    sections: List[LandingSection] = []
    for section_type in config['section_types']:
        section = _build_section(section_type, topic, config)
        sections.append(section)

    page = LandingPage(
        persona=persona,
        topic=topic,
        headline=headline,
        subheadline=subheadline,
        sections=sections,
        cta_text=cta_text,
        tone=tone,
    )

    logger.info(f"랜딩 페이지 생성: persona={persona}, topic={topic}, "
                f"sections={len(sections)}")
    return page
