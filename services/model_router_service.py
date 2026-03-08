"""
AI 모델 라우터 서비스 (F10-26)
요청 특성(복잡도, 스타일, 예산, 레이턴시)에 따라 최적 모델 자동 선택
"""
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ModelSpec:
    """모델 사양"""
    provider: str
    model_id: str
    context_window: int       # 최대 컨텍스트 토큰
    avg_latency_s: float      # 평균 레이턴시 (초)
    cost_per_1k_input: float  # 입력 1K 토큰당 비용 ($)
    cost_per_1k_output: float # 출력 1K 토큰당 비용 ($)
    quality_score: float      # 품질 점수 (0~1, 주관적)
    supports_streaming: bool = True
    suitable_styles: Optional[List[str]] = None  # None이면 모든 스타일


# 지원 모델 스펙 테이블
MODEL_CATALOG: Dict[str, ModelSpec] = {
    'gemini/gemini-2.5-flash-lite-preview-09-2025': ModelSpec(
        provider='gemini', model_id='gemini-2.5-flash-lite-preview-09-2025',
        context_window=1_000_000, avg_latency_s=3.0,
        cost_per_1k_input=0.000075, cost_per_1k_output=0.0003,
        quality_score=0.80,
        suitable_styles=['summary', 'qna', 'show_notes', 'sns_post'],
    ),
    'gemini/gemini-3-flash-preview': ModelSpec(
        provider='gemini', model_id='gemini-3-flash-preview',
        context_window=1_000_000, avg_latency_s=5.0,
        cost_per_1k_input=0.00015, cost_per_1k_output=0.0006,
        quality_score=0.90,
    ),
    'deepseek/deepseek-chat': ModelSpec(
        provider='deepseek', model_id='deepseek-chat',
        context_window=128_000, avg_latency_s=4.0,
        cost_per_1k_input=0.00014, cost_per_1k_output=0.00028,
        quality_score=0.85,
        suitable_styles=['tutorial', 'blog_seo', 'newsletter'],
    ),
    'deepseek/deepseek-reasoner': ModelSpec(
        provider='deepseek', model_id='deepseek-reasoner',
        context_window=128_000, avg_latency_s=15.0,
        cost_per_1k_input=0.00055, cost_per_1k_output=0.00219,
        quality_score=0.92,
        suitable_styles=['qna', 'tutorial', 'course'],
    ),
    'zhipuai/GLM-4.5-Air': ModelSpec(
        provider='zhipuai', model_id='GLM-4.5-Air',
        context_window=128_000, avg_latency_s=3.5,
        cost_per_1k_input=0.0001, cost_per_1k_output=0.0001,
        quality_score=0.78,
    ),
}


@dataclass
class RouterDecision:
    """라우팅 결정 결과"""
    model_key: str
    reason: str
    estimated_cost: float
    estimated_latency_s: float
    fallback_models: List[str]


class ModelRouter:
    """
    AI 모델 자동 라우터

    선택 기준 (우선순위):
    1. 사용 가능한 API 키 필터링
    2. 스타일 적합성 (suitable_styles)
    3. 컨텍스트 길이 충족 여부
    4. 사용자 설정 (budget_mode / quality_mode)
    5. 예상 비용 / 레이턴시 균형
    """

    def __init__(self):
        self._available_models = self._detect_available_models()
        logger.info("ModelRouter 초기화: 사용 가능 모델 %d개", len(self._available_models))

    def _detect_available_models(self) -> List[str]:
        """API 키가 설정된 모델만 필터링"""
        api_keys = {
            'gemini': os.getenv('GEMINI_API_KEY', ''),
            'deepseek': os.getenv('DEEPSEEK_API_KEY', ''),
            'zhipuai': os.getenv('ZHIPUAI_API_KEY', ''),
            'openai': os.getenv('OPENAI_API_KEY', ''),
        }
        available = []
        for key, spec in MODEL_CATALOG.items():
            if api_keys.get(spec.provider) or spec.provider == 'ollama':
                available.append(key)
        return available

    def _filter_candidates(self, style_id: str, transcript_length: int) -> List[str]:
        """컨텍스트 윈도우와 스타일 적합성으로 후보 모델을 필터링합니다."""
        candidates = [
            k for k in self._available_models
            if MODEL_CATALOG[k].context_window >= transcript_length + 2000
        ]

        if not candidates:
            candidates = sorted(
                self._available_models,
                key=lambda k: MODEL_CATALOG[k].context_window,
                reverse=True
            )[:1]

        style_preferred = [
            k for k in candidates
            if MODEL_CATALOG[k].suitable_styles is None
            or style_id in (MODEL_CATALOG[k].suitable_styles or [])
        ]
        return style_preferred if style_preferred else candidates

    def _sort_by_mode(self, candidates: List[str], mode: str) -> None:
        """라우팅 모드에 따라 후보를 정렬합니다 (in-place)."""
        if mode == 'budget':
            candidates.sort(key=lambda k: MODEL_CATALOG[k].cost_per_1k_output)
        elif mode == 'quality':
            candidates.sort(key=lambda k: MODEL_CATALOG[k].quality_score, reverse=True)
        elif mode == 'fast':
            candidates.sort(key=lambda k: MODEL_CATALOG[k].avg_latency_s)
        else:  # balanced
            candidates.sort(
                key=lambda k: (
                    -MODEL_CATALOG[k].quality_score * 0.6
                    + MODEL_CATALOG[k].cost_per_1k_output * 1000 * 0.2
                    + MODEL_CATALOG[k].avg_latency_s / 60 * 0.2
                )
            )

    def route(
        self,
        style_id: str,
        transcript_length: int = 0,
        mode: str = 'balanced',
        user_model_preference: Optional[str] = None,
    ) -> RouterDecision:
        """최적 모델을 선택합니다.

        Args:
            style_id: 콘텐츠 스타일
            transcript_length: 자막 토큰 수 (컨텍스트 제한 확인용)
            mode: 라우팅 모드 ('budget', 'quality', 'balanced', 'fast')
            user_model_preference: 사용자가 명시적으로 지정한 모델

        Returns:
            RouterDecision
        """
        if user_model_preference and user_model_preference in self._available_models:
            spec = MODEL_CATALOG[user_model_preference]
            return RouterDecision(
                model_key=user_model_preference,
                reason="사용자 지정 모델",
                estimated_cost=self._estimate_cost(spec, transcript_length),
                estimated_latency_s=spec.avg_latency_s,
                fallback_models=self._get_fallbacks(user_model_preference),
            )

        candidates = self._filter_candidates(style_id, transcript_length)
        self._sort_by_mode(candidates, mode)

        selected = candidates[0]
        spec = MODEL_CATALOG[selected]

        return RouterDecision(
            model_key=selected,
            reason=f"mode={mode}, style={style_id}",
            estimated_cost=self._estimate_cost(spec, transcript_length),
            estimated_latency_s=spec.avg_latency_s,
            fallback_models=self._get_fallbacks(selected),
        )

    def _estimate_cost(self, spec: ModelSpec, transcript_tokens: int) -> float:
        """예상 비용 계산 ($)"""
        input_cost = (transcript_tokens / 1000) * spec.cost_per_1k_input
        output_tokens = 2000  # 평균 출력 예상
        output_cost = (output_tokens / 1000) * spec.cost_per_1k_output
        return round(input_cost + output_cost, 6)

    def _get_fallbacks(self, primary: str) -> List[str]:
        """폴백 모델 목록 (primary 제외)"""
        return [k for k in self._available_models if k != primary][:2]

    def get_available_models(self) -> List[Dict]:
        """사용 가능한 모델 목록 반환"""
        result = []
        for key in self._available_models:
            spec = MODEL_CATALOG[key]
            result.append({
                'model_key': key,
                'provider': spec.provider,
                'context_window': spec.context_window,
                'avg_latency_s': spec.avg_latency_s,
                'quality_score': spec.quality_score,
            })
        return result


# 싱글톤
_router: Optional[ModelRouter] = None


def get_model_router() -> ModelRouter:
    """ModelRouter 싱글톤 인스턴스 반환"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
