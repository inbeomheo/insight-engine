"""
멀티에이전트 파이프라인의 기반 추상 클래스

모든 전문 에이전트(Research, Writer, Editor, SEO)가 이 클래스를 상속.
Flask는 동기 방식이므로 execute()는 동기 메서드로 구현.
"""
from abc import ABC, abstractmethod
from typing import Any
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """모든 에이전트의 기반 추상 클래스.

    Args:
        model: 사용할 AI 모델 ID (예: 'gemini/gemini-3-flash-preview').
               None이면 기본 모델 자동 선택.
    """

    def __init__(self, model: str = None):
        self.model = model
        self._logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def execute(self, context: dict) -> dict:
        """에이전트를 실행합니다.

        Args:
            context: 이전 에이전트 결과와 공통 입력이 담긴 딕셔너리.
                     최소한 다음 키를 포함해야 합니다:
                     - 'transcript': YouTube 자막 텍스트 (str)
                     - 'style': 콘텐츠 스타일 ID (str)

        Returns:
            처리 결과가 담긴 딕셔너리. 에이전트마다 다른 키 포함.
            반드시 'agent' (에이전트 이름) 키를 포함해야 합니다.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """에이전트 고유 이름 (예: 'research', 'writer')."""

    @property
    @abstractmethod
    def role(self) -> str:
        """에이전트 역할 설명 (한국어)."""

    def _get_default_model(self) -> str:
        """설정된 모델이 없을 때 사용 가능한 기본 모델을 반환합니다.

        config.py의 PROVIDER_API_KEYS를 확인하여 사용 가능한 모델 선택.
        """
        try:
            from config import PROVIDER_API_KEYS
            # 우선순위: Gemini → DeepSeek → Zhipu
            candidates = [
                ('gemini', 'gemini/gemini-3-flash-preview'),
                ('deepseek', 'deepseek/deepseek-chat'),
                ('zhipuai', 'zhipuai/GLM-4.5-Air'),
            ]
            for provider, model_id in candidates:
                if PROVIDER_API_KEYS.get(provider):
                    return model_id
        except Exception:
            pass
        return 'gemini/gemini-3-flash-preview'

    def _call_ai(self, prompt: str, temperature: float = 0.7, max_tokens: int = 4000) -> str:
        """AI 모델을 호출하여 응답을 반환하는 헬퍼.

        Args:
            prompt: 프롬프트 문자열
            temperature: 생성 temperature (0.0 ~ 1.0)
            max_tokens: 최대 출력 토큰 수

        Returns:
            AI 응답 텍스트. 오류 발생 시 빈 문자열 반환.
        """
        import os
        import threading
        from litellm import completion

        model = self.model or self._get_default_model()

        # GLM 모델 → OpenAI 호환 변환
        ZHIPUAI_API_BASE = 'https://open.bigmodel.cn/api/paas/v4/'
        _glm_lock_attr = '_glm_lock'
        if not hasattr(BaseAgent, '_glm_lock'):
            BaseAgent._glm_lock = threading.Lock()

        kwargs: dict[str, Any] = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'timeout': 180,
        }

        if model.startswith('zhipuai/'):
            zhipuai_key = os.getenv('ZHIPUAI_API_KEY')
            if not zhipuai_key:
                raise ValueError('ZHIPUAI_API_KEY 환경변수가 설정되지 않았습니다.')
            kwargs['model'] = f"openai/{model.replace('zhipuai/', '')}"
            kwargs['api_base'] = ZHIPUAI_API_BASE
            kwargs['api_key'] = zhipuai_key

        elif model.startswith('gemini/') and 'lite' not in model.lower():
            kwargs['reasoning_effort'] = 'minimal'

        elif model.startswith('ollama_chat/') or model.startswith('ollama/'):
            kwargs['api_base'] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

        try:
            if model.startswith('zhipuai/') or 'zhipuai' in kwargs.get('model', ''):
                # GLM은 순차 처리
                with BaseAgent._glm_lock:
                    resp = completion(**kwargs)
            else:
                resp = completion(**kwargs)

            return resp.choices[0].message.content or ''
        except Exception as e:
            self._logger.error(f"[{self.name}] AI 호출 실패: {e}")
            raise
