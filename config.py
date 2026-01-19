"""
스마트 콘텐츠 생성기 설정 파일
AI 서비스, 스타일 옵션 정의
프롬프트 템플릿은 prompts/ 패키지에서 관리

v2.0 업데이트:
- 8개 핵심 스타일 (15개에서 통합)
- 7개 모디파이어 (4개에서 확장)
- 베이스 프롬프트 + 스타일 오버라이드 구조
"""
from typing import Dict, List, Any, Tuple
import os

# prompts 패키지에서 가져오기
from prompts import (
    STYLE_PROMPTS,
    MODIFIER_OPTIONS,
    DEFAULT_MODIFIERS,
    build_full_prompt,
    get_available_styles,
)

# YouTube API Key
YOUTUBE_API_KEY: str = os.getenv('YOUTUBE_API_KEY', '')

# AI Provider API Keys (환경변수에서 로드)
PROVIDER_API_KEYS: Dict[str, str] = {
    'openai': os.getenv('OPENAI_API_KEY', ''),
    'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
    'gemini': os.getenv('GEMINI_API_KEY', ''),
    'zhipu': os.getenv('ZHIPU_API_KEY', ''),
    'deepseek': os.getenv('DEEPSEEK_API_KEY', ''),
}

# Supadata API Key (YouTube 자막 백업 서비스)
SUPADATA_API_KEY: str = os.getenv('SUPADATA_API_KEY', '')

# Token Limits (기본값, 모델별 설정이 없을 때 사용)
MAX_TRANSCRIPT_TOKENS: int = 100000
MAX_COMMENTS_TOKENS: int = 5000
MAX_CONTENT_TOKENS: int = 100000  # 기본 fallback 값

# 지원 AI 서비스 정의 (max_input_tokens: 컨텍스트 윈도우의 ~75% 할당)
SUPPORTED_PROVIDERS: Dict[str, Dict[str, Any]] = {
    'gemini': {
        'name': 'Google Gemini',
        'models': [
            {'id': 'gemini/gemini-2.5-flash-lite-preview-09-2025', 'name': 'Gemini 2.5 Flash Lite', 'max_input_tokens': 750000},
        ]
    },
    'deepseek': {
        'name': 'DeepSeek',
        'models': [
            {'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek-V3 (채팅)', 'max_input_tokens': 96000},
            {'id': 'deepseek/deepseek-reasoner', 'name': 'DeepSeek-R1 (추론)', 'max_input_tokens': 96000}
        ]
    }
}


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """API 키가 설정된 프로바이더만 반환합니다."""
    available = {}
    for provider_id, api_key in PROVIDER_API_KEYS.items():
        if api_key and provider_id in SUPPORTED_PROVIDERS:
            available[provider_id] = SUPPORTED_PROVIDERS[provider_id]
    return available


def get_provider_from_model(model_id: str) -> str:
    """모델 ID에서 프로바이더를 추출합니다."""
    if model_id.startswith('gpt-'):
        return 'openai'
    elif model_id.startswith('claude-'):
        return 'anthropic'
    elif model_id.startswith('gemini/'):
        return 'gemini'
    elif model_id.startswith('glm-'):
        return 'zhipu'
    elif model_id.startswith('deepseek/'):
        return 'deepseek'
    return 'openai'  # 기본값


# ============================================================
# 스타일 옵션 v2.0 (8개 핵심 스타일)
# ============================================================

STYLE_OPTIONS: List[Tuple[str, str]] = [
    ('professional', '📝 전문 블로그/아티클'),
    ('summary', '⚡ 핵심 요약 리포트'),
    ('tutorial', '📚 단계별 튜토리얼'),
    ('review', '⭐ 리뷰/비교 분석'),
    ('seo', '🔍 SEO 최적화'),
    ('creative', '🎬 크리에이티브 (숏폼/SNS)'),
    ('analysis', '📊 분석 리포트'),
    ('structured', '📋 구조화된 정보'),
]

# 하위 호환성: 레거시 스타일 옵션 (UI에서 기존 스타일명 사용 시)
LEGACY_STYLE_OPTIONS: List[Tuple[str, str]] = [
    ('blog', '📝 블로그 포스트'),
    ('detailed', '📝 상세 요약'),
    ('summary', '⚡ 핵심 요약'),
    ('easy', '🎯 쉬운 설명'),
    ('news', '📰 뉴스 스타일'),
    ('script', '🎬 스크립트'),
    ('seo', '🔍 SEO 최적화'),
    ('needs', '💡 니즈/아이템 분석'),
    ('qna', '❓ Q&A 형식'),
    ('infographic', '📊 인포그래픽용'),
    ('compare', '⚖️ 비교분석'),
    ('sns', '📱 SNS 포스팅'),
    ('review', '⭐ 리뷰'),
    ('tutorial', '📚 튜토리얼'),
    ('newsletter', '✉️ 뉴스레터'),
]

# 스타일 매핑 (레거시 → 새 스타일)
STYLE_MAPPING: Dict[str, str] = {
    'blog': 'professional',
    'detailed': 'professional',
    'news': 'professional',
    'easy': 'tutorial',
    'script': 'creative',
    'sns': 'creative',
    'needs': 'analysis',
    'infographic': 'analysis',
    'qna': 'structured',
    'mindmap': 'structured',
    'newsletter': 'structured',
    'compare': 'review',
}


# ============================================================
# 모디파이어 v2.0 (7개로 확장)
# ============================================================

# 새 모디파이어 시스템 (prompts/modifiers.py에서 import)
# MODIFIER_OPTIONS: UI 표시용 옵션 정보
# DEFAULT_MODIFIERS: 기본값

# 하위 호환성: 레거시 STYLE_MODIFIERS (간단한 텍스트 버전)
STYLE_MODIFIERS: Dict[str, Dict[str, str]] = {
    'length': {
        'short': '총 분량은 약 300~500자로 핵심만 간결하게 작성하세요.',
        'medium': '총 분량은 약 800~1200자로 적절히 작성하세요.',
        'long': '총 분량은 약 1500자 이상으로 상세하고 풍부하게 작성하세요.'
    },
    'tone': {
        'professional': '말투는 전문적이고 객관적인 스타일로 작성하세요. 경어체(~습니다, ~입니다)를 사용하세요.',
        'friendly': '말투는 친근하고 대화하듯이 작성하세요. 부드러운 어조로 독자와 소통하는 느낌을 주세요.',
        'humorous': '말투는 유머러스하고 재치있게 작성하세요. 적절한 위트와 가벼운 농담을 포함하세요.'
    },
    'language': {
        'ko': '결과는 반드시 한국어로 작성해주세요.',
        'en': 'Please write the result in English.',
        'ja': '結果は必ず日本語で作成してください。'
    },
    'emoji': {
        'use': '적절한 이모지를 활용하여 가독성과 재미를 높이세요. 각 섹션이나 중요 포인트에 이모지를 추가하세요.',
        'none': '이모지는 사용하지 마세요. 텍스트만으로 작성하세요.'
    },
    # 신규 모디파이어
    'target': {
        'general': '일반 독자 대상으로 전문 용어 사용 시 설명을 추가하세요.',
        'expert': '전문가 대상으로 심층적인 분석과 업계 맥락을 포함하세요.',
        'beginner': '입문자 대상으로 기초부터 친절하게 설명하세요.'
    },
    'focus': {
        'actionable': '실행 가능한 팁과 액션 아이템 중심으로 작성하세요.',
        'informative': '정보 전달과 개념 설명 중심으로 작성하세요.',
        'persuasive': '논리적 근거와 설득력 있는 구조로 작성하세요.'
    },
    'depth': {
        'overview': '개요 수준으로 핵심만 빠르게 훑으세요.',
        'detailed': '상세하게 각 포인트를 충분히 설명하세요.',
        'comprehensive': '종합적으로 모든 측면을 빠짐없이 다루세요.'
    }
}


# ============================================================
# 유틸리티 함수
# ============================================================

def get_model_max_tokens(model_id: str) -> int:
    """모델 ID로 최대 입력 토큰 수를 반환합니다."""
    for provider in SUPPORTED_PROVIDERS.values():
        for model in provider.get('models', []):
            if model['id'] == model_id:
                return model.get('max_input_tokens', MAX_CONTENT_TOKENS)
    return MAX_CONTENT_TOKENS  # fallback


def normalize_style(style: str) -> str:
    """레거시 스타일 이름을 새 스타일로 변환합니다."""
    return STYLE_MAPPING.get(style, style)


def get_style_options(use_legacy: bool = False) -> List[Tuple[str, str]]:
    """
    스타일 옵션 목록을 반환합니다.

    Args:
        use_legacy: True면 기존 15개 스타일, False면 새 8개 스타일

    Returns:
        (style_id, label) 튜플 리스트
    """
    return LEGACY_STYLE_OPTIONS if use_legacy else STYLE_OPTIONS


def get_modifier_options() -> Dict[str, Dict[str, Any]]:
    """
    모디파이어 옵션 정보를 반환합니다 (UI 구성용).

    Returns:
        MODIFIER_OPTIONS 딕셔너리
    """
    return MODIFIER_OPTIONS


# ============================================================
# Export
# ============================================================

__all__ = [
    # API Keys
    'YOUTUBE_API_KEY',
    'PROVIDER_API_KEYS',
    'SUPADATA_API_KEY',

    # Token Limits
    'MAX_TRANSCRIPT_TOKENS',
    'MAX_COMMENTS_TOKENS',
    'MAX_CONTENT_TOKENS',

    # Providers
    'SUPPORTED_PROVIDERS',
    'get_available_providers',
    'get_provider_from_model',
    'get_model_max_tokens',

    # Styles (v2.0)
    'STYLE_OPTIONS',
    'LEGACY_STYLE_OPTIONS',
    'STYLE_MAPPING',
    'STYLE_PROMPTS',
    'normalize_style',
    'get_style_options',

    # Modifiers (v2.0)
    'STYLE_MODIFIERS',
    'MODIFIER_OPTIONS',
    'DEFAULT_MODIFIERS',
    'get_modifier_options',

    # Prompt Builder
    'build_full_prompt',
]
