"""
지식 그래프 빌더 — 텍스트에서 엔티티와 관계를 추출하여 그래프를 구성
LiteLLM을 통해 LLM 기반 추출 수행 (JSON 구조화 출력)
"""
import json
import logging
import re
from typing import Any, Callable, Optional

import litellm

from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

# 기본 추출 모델 (ChatMock/OpenAI 호환)
_DEFAULT_MODEL = "chatmock/gpt-5.4-mini"

_ENTITY_RELATION_PROMPT = """다음 텍스트에서 주요 엔티티와 관계를 추출하세요.

**엔티티 타입**: person(인물), organization(기관/기업), technology(기술), concept(개념), product(제품/서비스), location(장소)

**출력 형식 (JSON만 출력, 다른 텍스트 없음)**:
{{
  "entities": [
    {{"name": "엔티티명", "type": "타입", "description": "한 줄 설명"}}
  ],
  "relations": [
    {{"source": "소스엔티티명", "target": "타겟엔티티명", "relation": "관계설명", "weight": 0.8}}
  ]
}}

**규칙**:
- 엔티티는 최대 15개 추출
- 관계는 최대 20개 추출
- weight는 0.0~1.0 (관계 강도)
- 텍스트에 명시된 사실만 사용 (추측 금지)
- JSON 이외 텍스트 절대 출력 금지

[텍스트]
{text}"""


def _call_llm(
    text: str,
    model: str,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> dict[str, Any]:
    """LLM을 호출하여 엔티티/관계를 추출합니다."""
    truncated = text[:3000]  # 토큰 제한을 위해 앞부분만 사용
    prompt = _ENTITY_RELATION_PROMPT.format(text=truncated)
    completion_kwargs = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1,  # 정밀 추출이므로 낮은 temperature
        "max_tokens": 2000,
    }

    try:
        if callable(on_cost_start):
            on_cost_start()
        else:
            from services.usage.usage_decorator import mark_usage_charge_committed
            mark_usage_charge_committed()
        response = litellm.completion(**completion_kwargs)
        raw = response.choices[0].message.content.strip()

        # JSON 블록 추출 (```json ... ``` 형식 처리)
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return {"entities": [], "relations": []}

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning(f"LLM 응답 파싱 실패: {e}")
        return {"entities": [], "relations": []}
    except UsageLockUnavailable:
        raise
    except Exception as e:
        logger.error(f"LLM 호출 실패: {e}")
        return {"entities": [], "relations": []}


def extract_entities(
    text: str,
    model: str = _DEFAULT_MODEL,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> list[dict]:
    """텍스트에서 엔티티 목록을 추출합니다.

    Args:
        text: 분석할 텍스트
        model: 사용할 LLM 모델 ID

    Returns:
        엔티티 딕셔너리 리스트. 각 엔티티: {"name": str, "type": str, "description": str}
    """
    result = _call_llm(text, model, on_cost_start=on_cost_start)
    entities = result.get("entities", [])

    # 필수 필드 검증 및 정규화
    validated = []
    for ent in entities:
        if isinstance(ent, dict) and ent.get("name"):
            validated.append({
                "name": str(ent["name"]).strip(),
                "type": str(ent.get("type", "concept")).strip(),
                "description": str(ent.get("description", "")).strip(),
            })
    return validated


def extract_relations(
    text: str,
    entities: list[dict],
    model: str = _DEFAULT_MODEL,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> list[dict]:
    """텍스트에서 엔티티 간 관계를 추출합니다.

    엔티티 추출과 관계 추출을 분리하지 않고, extract_entities와 동일한
    LLM 호출에서 함께 추출합니다 (효율성을 위해).
    이 함수는 이미 추출된 결과에서 관계만 필터링합니다.

    Args:
        text: 분석할 텍스트 (캐시 미스 시 LLM 재호출)
        entities: 이미 추출된 엔티티 목록
        model: 사용할 LLM 모델 ID

    Returns:
        관계 딕셔너리 리스트. 각 관계: {"source": str, "target": str, "relation": str, "weight": float}
    """
    result = _call_llm(text, model, on_cost_start=on_cost_start)
    relations = result.get("relations", [])

    entity_names = {e["name"] for e in entities}

    validated = []
    for rel in relations:
        if not isinstance(rel, dict):
            continue
        source = str(rel.get("source", "")).strip()
        target = str(rel.get("target", "")).strip()
        if not source or not target:
            continue
        # 추출된 엔티티에 포함된 관계만 허용
        if source not in entity_names or target not in entity_names:
            continue
        try:
            weight = float(rel.get("weight", 0.5))
            weight = max(0.0, min(1.0, weight))  # 0~1 클램핑
        except (ValueError, TypeError):
            weight = 0.5

        validated.append({
            "source": source,
            "target": target,
            "relation": str(rel.get("relation", "관련")).strip(),
            "weight": weight,
        })
    return validated


def extract_graph(
    text: str,
    model: str = _DEFAULT_MODEL,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> dict[str, list]:
    """텍스트에서 엔티티와 관계를 한 번에 추출합니다 (단일 LLM 호출).

    Args:
        text: 분석할 텍스트
        model: 사용할 LLM 모델 ID

    Returns:
        {"entities": [...], "relations": [...]}
    """
    raw = _call_llm(text, model, on_cost_start=on_cost_start)

    entities = []
    for ent in raw.get("entities", []):
        if isinstance(ent, dict) and ent.get("name"):
            entities.append({
                "name": str(ent["name"]).strip(),
                "type": str(ent.get("type", "concept")).strip(),
                "description": str(ent.get("description", "")).strip(),
            })

    entity_names = {e["name"] for e in entities}
    relations = []
    for rel in raw.get("relations", []):
        if not isinstance(rel, dict):
            continue
        source = str(rel.get("source", "")).strip()
        target = str(rel.get("target", "")).strip()
        if not source or not target:
            continue
        if source not in entity_names or target not in entity_names:
            continue
        try:
            weight = max(0.0, min(1.0, float(rel.get("weight", 0.5))))
        except (ValueError, TypeError):
            weight = 0.5
        relations.append({
            "source": source,
            "target": target,
            "relation": str(rel.get("relation", "관련")).strip(),
            "weight": weight,
        })

    logger.info(f"그래프 추출 완료: 엔티티 {len(entities)}개, 관계 {len(relations)}개")
    return {"entities": entities, "relations": relations}


def extract_graph_from_chunks(
    chunks: list[str],
    model: str = _DEFAULT_MODEL,
    *,
    on_cost_start: Optional[Callable[[], None]] = None,
) -> dict[str, list]:
    """여러 청크에서 엔티티/관계를 추출하고 병합합니다.

    긴 텍스트를 청크로 나눠서 각각 추출 후,
    동일 이름 엔티티는 병합하고 관계는 합산합니다.

    Args:
        chunks: 텍스트 청크 리스트
        model: 사용할 LLM 모델 ID

    Returns:
        {"entities": [...], "relations": [...]}
    """
    all_entities: dict[str, dict] = {}  # name -> entity dict
    all_relations: list[dict] = []
    seen_relations: set[tuple[str, str, str]] = set()

    for chunk in chunks:
        if not chunk or not chunk.strip():
            continue

        result = extract_graph(
            chunk,
            model=model,
            on_cost_start=on_cost_start,
        )

        # 엔티티 병합 (같은 이름이면 description 보강)
        for ent in result.get("entities", []):
            name = ent["name"]
            if name in all_entities:
                existing = all_entities[name]
                # description이 더 긴 쪽으로 갱신
                if len(ent.get("description", "")) > len(existing.get("description", "")):
                    existing["description"] = ent["description"]
            else:
                all_entities[name] = dict(ent)

        # 관계 중복 제거 (source, target, relation 동일하면 스킵)
        for rel in result.get("relations", []):
            key = (rel["source"], rel["target"], rel["relation"])
            if key not in seen_relations:
                seen_relations.add(key)
                all_relations.append(rel)

    entities = list(all_entities.values())
    logger.info(f"청크 {len(chunks)}개에서 병합 추출: 엔티티 {len(entities)}개, 관계 {len(all_relations)}개")
    return {"entities": entities, "relations": all_relations}
