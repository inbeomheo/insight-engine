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
import functools
import os
import time

# prompts 패키지에서 가져오기
from prompts import (
    STYLE_PROMPTS,
    MODIFIERS,
    MODIFIER_OPTIONS,
    DEFAULT_MODIFIERS,
    build_full_prompt,
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
    'chatmock': os.getenv('CHATMOCK_API_KEY', 'dummy'),
}

SUPADATA_API_KEY: str = os.getenv('SUPADATA_API_KEY', '')

# === 웹 검색 보강 (Grounded Generation) ===

TAVILY_API_KEY: str = os.getenv('TAVILY_API_KEY', '')
WEB_SEARCH_ENABLED: bool = os.getenv('WEB_SEARCH_ENABLED', 'false').lower() == 'true'
WEB_SEARCH_MAX_RESULTS: int = int(os.getenv('WEB_SEARCH_MAX_RESULTS', '5'))

# === 외부 소스 연동 ===

NOTION_API_KEY: str = os.getenv('NOTION_API_KEY', '')

# === RAG (지식 참조) ===

RAG_ENABLED: bool = os.environ.get('RAG_ENABLED', 'false').lower() == 'true'
CHROMA_DB_PATH: str = os.environ.get('CHROMA_DB_PATH', './data/chroma_db')
RAG_TOP_K: int = int(os.environ.get('RAG_TOP_K', '5'))

# === GraphRAG (지식 그래프 + 리랭킹) ===

GRAPH_RAG_ENABLED: bool = os.environ.get('GRAPH_RAG_ENABLED', 'false').lower() == 'true'
GRAPH_STORE_PATH: str = os.environ.get('GRAPH_STORE_PATH', './data/graph_store')
RERANKER_ENABLED: bool = os.environ.get('RERANKER_ENABLED', 'false').lower() == 'true'
RERANKER_TOP_K: int = int(os.environ.get('RERANKER_TOP_K', '5'))

# === Corrective RAG (CRAG) ===
# 주의: 품질 미달 시 LLM 추가 호출 발생 (비용 +1~2회/요청)

CRAG_ENABLED: bool = os.environ.get('CRAG_ENABLED', 'false').lower() == 'true'
CRAG_QUALITY_THRESHOLD: float = float(os.environ.get('CRAG_QUALITY_THRESHOLD', '0.7'))

# === 에이전트 모드 ===

AGENT_MODE_ENABLED: bool = os.getenv('AGENT_MODE_ENABLED', 'false').lower() == 'true'
AGENT_MAX_ITERATIONS: int = int(os.getenv('AGENT_MAX_ITERATIONS', '5'))
AGENT_DEFAULT_MODEL: str = os.getenv('AGENT_DEFAULT_MODEL', 'gemini/gemini-3.1-flash-lite-preview')

# === Whisper (음성 인식 자막 폴백) ===

WHISPER_ENABLED: bool = os.getenv('WHISPER_ENABLED', 'false').lower() == 'true'
WHISPER_MODEL_SIZE: str = os.getenv('WHISPER_MODEL_SIZE', 'base')

# === TTS (텍스트 → 오디오 변환) ===

TTS_ENABLED: bool = os.getenv('TTS_ENABLED', 'false').lower() == 'true'
TTS_BACKEND: str = os.getenv('TTS_BACKEND', 'auto')   # 'openai', 'edge', 'auto'
TTS_DEFAULT_VOICE: str = os.getenv('TTS_DEFAULT_VOICE', 'alloy')
TTS_MAX_CHARS: int = 5000

# === 이미지 생성 ===

IMAGE_GEN_PROVIDER: str = os.getenv('IMAGE_GEN_PROVIDER', 'openai')
IMAGE_GEN_API_KEY: str = os.getenv('IMAGE_GEN_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')

# === Stripe 결제 ===

STRIPE_SECRET_KEY: str = os.getenv('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET: str = os.getenv('STRIPE_WEBHOOK_SECRET', '')

# === 화이트라벨 (F4-15) ===

WHITELABEL_ENABLED: bool = os.getenv('WHITELABEL_ENABLED', 'false').lower() == 'true'
WHITELABEL_CONFIG: Dict[str, str] = {
    'default_app_name': os.getenv('WHITELABEL_APP_NAME', 'Insight Engine'),
    'default_primary_color': os.getenv('WHITELABEL_PRIMARY_COLOR', '#6366f1'),
}

# === 플랜별 기능 제한 (F4-18) ===

PLAN_FEATURES: Dict[str, List[str]] = {
    'free': ['generate', 'history', 'export_markdown'],
    'starter': ['generate', 'history', 'export_markdown', 'export_docx', 'multi_style', 'custom_style', 'rag'],
    'pro': ['generate', 'history', 'export_markdown', 'export_docx', 'export_pdf',
            'multi_style', 'custom_style', 'rag', 'pipeline', 'tts', 'image_gen', 'whitelabel', 'api_access'],
    'enterprise': ['generate', 'history', 'export_markdown', 'export_docx', 'export_pdf',
                   'multi_style', 'custom_style', 'rag', 'pipeline', 'tts', 'image_gen', 'whitelabel',
                   'api_access', 'sso', 'audit_log', 'team_billing', 'custom_model'],
}

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
    'summary': 0.35, 'tutorial': 0.5, 'qna': 0.35, 'show_notes': 0.45, 'geo_seo': 0.4, 'course': 0.5, 'quiz': 0.5,
    'blog_seo': 0.7, 'yozm_it': 0.7, 'app_ideas': 0.7, 'newsletter': 0.7, 'shorts_script': 0.7,
    'brunch_essay': 0.85, 'naver_popular': 0.85, 'sns_post': 0.8,
    'comment_summary': 0.35,
    # 엄격한 출력 형식이 필요한 변환계 — 창의성보다 형식 준수 우선
    'mindmap': 0.3, 'cited_summary': 0.4, 'chapter_split': 0.3, 'knowledge_note': 0.4,
}

# 길이별 max_tokens (한국어 2~3토큰/자 + 마크다운 오버헤드 ~40% 감안)
LENGTH_MAX_TOKENS: Dict[str, int] = {
    'short': 2000, 'medium': 8000, 'long': 16000,
}

# 요약 상세도 프리셋 (brief/standard/deep)
DETAIL_PRESETS: Dict[str, Dict[str, Any]] = {
    'brief': {
        'temperature_offset': -0.1,
        'max_tokens_multiplier': 0.5,
        'prompt_suffix': '핵심 내용만 간결하게 3-5개 포인트로 요약하세요. 부연 설명은 최소화하세요.',
    },
    'standard': {
        'temperature_offset': 0.0,
        'max_tokens_multiplier': 1.0,
        'prompt_suffix': '',
    },
    'deep': {
        'temperature_offset': 0.1,
        'max_tokens_multiplier': 2.0,
        'prompt_suffix': '가능한 한 상세하게 작성하세요. 각 포인트에 대해 배경 설명, 구체적 예시, 관련 맥락을 풍부하게 포함하세요.',
    },
}

# === QA 게이트 (발행 전 품질 검증) ===

QA_FORBIDDEN_WORDS: List[str] = [
    '놀라운', '혁신적', '획기적', '최고의', '게임체인저',
    '압도적', '경이로운', '드디어', '탁월한', '인상적', '뛰어난', '강력한',
]

QA_MIN_SECTIONS: int = 2
QA_MIN_CHARS: int = 200

# === Providers ===

SUPPORTED_PROVIDERS: Dict[str, Dict[str, Any]] = {
    'gemini': {
        'name': 'Google Gemini',
        'models': [
            {'id': 'gemini/gemini-3.1-flash-lite-preview', 'name': 'Gemini 3.1 Flash Lite (최신)', 'max_input_tokens': 1048576, 'price_input': 0.075, 'price_output': 0.30},
        ]
    },
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
    'chatmock': {
        'name': 'ChatMock',
        'api_base': os.getenv('CHATMOCK_BASE_URL', 'http://127.0.0.1:8000/v1'),
        'models': [
            {'id': 'chatmock/gpt-5.4', 'name': 'GPT-5.4', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
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


_providers_cache: Dict[str, Any] = {}
_providers_cache_time: float = 0.0
_PROVIDERS_CACHE_TTL: float = 60.0  # 60초 TTL


def get_available_providers() -> Dict[str, Dict[str, Any]]:
    """API 키가 설정된 프로바이더만 반환합니다.
    Ollama는 API 키 불필요 — OLLAMA_BASE_URL이 설정되어 있으면 활성화.
    결과를 60초간 캐싱합니다.
    """
    global _providers_cache, _providers_cache_time
    now = time.time()
    if _providers_cache and (now - _providers_cache_time) < _PROVIDERS_CACHE_TTL:
        return _providers_cache

    available = {}
    for provider_id, api_key in PROVIDER_API_KEYS.items():
        if api_key and provider_id in SUPPORTED_PROVIDERS:
            available[provider_id] = SUPPORTED_PROVIDERS[provider_id]

    _providers_cache = available
    _providers_cache_time = now
    return available


@functools.lru_cache(maxsize=128)
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
    elif model_id.startswith('chatmock/'):
        return 'chatmock'
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
    ('shorts_script', '🎬 쇼츠 클립'),
    ('geo_seo', '🤖 GEO (AI검색)'),
    ('course', '🎓 AI 코스'),
    ('quiz', '🧠 퀴즈'),
]


# 모디파이어 지시문 — prompts/modifiers.py가 단일 소스 (v4에서 이중화 제거)
STYLE_MODIFIERS: Dict[str, Dict[str, str]] = MODIFIERS


@functools.lru_cache(maxsize=128)
def get_model_max_tokens(model_id: str) -> int:
    """모델 ID로 최대 입력 토큰 수를 반환합니다."""
    for provider in SUPPORTED_PROVIDERS.values():
        for model in provider.get('models', []):
            if model['id'] == model_id:
                return model.get('max_input_tokens', MAX_CONTENT_TOKENS)
    return MAX_CONTENT_TOKENS  # fallback


def get_model_display_name(model_id: str) -> str:
    """모델 ID로 사용자 표시용 이름을 반환합니다.

    예: 'zhipuai/GLM-4.5-Air' → 'GLM-4.5 Air (경량)'
    매칭 실패 시 모델 ID를 그대로 반환합니다.
    """
    for provider in SUPPORTED_PROVIDERS.values():
        for model in provider.get('models', []):
            if model['id'] == model_id:
                return model.get('name', model_id)
    return model_id


# === Phase 9: 인프라 & 성능 설정 ===

# Redis 캐싱 (옵셔널)
REDIS_URL: str = os.getenv('REDIS_URL', '')
REDIS_TTL_SECONDS: int = int(os.getenv('REDIS_TTL_SECONDS', '3600'))

# 암호화
ENCRYPTION_KEY: str = os.getenv('ENCRYPTION_KEY', '')

# Sentry 오류 추적
SENTRY_DSN: str = os.getenv('SENTRY_DSN', '')

# 환경별 설정
class Config:
    """기본 설정"""
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    LOG_LEVEL = 'INFO'
    PREFERRED_URL_SCHEME = 'https'

class TestingConfig(Config):
    TESTING = True
    LOG_LEVEL = 'WARNING'

ENV_CONFIGS = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

ACTIVE_CONFIG = ENV_CONFIGS.get(
    os.getenv('FLASK_ENV', 'development'), DevelopmentConfig
)

# === Phase 10: 고급 AI 설정 ===

# ElevenLabs 음성 복제
ELEVENLABS_API_KEY: str = os.getenv('ELEVENLABS_API_KEY', '')

# 비디오 생성
RUNWAY_API_KEY: str = os.getenv('RUNWAY_API_KEY', '')

# 번역
DEEPL_API_KEY: str = os.getenv('DEEPL_API_KEY', '')
TRANSLATION_MODEL: str = os.getenv(
    'TRANSLATION_MODEL',
    'gemini/gemini-2.5-flash-lite-preview-09-2025'
)

# 임베딩 모델 (RAG)
EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'text-embedding-3-small')

# 파인튜닝
FINETUNE_OUTPUT_DIR: str = os.getenv('FINETUNE_OUTPUT_DIR', './data/finetune')
FINETUNE_MIN_QUALITY_SCORE: float = float(os.getenv('FINETUNE_MIN_QUALITY_SCORE', '0.6'))

# 모델 라우터 기본 모드
MODEL_ROUTER_DEFAULT_MODE: str = os.getenv('MODEL_ROUTER_DEFAULT_MODE', 'balanced')


# === Public API (모든 정의 후 배치 — NameError 방지) ===

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
    'DETAIL_PRESETS',

    # QA Gate
    'QA_FORBIDDEN_WORDS',
    'QA_MIN_SECTIONS',
    'QA_MIN_CHARS',

    # Providers
    'SUPPORTED_PROVIDERS',
    'get_available_providers',
    'get_provider_from_model',
    'get_model_max_tokens',

    # Styles (v3.0)
    'STYLE_OPTIONS',
    'STYLE_PROMPTS',

    # Modifiers (v3.0)
    'STYLE_MODIFIERS',
    'MODIFIER_OPTIONS',
    'DEFAULT_MODIFIERS',

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

    # Phase 9: 인프라 & 성능
    'REDIS_URL',
    'ENCRYPTION_KEY',
    'SENTRY_DSN',

    # Phase 10: 고급 AI & 미래 기술
    'ELEVENLABS_API_KEY',
    'RUNWAY_API_KEY',
    'DEEPL_API_KEY',
    'TRANSLATION_MODEL',
    'FINETUNE_OUTPUT_DIR',
    'EMBEDDING_MODEL',
]
