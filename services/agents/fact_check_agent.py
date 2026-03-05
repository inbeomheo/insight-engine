"""
팩트체크 에이전트 — 콘텐츠의 검증 가능한 주장을 추출하고 판정

LLM을 사용하여 콘텐츠에서 사실적 주장을 추출하고,
각 주장의 검증 가능성을 판정합니다.
"""
import json
import logging
import re

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

_FACT_CHECK_PROMPT = """다음 콘텐츠에서 검증 가능한 사실적 주장(팩트)을 추출하고 판정하세요.
의견이나 주관적 서술은 제외하고, 수치·날짜·인물·사건 등 객관적으로 확인 가능한 주장만 추출합니다.

[콘텐츠]
{content}

JSON 배열만 반환하세요 (설명 없이):
[
  {{
    "claim": "추출된 주장 원문",
    "category": "statistic" | "date" | "person" | "event" | "technical" | "other",
    "verifiable": true,
    "confidence": 0.8,
    "reasoning": "판정 근거 (한 줄)"
  }}
]

규칙:
- 최대 10개까지 추출
- confidence: 해당 주장이 사실일 가능성 (0~1)
- 검증 불가능한 주관적 의견은 verifiable: false
- 명확히 틀린 주장은 confidence 낮게"""


class FactCheckAgent(BaseAgent):
    """콘텐츠 팩트체크 에이전트."""

    @property
    def name(self) -> str:
        return 'fact_check'

    @property
    def role(self) -> str:
        return '콘텐츠 사실 검증'

    def execute(self, context: dict) -> dict:
        content = context.get('content', '')
        if not content:
            return {'agent': self.name, 'claims': [], 'summary': '검증할 콘텐츠 없음'}

        prompt = _FACT_CHECK_PROMPT.format(content=content[:3000])

        try:
            raw = self._call_ai(prompt, temperature=0.3, max_tokens=2000)
            claims = _parse_claims(raw)
        except Exception as e:
            logger.warning(f"팩트체크 실패: {e}")
            claims = []

        verified = sum(1 for c in claims if c.get('confidence', 0) >= 0.7)
        uncertain = sum(1 for c in claims if 0.3 <= c.get('confidence', 0) < 0.7)
        suspicious = sum(1 for c in claims if c.get('confidence', 0) < 0.3)

        return {
            'agent': self.name,
            'claims': claims,
            'summary': {
                'total': len(claims),
                'verified': verified,
                'uncertain': uncertain,
                'suspicious': suspicious,
            },
        }


def _parse_claims(raw: str) -> list:
    """LLM 응답에서 주장 목록을 파싱합니다."""
    if not raw:
        return []

    text = re.sub(r'```json\s*', '', raw)
    text = re.sub(r'```\s*', '', text).strip()

    # JSON 배열 추출
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return [_validate_claim(c) for c in parsed[:10] if isinstance(c, dict)]
        except json.JSONDecodeError:
            pass
    return []


def _validate_claim(claim: dict) -> dict:
    """주장 항목을 정규화합니다."""
    confidence = claim.get('confidence', 0.5)
    try:
        confidence = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0.5

    category = claim.get('category', 'other')
    if category not in ('statistic', 'date', 'person', 'event', 'technical', 'other'):
        category = 'other'

    return {
        'claim': str(claim.get('claim', ''))[:200],
        'category': category,
        'verifiable': bool(claim.get('verifiable', True)),
        'confidence': confidence,
        'reasoning': str(claim.get('reasoning', ''))[:200],
    }


def fact_check(content: str, model: str = None) -> dict:
    """콘텐츠를 팩트체크합니다 (편의 함수).

    Args:
        content: 검증할 텍스트
        model: AI 모델 ID (None이면 자동 선택)

    Returns:
        {"claims": list, "summary": dict}
    """
    agent = FactCheckAgent(model=model)
    result = agent.execute({'content': content})
    return {
        'claims': result['claims'],
        'summary': result['summary'],
    }
