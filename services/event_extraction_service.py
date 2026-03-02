"""
이벤트 추출 서비스

YouTube 영상 자막에서 액션 아이템, 핵심 포인트, 결정 사항, 질문 등
구조화된 이벤트를 추출합니다.
"""
import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# 이벤트 유형 상수
EVENT_TYPES = {
    'action_item': '액션 아이템',
    'key_point': '핵심 포인트',
    'decision': '결정 사항',
    'question': '질문',
}

# 기본 모델 (설정 없을 때 사용)
DEFAULT_MODEL = 'zhipuai/GLM-4.5-Air'


def extract_events(transcript: str, model: Optional[str] = None) -> List[Dict]:
    """자막에서 구조화된 이벤트를 추출합니다.

    Args:
        transcript: YouTube 영상 자막 텍스트
        model: 사용할 AI 모델 ID (기본값: DEFAULT_MODEL)

    Returns:
        이벤트 딕셔너리 목록. 실패 시 빈 리스트 반환.

    Raises:
        ValueError: transcript가 비어있는 경우
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막이 비어있습니다. 이벤트를 추출할 수 없습니다.")

    from prompts.event_extraction import EVENT_EXTRACTION_PROMPT
    from services.ai_service import _build_completion_kwargs

    # 자막이 너무 길면 앞부분만 사용 (토큰 절약)
    max_transcript_len = 8000
    truncated_transcript = transcript[:max_transcript_len]
    if len(transcript) > max_transcript_len:
        truncated_transcript += "\n\n[자막이 너무 길어 일부만 분석되었습니다]"

    prompt = EVENT_EXTRACTION_PROMPT + truncated_transcript

    used_model = model or DEFAULT_MODEL

    try:
        kwargs = _build_completion_kwargs(
            model=used_model,
            prompt=prompt,
            style_id='summary',  # 정밀형 temperature 0.5 사용
        )
        # 이벤트 추출은 짧은 JSON 응답이므로 max_tokens 제한
        kwargs['max_tokens'] = 4000

        from litellm import completion
        response = completion(**kwargs)
        raw_text = response.choices[0].message.content or ''

        events = _parse_events_json(raw_text)
        validated = _validate_events(events)
        logger.info("이벤트 추출 완료: %d개 이벤트 (모델: %s)", len(validated), used_model)
        return validated

    except ValueError:
        raise
    except Exception as e:
        logger.error("이벤트 추출 실패: %s", str(e), exc_info=True)
        raise RuntimeError(f"이벤트 추출 중 오류가 발생했습니다: {str(e)}") from e


def _parse_events_json(raw_text: str) -> List[Dict]:
    """LLM 응답에서 JSON 배열을 파싱합니다.

    마크다운 코드블록이나 여분의 텍스트를 제거하고 JSON을 추출합니다.

    Args:
        raw_text: LLM이 반환한 원시 텍스트

    Returns:
        파싱된 이벤트 리스트. 파싱 실패 시 빈 리스트.
    """
    if not raw_text:
        return []

    # 마크다운 코드블록 제거 (```json ... ``` 또는 ``` ... ```)
    cleaned = re.sub(r'```(?:json)?\s*', '', raw_text).strip()
    cleaned = re.sub(r'```\s*$', '', cleaned).strip()

    # JSON 배열 패턴으로 직접 추출 시도
    array_match = re.search(r'\[[\s\S]*\]', cleaned)
    if array_match:
        json_str = array_match.group(0)
        try:
            result = json.loads(json_str)
            if isinstance(result, list):
                return result
        except json.JSONDecodeError:
            pass

    # 전체 텍스트 직접 파싱 시도
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return result
    except json.JSONDecodeError:
        pass

    logger.warning("이벤트 JSON 파싱 실패. 원시 텍스트 길이: %d", len(raw_text))
    return []


def _validate_events(events: List[Dict]) -> List[Dict]:
    """이벤트 목록을 검증하고 정규화합니다.

    필수 필드가 없는 이벤트는 제거하고, 선택 필드는 기본값으로 채웁니다.

    Args:
        events: 파싱된 이벤트 리스트

    Returns:
        검증/정규화된 이벤트 리스트
    """
    valid_events = []
    valid_types = set(EVENT_TYPES.keys())

    for i, event in enumerate(events):
        if not isinstance(event, dict):
            logger.warning("이벤트 #%d: dict가 아님 (%s), 건너뜀", i, type(event))
            continue

        event_type = event.get('type', '')
        if event_type not in valid_types:
            logger.warning("이벤트 #%d: 알 수 없는 타입 '%s', 건너뜀", i, event_type)
            continue

        content = str(event.get('content', '')).strip()
        if not content:
            logger.warning("이벤트 #%d: content가 비어있음, 건너뜀", i)
            continue

        # 기본 구조 정규화
        normalized: Dict = {
            'type': event_type,
            'content': content[:200],  # 최대 200자
            'timestamp': str(event.get('timestamp', '')).strip(),
            'context': str(event.get('context', '')).strip()[:300],
        }

        # 타입별 전용 필드 추가
        if event_type == 'action_item':
            priority = event.get('priority', 'medium')
            if priority not in ('high', 'medium', 'low'):
                priority = 'medium'
            normalized['priority'] = priority

        elif event_type == 'key_point':
            try:
                importance = float(event.get('importance', 0.7))
                importance = max(0.0, min(1.0, importance))
            except (TypeError, ValueError):
                importance = 0.7
            normalized['importance'] = importance

        elif event_type == 'decision':
            stakeholders = event.get('stakeholders', [])
            if not isinstance(stakeholders, list):
                stakeholders = []
            normalized['stakeholders'] = [str(s)[:50] for s in stakeholders[:5]]

        elif event_type == 'question':
            status = event.get('status', 'open')
            if status not in ('open', 'resolved'):
                status = 'open'
            normalized['status'] = status

        valid_events.append(normalized)

    return valid_events


def categorize_events(events: List[Dict]) -> Dict[str, List[Dict]]:
    """이벤트 목록을 유형별로 분류합니다.

    Args:
        events: 검증된 이벤트 리스트

    Returns:
        유형별 이벤트 딕셔너리 {'action_item': [...], 'key_point': [...], ...}
    """
    categorized: Dict[str, List[Dict]] = {key: [] for key in EVENT_TYPES}

    for event in events:
        event_type = event.get('type', '')
        if event_type in categorized:
            categorized[event_type].append(event)

    return categorized


def get_event_summary(events: List[Dict]) -> Dict:
    """이벤트 목록의 요약 통계를 반환합니다.

    Args:
        events: 이벤트 리스트

    Returns:
        요약 딕셔너리 (총 개수, 유형별 개수, 우선순위 높은 액션 아이템, 중요 핵심 포인트)
    """
    categorized = categorize_events(events)

    # 우선순위 높은 액션 아이템
    high_priority_actions = [
        e for e in categorized['action_item']
        if e.get('priority') == 'high'
    ]

    # 중요도 높은 핵심 포인트 (0.8 이상)
    important_key_points = [
        e for e in categorized['key_point']
        if e.get('importance', 0) >= 0.8
    ]

    return {
        'total': len(events),
        'by_type': {
            event_type: len(categorized[event_type])
            for event_type in EVENT_TYPES
        },
        'type_labels': EVENT_TYPES,
        'highlights': {
            'high_priority_actions': high_priority_actions[:3],
            'important_key_points': important_key_points[:3],
            'open_questions': [
                e for e in categorized['question']
                if e.get('status') == 'open'
            ][:3],
        },
    }
