"""
스마트 콘텐츠 생성기 설정 파일
AI 서비스, 스타일 옵션 정의
프롬프트 템플릿은 prompts.py에서 관리
"""
from typing import Dict, List, Any
import os

# prompts.py에서 프롬프트 가져오기
from prompts import STYLE_PROMPTS

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
            {'id': 'gemini/gemini-2.0-flash-lite', 'name': 'Gemini 2.0 Flash Lite', 'max_input_tokens': 750000},
            {'id': 'gemini/gemini-flash-lite-latest', 'name': 'Gemini Flash Lite (Latest)', 'max_input_tokens': 750000},
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

# 스타일/톤 옵션
STYLE_OPTIONS: List[tuple] = [
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
    ('sns', '📱 SNS 포스팅')
]

# 세부 옵션 (길이, 톤, 언어, 이모지)
STYLE_MODIFIERS: Dict[str, Dict[str, str]] = {
    'length': {
        'short': '총 분량은 약 300자 내외로 핵심만 간결하게 작성하세요.',
        'medium': '총 분량은 약 800자 내외로 적절히 작성하세요.',
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
    }
}

# STYLE_PROMPTS는 prompts.py에서 import됨

def get_model_max_tokens(model_id: str) -> int:
    """모델 ID로 최대 입력 토큰 수를 반환합니다."""
    for provider in SUPPORTED_PROVIDERS.values():
        for model in provider.get('models', []):
            if model['id'] == model_id:
                return model.get('max_input_tokens', MAX_CONTENT_TOKENS)
    return MAX_CONTENT_TOKENS  # fallback

__all__ = [
    'YOUTUBE_API_KEY',
    'PROVIDER_API_KEYS',
    'SUPADATA_API_KEY',
    'MAX_TRANSCRIPT_TOKENS',
    'MAX_COMMENTS_TOKENS',
    'MAX_CONTENT_TOKENS',
    'SUPPORTED_PROVIDERS',
    'STYLE_OPTIONS',
    'STYLE_MODIFIERS',
    'STYLE_PROMPTS',
    'get_model_max_tokens',
    'get_available_providers',
    'get_provider_from_model'
]
