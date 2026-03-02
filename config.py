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

# === API Keys ===

YOUTUBE_API_KEY: str = os.getenv('YOUTUBE_API_KEY', '')

PROVIDER_API_KEYS: Dict[str, str] = {
    'openai': os.getenv('OPENAI_API_KEY', ''),
    'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
    'gemini': os.getenv('GEMINI_API_KEY', ''),
    'deepseek': os.getenv('DEEPSEEK_API_KEY', ''),
    'zhipuai': os.getenv('ZHIPUAI_API_KEY', ''),
    'ollama': os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434'),
    'openrouter': os.getenv('OPENROUTER_API_KEY', ''),
}

SUPADATA_API_KEY: str = os.getenv('SUPADATA_API_KEY', '')

# === 웹 검색 보강 (Grounded Generation) ===

TAVILY_API_KEY: str = os.getenv('TAVILY_API_KEY', '')
WEB_SEARCH_ENABLED: bool = os.getenv('WEB_SEARCH_ENABLED', 'false').lower() == 'true'
WEB_SEARCH_MAX_RESULTS: int = int(os.getenv('WEB_SEARCH_MAX_RESULTS', '5'))

# === RAG (지식 참조) ===

RAG_ENABLED: bool = os.environ.get('RAG_ENABLED', 'false').lower() == 'true'
CHROMA_DB_PATH: str = os.environ.get('CHROMA_DB_PATH', './data/chroma_db')
RAG_TOP_K: int = int(os.environ.get('RAG_TOP_K', '5'))

# === GraphRAG (지식 그래프 + 리랭킹) ===

GRAPH_RAG_ENABLED: bool = os.environ.get('GRAPH_RAG_ENABLED', 'false').lower() == 'true'
GRAPH_STORE_PATH: str = os.environ.get('GRAPH_STORE_PATH', './data/graph_store')
RERANKER_ENABLED: bool = os.environ.get('RERANKER_ENABLED', 'false').lower() == 'true'
RERANKER_TOP_K: int = int(os.environ.get('RERANKER_TOP_K', '5'))

# === Whisper (음성 인식 자막 폴백) ===

WHISPER_ENABLED: bool = os.getenv('WHISPER_ENABLED', 'false').lower() == 'true'
WHISPER_MODEL_SIZE: str = os.getenv('WHISPER_MODEL_SIZE', 'base')

# === TTS (텍스트 → 오디오 변환) ===

TTS_ENABLED: bool = os.getenv('TTS_ENABLED', 'false').lower() == 'true'
TTS_BACKEND: str = os.getenv('TTS_BACKEND', 'auto')   # 'openai', 'edge', 'auto'
TTS_DEFAULT_VOICE: str = os.getenv('TTS_DEFAULT_VOICE', 'alloy')
TTS_MAX_CHARS: int = 5000

# === Webhook ===

WEBHOOK_URL: str = os.getenv('WEBHOOK_URL', '')
WEBHOOK_ENABLED: bool = os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true'

# === Content Limits ===

MAX_TRANSCRIPT_TOKENS: int = 100000
MAX_COMMENTS_TOKENS: int = 5000
MAX_CONTENT_TOKENS: int = 100000  # 기본 fallback 값
HISTORY_RETENTION_DAYS: int = 7  # 히스토리 보존 기간 (일)

# === Short Content Bypass ===

SHORT_CONTENT_THRESHOLD: int = 500  # 자 미만이면 AI 호출 바이패스
SHORT_CONTENT_BYPASS_STYLES = {'summary'}  # 바이패스 대상 스타일

# === AI Cache ===

AI_CACHE_DB = os.path.join(os.path.dirname(__file__), 'cache', 'ai_results.db')
AI_CACHE_TTL_DAYS = 30
AI_CACHE_MAX_SIZE_MB = 512

# === AI Model & Fallback ===

FALLBACK_CHAIN = [
    'zhipuai/GLM-4.5-Air',
    'zhipuai/GLM-4.7',
]
MAX_FALLBACK_ATTEMPTS = 3

# === Style Tuning ===
# 스타일별 temperature (정밀형 0.5 / 균형형 0.7 / 창의형 0.85)
STYLE_TEMPERATURE: Dict[str, float] = {
    'summary': 0.5, 'tutorial': 0.5, 'qna': 0.5, 'show_notes': 0.5, 'geo_seo': 0.5, 'course': 0.5,
    'blog_seo': 0.7, 'yozm_it': 0.7, 'app_ideas': 0.7, 'newsletter': 0.7, 'shorts_script': 0.7,
    'brunch_essay': 0.85, 'naver_popular': 0.85, 'sns_post': 0.8,
    'comment_summary': 0.5,
}

# 길이별 max_tokens (한국어 2~3토큰/자 + 마크다운 오버헤드 ~40% 감안)
LENGTH_MAX_TOKENS: Dict[str, int] = {
    'short': 4000, 'medium': 8000, 'long': 16000,
}

# === Providers ===

SUPPORTED_PROVIDERS: Dict[str, Dict[str, Any]] = {
    'zhipuai': {
        'name': 'Zhipu AI (GLM)',
        'api_base': 'https://open.bigmodel.cn/api/paas/v4/',
        'models': [
            {'id': 'zhipuai/GLM-4.7', 'name': 'GLM-4.7 (최신)', 'max_input_tokens': 128000, 'price_input': 1.00, 'price_output': 1.00},
            {'id': 'zhipuai/GLM-4.5-Air', 'name': 'GLM-4.5 Air (경량)', 'max_input_tokens': 128000, 'price_input': 0.10, 'price_output': 0.10},
        ]
    },
    'deepseek': {
        'name': 'DeepSeek',
        'models': [
            {'id': 'deepseek/deepseek-chat', 'name': 'DeepSeek Chat (V3)', 'max_input_tokens': 64000, 'price_input': 0.27, 'price_output': 1.10},
            {'id': 'deepseek/deepseek-reasoner', 'name': 'DeepSeek Reasoner (R1)', 'max_input_tokens': 64000, 'price_input': 0.55, 'price_output': 2.19},
        ]
    },
    'ollama': {
        'name': 'Ollama (로컬)',
        'api_base': os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434'),
        'models': [
            {'id': 'ollama_chat/llama3.2', 'name': 'Llama 3.2 (8B)', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
            {'id': 'ollama_chat/mistral', 'name': 'Mistral 7B', 'max_input_tokens': 32000, 'price_input': 0, 'price_output': 0},
            {'id': 'ollama_chat/gemma2', 'name': 'Gemma 2 (9B)', 'max_input_tokens': 8192, 'price_input': 0, 'price_output': 0},
        ]
    },
    'openrouter': {
        'name': 'OpenRouter (2600+ 모델)',
        'api_base': 'https://openrouter.ai/api/v1',
        'models': [
            {'id': 'openrouter/anthropic/claude-sonnet-4', 'name': 'Claude Sonnet 4 (Anthropic)', 'max_input_tokens': 200000, 'price_input': 3.00, 'price_output': 15.00},
            {'id': 'openrouter/google/gemini-2.5-flash', 'name': 'Gemini 2.5 Flash (Google)', 'max_input_tokens': 1048576, 'price_input': 0.15, 'price_output': 0.60},
            {'id': 'openrouter/meta-llama/llama-4-scout', 'name': 'Llama 4 Scout (Meta)', 'max_input_tokens': 131072, 'price_input': 0.08, 'price_output': 0.30},
            {'id': 'openrouter/mistralai/mistral-large-2', 'name': 'Mistral Large 2 (Mistral)', 'max_input_tokens': 131072, 'price_input': 2.00, 'price_output': 6.00},
        ]
    },
}


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """API 키가 설정된 프로바이더만 반환합니다.
    Ollama는 API 키 불필요 — OLLAMA_BASE_URL이 설정되어 있으면 활성화.
    """
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
    elif model_id.startswith('ollama_chat/') or model_id.startswith('ollama/'):
        return 'ollama'
    elif model_id.startswith('openrouter/'):
        return 'openrouter'
    return 'gemini'  # 기본값 (Gemini)


# === Styles & Modifiers ===

STYLE_OPTIONS: List[Tuple[str, str]] = [
    ('blog_seo', '🔍 블로그+SEO'),
    ('summary', '⚡ 요약'),
    ('tutorial', '📚 튜토리얼'),
    ('qna', '❓ Q&A'),
    ('app_ideas', '💡 앱 아이디어'),
    ('yozm_it', '💻 요즘IT'),
    ('brunch_essay', '✍️ 브런치'),
    ('naver_popular', '💚 네이버'),
    ('sns_post', '📱 SNS 포스트'),
    ('newsletter', '📧 뉴스레터'),
    ('show_notes', '🎙️ 쇼노트'),
    ('shorts_script', '🎬 Shorts 클립'),
    ('geo_seo', '🤖 GEO (AI검색)'),
    ('course', '🎓 AI 코스'),
]


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
    },
    'language': {
        'ko': '결과는 반드시 한국어로 작성해주세요.',
        'en': 'You MUST write the entire result in English.',
        'ja': '結果は必ず日本語で書いてください。'
    }
}


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


__all__ = [
    # API Keys
    'YOUTUBE_API_KEY',
    'PROVIDER_API_KEYS',
    'SUPADATA_API_KEY',

    # Webhook
    'WEBHOOK_URL',
    'WEBHOOK_ENABLED',

    # Token Limits
    'MAX_TRANSCRIPT_TOKENS',
    'MAX_COMMENTS_TOKENS',
    'MAX_CONTENT_TOKENS',

    # Short Content Bypass
    'SHORT_CONTENT_THRESHOLD',
    'SHORT_CONTENT_BYPASS_STYLES',

    # AI Cache
    'AI_CACHE_DB',
    'AI_CACHE_TTL_DAYS',
    'AI_CACHE_MAX_SIZE_MB',

    # Fallback Chain
    'FALLBACK_CHAIN',
    'MAX_FALLBACK_ATTEMPTS',

    # Style/Length Tuning
    'STYLE_TEMPERATURE',
    'LENGTH_MAX_TOKENS',

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

    # 웹 검색 보강
    'TAVILY_API_KEY',
    'WEB_SEARCH_ENABLED',
    'WEB_SEARCH_MAX_RESULTS',

    # RAG
    'RAG_ENABLED',
    'CHROMA_DB_PATH',
    'RAG_TOP_K',

    # GraphRAG
    'GRAPH_RAG_ENABLED',
    'GRAPH_STORE_PATH',
    'RERANKER_ENABLED',
    'RERANKER_TOP_K',

    # TTS
    'TTS_ENABLED',
    'TTS_BACKEND',
    'TTS_DEFAULT_VOICE',
    'TTS_MAX_CHARS',
]
