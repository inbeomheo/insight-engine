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
        model: 사용할 AI 모델 ID (예: 'chatmock/gpt-5.4-mini').
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

        config.py의 AGENT_DEFAULT_MODEL을 사용합니다.
        """
        try:
            from config import AGENT_DEFAULT_MODEL
            return AGENT_DEFAULT_MODEL
        except Exception:
            pass
        return 'chatmock/gpt-5.4-mini'

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
        from litellm import completion

        model = self.model or self._get_default_model()

        kwargs: dict[str, Any] = {
            'model': model,
            'messages': [{'role': 'user', 'content': prompt}],
            'temperature': temperature,
            'max_tokens': max_tokens,
            'timeout': 180,
        }

        if model.startswith('chatmock/') or model.startswith('gpt-'):
            kwargs['model'] = model.replace('chatmock/', '', 1)
            kwargs['api_base'] = os.getenv('CHATMOCK_BASE_URL', 'http://127.0.0.1:8000/v1')
            kwargs['api_key'] = os.getenv('CHATMOCK_API_KEY', 'dummy') or 'dummy'
            kwargs['reasoning_effort'] = 'medium'
            kwargs['drop_params'] = True
            kwargs.pop('temperature', None)

        try:
            resp = completion(**kwargs)

            return resp.choices[0].message.content or ''
        except Exception as e:
            self._logger.error(f"[{self.name}] AI 호출 실패: {e}")
            raise
