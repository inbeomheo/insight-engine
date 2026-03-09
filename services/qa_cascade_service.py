"""Q&A 캐스케이드 서비스 — 자막에서 예상 질문/답변 쌍 자동 생성

자막 텍스트를 분석하여 직원/시청자가 할 수 있는 예상 질문과
관리자/전문가 관점의 답변 쌍을 생성합니다.
카테고리별(process/policy/technical/general) 분류 + 신뢰도 점수 포함.
"""
import json
import logging
import re
from dataclasses import dataclass, asdict
from typing import List

logger = logging.getLogger(__name__)

# Q&A 생성에 사용할 프롬프트
_QA_CASCADE_PROMPT = """다음 자막(transcript)을 읽고, 직원/시청자가 할 수 있는 예상 질문과
관리자/전문가 관점의 답변 쌍을 5개 이상 생성하세요.

[자막]
{transcript}

JSON만 반환하세요 (설명 없이):
{{
  "qa_pairs": [
    {{
      "question": "예상 질문",
      "answer": "전문가 답변",
      "category": "process",
      "confidence": 0.9
    }}
  ]
}}

규칙:
- category: "process"(절차/방법) | "policy"(정책/규정) | "technical"(기술적) | "general"(일반)
- confidence: 0.0~1.0 (자막 내용에 근거가 명확할수록 높음)
- 자막에 있는 정보만 사용 (창작/추측 금지)
- 질문은 구체적이고 실용적으로
- 답변은 자막 내용 기반으로 정확하게
- 최소 5개, 최대 15개"""

# 유효한 카테고리 목록
_VALID_CATEGORIES = {"process", "policy", "technical", "general"}


@dataclass
class QaPair:
    """질문-답변 쌍"""
    question: str
    answer: str
    category: str       # "process" | "policy" | "technical" | "general"
    confidence: float   # 0.0~1.0


def generate_qa_cascade(transcript: str) -> List[QaPair]:
    """자막에서 직원 예상 질문 + 관리자 답변 쌍 생성 (5개+)

    Args:
        transcript: 자막 텍스트

    Returns:
        QaPair 리스트 (최소 5개 목표, AI 응답에 따라 달라질 수 있음)

    Raises:
        ValueError: 자막이 비어있을 때
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막 텍스트가 비어있습니다")

    # 너무 짧은 자막은 의미 있는 Q&A 생성 불가
    stripped = transcript.strip()
    if len(stripped) < 30:
        raise ValueError("자막이 너무 짧아 Q&A를 생성할 수 없습니다 (최소 30자)")

    model = _get_model()

    try:
        raw_text = _call_llm(stripped, model)
        return _parse_qa_response(raw_text)
    except ValueError:
        raise
    except Exception as e:
        logger.error("Q&A 캐스케이드 생성 실패: %s", e)
        return []


def _get_model() -> str:
    """사용 가능한 AI 모델을 반환합니다."""
    try:
        from config import PROVIDER_API_KEYS
        if PROVIDER_API_KEYS.get('gemini'):
            return 'gemini/gemini-3-flash-preview'
        if PROVIDER_API_KEYS.get('zhipuai'):
            return 'zhipuai/GLM-4.5-Air'
        if PROVIDER_API_KEYS.get('deepseek'):
            return 'deepseek/deepseek-chat'
    except ImportError:
        pass
    return 'gemini/gemini-3-flash-preview'


def _call_llm(transcript: str, model: str) -> str:
    """LLM을 호출하여 Q&A JSON 텍스트를 반환합니다."""
    from services.ai_service import create_content

    # 비용 절감: 최대 5000자
    truncated = transcript[:5000]
    prompt = _QA_CASCADE_PROMPT.format(transcript=truncated)

    result = create_content(
        content=truncated,
        model=model,
        style_prompt=prompt,
        style_id='summary'
    )
    return result.get('content', '')


def _parse_qa_response(raw: str) -> List[QaPair]:
    """LLM 응답에서 Q&A 쌍 리스트를 파싱합니다."""
    if not raw or not raw.strip():
        return []

    text = raw.strip()

    # ```json ... ``` 코드블록 제거
    if text.startswith('```'):
        lines = text.split('\n')
        text = '\n'.join(lines[1:-1]) if len(lines) > 2 else ''
        text = text.strip()

    # JSON 파싱 시도
    parsed = None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # { } 블록 추출
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                parsed = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("Q&A JSON 파싱 실패")
                return []

    if not parsed or not isinstance(parsed, dict):
        return []

    raw_pairs = parsed.get('qa_pairs', [])
    if not isinstance(raw_pairs, list):
        return []

    # 검증 및 QaPair 변환
    results = []
    for item in raw_pairs[:15]:  # 최대 15개
        if not isinstance(item, dict):
            continue

        question = item.get('question', '')
        answer = item.get('answer', '')
        if not question or not answer:
            continue

        category = item.get('category', 'general')
        if category not in _VALID_CATEGORIES:
            category = 'general'

        try:
            confidence = max(0.0, min(1.0, float(item.get('confidence', 0.5))))
        except (TypeError, ValueError):
            confidence = 0.5

        results.append(QaPair(
            question=str(question).strip(),
            answer=str(answer).strip(),
            category=category,
            confidence=confidence,
        ))

    return results


def qa_pairs_to_dicts(pairs: List[QaPair]) -> List[dict]:
    """QaPair 리스트를 직렬화 가능한 dict 리스트로 변환합니다."""
    return [asdict(p) for p in pairs]
