"""
스마트 콘텐츠 생성기 설정 파일
AI 서비스, 스타일 옵션 정의
프롬프트 템플릿은 prompts/ 패키지에서 관리

v3.0 업데이트:
- 5개 핵심 스타일 (8개에서 축소)
- 2개 모디파이어 (7개에서 축소)
- 레거시 호환성 완전 제거
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
    'deepseek': os.getenv('DEEPSEEK_API_KEY', ''),
    'zhipuai': os.getenv('ZHIPUAI_API_KEY', ''),
}

# Supadata API Key (YouTube 자막 백업 서비스)
SUPADATA_API_KEY: str = os.getenv('SUPADATA_API_KEY', '')

# Token Limits (기본값, 모델별 설정이 없을 때 사용)
MAX_TRANSCRIPT_TOKENS: int = 100000
MAX_COMMENTS_TOKENS: int = 5000
MAX_CONTENT_TOKENS: int = 100000  # 기본 fallback 값

# 히스토리 보존 기간 (일)
HISTORY_RETENTION_DAYS: int = 7

# 지원 AI 서비스 정의 (max_input_tokens: 컨텍스트 윈도우의 ~75% 할당)
# Gemini가 기본 프로바이더 (첫 번째 위치)
SUPPORTED_PROVIDERS: Dict[str, Dict[str, Any]] = {
    'gemini': {
        'name': 'Google Gemini',
        'models': [
            {'id': 'gemini/gemini-3-flash-preview', 'name': 'Gemini 3.0 Flash', 'max_input_tokens': 750000, 'price_input': 0.50, 'price_output': 3.00},
            {'id': 'gemini/gemini-2.5-flash-lite-preview-09-2025', 'name': 'Gemini 2.5 Flash Lite', 'max_input_tokens': 750000, 'price_input': 0.10, 'price_output': 0.40},
        ]
    },
    'deepseek': {
        'name': 'DeepSeek',
        'models': [
            {'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek-V3 (채팅)', 'max_input_tokens': 96000, 'price_input': 0.27, 'price_output': 1.10},
            {'id': 'deepseek/deepseek-reasoner', 'name': 'DeepSeek-R1 (추론)', 'max_input_tokens': 96000, 'price_input': 0.55, 'price_output': 2.19}
        ]
    },
    'zhipuai': {
        'name': 'Zhipu AI (GLM)',
        'api_base': 'https://open.bigmodel.cn/api/paas/v4/',
        'models': [
            {'id': 'zhipuai/GLM-4.7', 'name': 'GLM-4.7 (최신)', 'max_input_tokens': 128000, 'price_input': 1.00, 'price_output': 1.00},
            {'id': 'zhipuai/GLM-4.5-Air', 'name': 'GLM-4.5 Air (경량)', 'max_input_tokens': 128000, 'price_input': 0.10, 'price_output': 0.10},
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
    elif model_id.startswith('deepseek/'):
        return 'deepseek'
    elif model_id.startswith('zhipuai/'):
        return 'zhipuai'
    return 'gemini'  # 기본값 (Gemini)


# ============================================================
# 스타일 옵션 v3.1 (8개 스타일)
# ============================================================

STYLE_OPTIONS: List[Tuple[str, str]] = [
    ('blog_seo', '🔍 블로그+SEO'),
    ('summary', '⚡ 요약'),
    ('tutorial', '📚 튜토리얼'),
    ('qna', '❓ Q&A'),
    ('app_ideas', '💡 앱 아이디어'),
    ('yozm_it', '💻 요즘IT'),
    ('brunch_essay', '✍️ 브런치'),
    ('naver_popular', '💚 네이버'),
]


# ============================================================
# 모디파이어 v3.0 (2개)
# ============================================================

# 모디파이어 텍스트 버전 (간단한 설명용)
STYLE_MODIFIERS: Dict[str, Dict[str, str]] = {
    'length': {
        'short': '총 분량은 약 500~800자로 핵심만 간결하게 작성하세요.',
        'medium': '총 분량은 약 1000~1500자로 적절히 작성하세요.',
        'long': '총 분량은 약 2000~3000자로 상세하고 풍부하게 작성하세요.'
    },
    'writing_style': {
        'conversational': '대화체(~요, ~해요)로 친근하게 작성하세요.',
        'explanatory': '설명체(~입니다, ~합니다)로 객관적으로 작성하세요.',
        'casual': '캐주얼체(~야, ~해)로 편하게 작성하세요.',
        'expert': '전문가 톤으로 업계 용어를 사용해 깊이 있게 작성하세요.'
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


def get_style_options() -> List[Tuple[str, str]]:
    """
    스타일 옵션 목록을 반환합니다.

    Returns:
        (style_id, label) 튜플 리스트
    """
    return STYLE_OPTIONS


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

    # Styles (v3.0)
    'STYLE_OPTIONS',
    'STYLE_PROMPTS',
    'get_style_options',

    # Modifiers (v3.0)
    'STYLE_MODIFIERS',
    'MODIFIER_OPTIONS',
    'DEFAULT_MODIFIERS',
    'get_modifier_options',

    # Prompt Builder
    'build_full_prompt',
]
