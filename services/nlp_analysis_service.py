"""
NLP 분석 서비스 — LLM 기반 키워드/감성/토픽 분석

외부 NLP 라이브러리(spaCy, nltk 등) 없이 LiteLLM을 통해 분석.
비용 절감을 위해 경량 모델 우선 사용.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)

# 분석에 사용할 경량 모델 폴백 체인
_ANALYSIS_MODEL_CHAIN = [
    'zhipuai/GLM-4.5-Air',
    'zhipuai/GLM-4.7',
]

# NLP 분석 프롬프트 — 최소 토큰으로 정확한 JSON 반환 유도
_ANALYSIS_PROMPT = """다음 텍스트를 분석하여 JSON만 반환하세요. 설명 없이 JSON만.

분석 대상:
{content}

반환 형식 (반드시 유효한 JSON):
{{
  "keywords": [
    {{"word": "키워드1", "relevance": 0.95}},
    {{"word": "키워드2", "relevance": 0.80}}
  ],
  "sentiment": {{
    "overall": "positive",
    "score": 0.75,
    "aspects": [
      {{"aspect": "측면1", "sentiment": "positive", "score": 0.8}},
      {{"aspect": "측면2", "sentiment": "negative", "score": -0.3}}
    ]
  }},
  "topics": [
    {{"topic": "토픽1", "confidence": 0.9}},
    {{"topic": "토픽2", "confidence": 0.7}}
  ]
}}

규칙:
- keywords: 상위 10개, relevance는 0~1 사이
- sentiment.overall: "positive" | "neutral" | "negative" 중 하나
- sentiment.score: -1.0(매우 부정) ~ 1.0(매우 긍정)
- sentiment.aspects: 최대 5개 측면별 감성
- topics: 상위 5개 토픽, confidence는 0~1 사이
- 모든 텍스트는 한국어로"""

_EMPTY_ANALYSIS = {
    "keywords": [],
    "sentiment": {
        "overall": "neutral",
        "score": 0.0,
        "aspects": []
    },
    "topics": []
}


def _get_analysis_model() -> str:
    """분석에 사용할 모델을 반환합니다. API 키가 있는 첫 번째 모델 사용."""
    from config import PROVIDER_API_KEYS

    zhipu_key = PROVIDER_API_KEYS.get('zhipuai', '')
    if zhipu_key:
        return _ANALYSIS_MODEL_CHAIN[0]

    # Gemini 폴백
    gemini_key = PROVIDER_API_KEYS.get('gemini', '')
    if gemini_key:
        return 'gemini/gemini-2.5-flash-lite-preview-09-2025'

    # DeepSeek 폴백
    deepseek_key = PROVIDER_API_KEYS.get('deepseek', '')
    if deepseek_key:
        return 'deepseek/deepseek-chat'

    # Ollama 폴백 (무료)
    ollama_url = PROVIDER_API_KEYS.get('ollama', '')
    if ollama_url:
        return 'ollama_chat/llama3.2'

    return _ANALYSIS_MODEL_CHAIN[0]


def _call_llm_for_analysis(content: str, model: str) -> dict:
    """LLM을 호출하여 분석 결과 dict를 반환합니다.

    Args:
        content: 분석할 텍스트 (최대 3000자로 잘림)
        model: 사용할 LiteLLM 모델 ID

    Returns:
        dict: 분석 결과 (keywords, sentiment, topics)
    """
    from litellm import completion

    # 비용 절감: 최대 3000자만 분석
    truncated = content[:3000] if len(content) > 3000 else content
    prompt = _ANALYSIS_PROMPT.format(content=truncated)

    kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.3,
    }

    # Zhipu GLM OpenAI 호환 API 설정
    if model.startswith('zhipuai/'):
        from services.ai_service import ZHIPUAI_API_BASE
        kwargs["api_base"] = ZHIPUAI_API_BASE
        api_key = os.getenv('ZHIPUAI_API_KEY', '')
        if api_key:
            kwargs["api_key"] = api_key

    # Ollama: api_base 설정
    if model.startswith('ollama_chat/') or model.startswith('ollama/'):
        ollama_base = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        kwargs["api_base"] = ollama_base

    response = completion(**kwargs)
    raw = response.choices[0].message.content or ''
    return _parse_analysis_json(raw)


def _parse_analysis_json(raw: str) -> dict:
    """LLM 응답에서 JSON을 파싱합니다. 실패 시 빈 분석 결과 반환.

    Args:
        raw: LLM이 반환한 원본 텍스트

    Returns:
        dict: 파싱된 분석 결과 또는 빈 결과
    """
    if not raw:
        return dict(_EMPTY_ANALYSIS)

    # ```json ... ``` 코드블록 제거
    text = raw.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        # 첫 줄(```json)과 마지막 줄(```) 제거
        inner = '\n'.join(lines[1:-1]) if len(lines) > 2 else ''
        text = inner.strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # JSON 블록을 찾아서 파싱 시도
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                parsed = json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                logger.warning("NLP 분석 JSON 파싱 실패 — 빈 결과 반환")
                return dict(_EMPTY_ANALYSIS)
        else:
            logger.warning("NLP 분석 JSON을 찾을 수 없음 — 빈 결과 반환")
            return dict(_EMPTY_ANALYSIS)

    return _validate_analysis(parsed)


def _validate_analysis(data: dict) -> dict:
    """분석 결과 구조를 검증하고 정규화합니다."""
    result = {
        "keywords": [],
        "sentiment": {
            "overall": "neutral",
            "score": 0.0,
            "aspects": []
        },
        "topics": []
    }

    # keywords 검증
    raw_kw = data.get('keywords', [])
    if isinstance(raw_kw, list):
        for item in raw_kw[:10]:
            if isinstance(item, dict) and 'word' in item:
                result['keywords'].append({
                    'word': str(item['word'])[:50],
                    'relevance': float(item.get('relevance', 0.5))
                })

    # sentiment 검증
    raw_sent = data.get('sentiment', {})
    if isinstance(raw_sent, dict):
        overall = raw_sent.get('overall', 'neutral')
        if overall not in ('positive', 'neutral', 'negative'):
            overall = 'neutral'
        result['sentiment']['overall'] = overall

        score = raw_sent.get('score', 0.0)
        try:
            score = max(-1.0, min(1.0, float(score)))
        except (TypeError, ValueError):
            score = 0.0
        result['sentiment']['score'] = score

        raw_aspects = raw_sent.get('aspects', [])
        if isinstance(raw_aspects, list):
            for aspect in raw_aspects[:5]:
                if isinstance(aspect, dict) and 'aspect' in aspect:
                    asp_sent = aspect.get('sentiment', 'neutral')
                    if asp_sent not in ('positive', 'neutral', 'negative'):
                        asp_sent = 'neutral'
                    try:
                        asp_score = float(aspect.get('score', 0.0))
                    except (TypeError, ValueError):
                        asp_score = 0.0
                    result['sentiment']['aspects'].append({
                        'aspect': str(aspect['aspect'])[:50],
                        'sentiment': asp_sent,
                        'score': max(-1.0, min(1.0, asp_score))
                    })

    # topics 검증
    raw_topics = data.get('topics', [])
    if isinstance(raw_topics, list):
        for item in raw_topics[:5]:
            if isinstance(item, dict) and 'topic' in item:
                result['topics'].append({
                    'topic': str(item['topic'])[:50],
                    'confidence': float(item.get('confidence', 0.5))
                })

    return result


def analyze_content(content: str, model: str = None) -> dict:
    """생성된 콘텐츠를 LLM으로 분석합니다.

    Args:
        content: 분석할 텍스트 (생성된 마크다운 콘텐츠)
        model: 사용할 모델 ID (None이면 자동 선택)

    Returns:
        dict: {
            "keywords": [{"word": str, "relevance": float}, ...],
            "sentiment": {
                "overall": "positive"|"neutral"|"negative",
                "score": float (-1.0~1.0),
                "aspects": [{"aspect": str, "sentiment": str, "score": float}, ...]
            },
            "topics": [{"topic": str, "confidence": float}, ...]
        }
        실패 시 빈 분석 결과 반환 (예외 전파 안 함)
    """
    if not content or not content.strip():
        return dict(_EMPTY_ANALYSIS)

    if model is None:
        model = _get_analysis_model()

    try:
        return _call_llm_for_analysis(content, model)
    except Exception as e:
        logger.warning(f"NLP 분석 실패 (무시): {e}")
        return dict(_EMPTY_ANALYSIS)


# ─── 문단별 감정 흐름 분석 (F3-11) ──────────────────────────────────────────

_SENTIMENT_FLOW_PROMPT = """다음 텍스트를 문단별로 감정 흐름을 분석하세요.
각 문단의 감정 극성과 강도를 측정합니다.

[텍스트]
{content}

JSON만 반환하세요 (설명 없이):
{{
  "flow": [
    {{"paragraph_index": 0, "text_preview": "첫 20자...", "sentiment": "positive", "score": 0.7, "emotion": "기대"}},
    {{"paragraph_index": 1, "text_preview": "첫 20자...", "sentiment": "neutral", "score": 0.1, "emotion": "설명"}}
  ],
  "overall_arc": "ascending" | "descending" | "stable" | "fluctuating",
  "dominant_emotion": "기대" | "신뢰" | "분노" | "슬픔" | "놀람" | "공포" | "기쁨" | "설명"
}}

규칙:
- 각 문단(빈 줄로 구분)마다 하나의 항목
- sentiment: "positive" | "neutral" | "negative"
- score: -1.0(매우 부정) ~ 1.0(매우 긍정)
- emotion: 해당 문단의 주된 감정 (한국어)
- overall_arc: 전체 감정 흐름 방향"""


def analyze_sentiment_flow(content: str, model: str = None) -> dict:
    """문단별 감정 흐름을 분석합니다.

    Args:
        content: 분석할 텍스트
        model: 사용할 모델 ID (None이면 자동 선택)

    Returns:
        {
            "flow": [{"paragraph_index": int, "text_preview": str, "sentiment": str, "score": float, "emotion": str}],
            "overall_arc": str,
            "dominant_emotion": str,
        }
    """
    empty_flow = {'flow': [], 'overall_arc': 'stable', 'dominant_emotion': '설명'}

    if not content or not content.strip():
        return empty_flow

    if model is None:
        model = _get_analysis_model()

    # 최대 3000자
    truncated = content[:3000]
    prompt = _SENTIMENT_FLOW_PROMPT.format(content=truncated)

    try:
        from litellm import completion

        kwargs = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
            "temperature": 0.3,
        }

        if model.startswith('zhipuai/'):
            from services.ai_service import ZHIPUAI_API_BASE
            kwargs["api_base"] = ZHIPUAI_API_BASE
            api_key = os.getenv('ZHIPUAI_API_KEY', '')
            if api_key:
                kwargs["api_key"] = api_key

        if model.startswith('ollama_chat/') or model.startswith('ollama/'):
            kwargs["api_base"] = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

        response = completion(**kwargs)
        raw = response.choices[0].message.content or ''
        return _parse_sentiment_flow(raw)
    except Exception as e:
        logger.warning(f"감정 흐름 분석 실패 (무시): {e}")
        return empty_flow


def _parse_sentiment_flow(raw: str) -> dict:
    """감정 흐름 JSON을 파싱합니다."""
    empty = {'flow': [], 'overall_arc': 'stable', 'dominant_emotion': '설명'}

    if not raw:
        return empty

    import json as json_mod

    text = raw.strip()
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else ''
        text = text.strip()

    try:
        parsed = json_mod.loads(text)
    except json_mod.JSONDecodeError:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                parsed = json_mod.loads(text[start:end + 1])
            except json_mod.JSONDecodeError:
                return empty
        else:
            return empty

    # 검증
    flow = parsed.get('flow', [])
    if not isinstance(flow, list):
        flow = []

    validated_flow = []
    for item in flow[:30]:  # 최대 30 문단
        if not isinstance(item, dict):
            continue
        sentiment = item.get('sentiment', 'neutral')
        if sentiment not in ('positive', 'neutral', 'negative'):
            sentiment = 'neutral'
        try:
            score = max(-1.0, min(1.0, float(item.get('score', 0.0))))
        except (TypeError, ValueError):
            score = 0.0

        validated_flow.append({
            'paragraph_index': int(item.get('paragraph_index', len(validated_flow))),
            'text_preview': str(item.get('text_preview', ''))[:50],
            'sentiment': sentiment,
            'score': score,
            'emotion': str(item.get('emotion', ''))[:20],
        })

    arc = parsed.get('overall_arc', 'stable')
    if arc not in ('ascending', 'descending', 'stable', 'fluctuating'):
        arc = 'stable'

    return {
        'flow': validated_flow,
        'overall_arc': arc,
        'dominant_emotion': str(parsed.get('dominant_emotion', '설명'))[:20],
    }
