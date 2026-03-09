"""
콜백 플래너 서비스

시리즈 콘텐츠의 떡밥(foreshadowing)/회수(callback) 포인트를 설계하고,
미회수 떡밥을 추적하여 회수 시점을 제안합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


@dataclass
class CallbackPoint:
    """떡밥/회수 포인트."""
    episode: int                    # 에피소드 번호
    position: str                   # "intro" | "middle" | "outro"
    callback_type: str              # "foreshadowing" | "question" | "cliffhanger" | "callback"
    description: str                # 떡밥/회수 설명
    target_episode: Optional[int]   # 회수 예정 에피소드 (None이면 미정)
    resolved: bool = False          # 회수 여부


@dataclass
class UnresolvedCallback:
    """미회수 떡밥."""
    point: CallbackPoint            # 원래 떡밥 포인트
    episodes_waiting: int           # 미회수 상태로 경과한 에피소드 수
    urgency: str = 'low'            # "low" | "medium" | "high"


# ── 키워드 패턴 ──────────────────────────────────

# 떡밥 키워드 (foreshadowing 감지)
_FORESHADOW_KEYWORDS = [
    '나중에', '다음에', '곧', '앞으로', '추후', '이후에',
    '뒤에서', '다시 다루', '자세히 다루', '돌아오',
    'later', 'soon', 'upcoming', 'next time', 'stay tuned',
    'we\'ll see', 'we\'ll cover', 'come back',
]
_FORESHADOW_RE = re.compile(
    '|'.join(re.escape(k) for k in _FORESHADOW_KEYWORDS),
    re.IGNORECASE
)

# 질문형 키워드 (question 감지)
_QUESTION_KEYWORDS = [
    '왜일까', '어떻게 될까', '무엇일까', '과연', '정말일까',
    '궁금하', '알아보', '살펴보',
    'why', 'how come', 'what if', 'wonder',
]
_QUESTION_RE = re.compile(
    '|'.join(re.escape(k) for k in _QUESTION_KEYWORDS),
    re.IGNORECASE
)

# 클리프행어 키워드 (cliffhanger 감지)
_CLIFFHANGER_KEYWORDS = [
    '다음 편', '계속', '이어서', '다음 화', '다음 시간',
    '다음 회', '다음 이야기', '다음 에피소드',
    'to be continued', 'next episode', 'next part', 'continued',
    'stay tuned', 'cliffhanger',
]
_CLIFFHANGER_RE = re.compile(
    '|'.join(re.escape(k) for k in _CLIFFHANGER_KEYWORDS),
    re.IGNORECASE
)

# 회수 키워드 (callback 감지)
_CALLBACK_KEYWORDS = [
    '앞서 언급', '이전에', '지난번', '말했던', '다뤘던',
    '돌아가', '앞에서', '설명했던', '소개했던',
    'as mentioned', 'previously', 'earlier', 'as we discussed',
    'recall', 'remember when', 'going back',
]
_CALLBACK_RE = re.compile(
    '|'.join(re.escape(k) for k in _CALLBACK_KEYWORDS),
    re.IGNORECASE
)


def _detect_position(text: str, full_text: str) -> str:
    """텍스트가 콘텐츠의 어느 위치에 있는지 추정합니다."""
    if not full_text:
        return 'middle'
    pos = full_text.find(text)
    if pos < 0:
        return 'middle'
    ratio = pos / max(1, len(full_text))
    if ratio < 0.25:
        return 'intro'
    elif ratio > 0.75:
        return 'outro'
    return 'middle'


def _extract_points_from_text(
    episode: int,
    text: str,
) -> List[CallbackPoint]:
    """단일 에피소드 텍스트에서 떡밥/회수 포인트를 추출합니다."""
    points = []
    sentences = re.split(r'[.!?。]\s*', text)

    for sentence in sentences:
        sentence = sentence.strip()
        if len(sentence) < 5:
            continue

        position = _detect_position(sentence, text)

        # 회수(callback) 감지 — 기존 떡밥의 회수
        if _CALLBACK_RE.search(sentence):
            points.append(CallbackPoint(
                episode=episode,
                position=position,
                callback_type='callback',
                description=sentence[:100],
                target_episode=None,
                resolved=True,
            ))
            continue

        # 클리프행어 감지
        if _CLIFFHANGER_RE.search(sentence):
            points.append(CallbackPoint(
                episode=episode,
                position=position,
                callback_type='cliffhanger',
                description=sentence[:100],
                target_episode=episode + 1,
                resolved=False,
            ))
            continue

        # 떡밥(foreshadowing) 감지
        if _FORESHADOW_RE.search(sentence):
            points.append(CallbackPoint(
                episode=episode,
                position=position,
                callback_type='foreshadowing',
                description=sentence[:100],
                target_episode=None,
                resolved=False,
            ))
            continue

        # 질문형 감지
        if _QUESTION_RE.search(sentence):
            points.append(CallbackPoint(
                episode=episode,
                position=position,
                callback_type='question',
                description=sentence[:100],
                target_episode=None,
                resolved=False,
            ))

    return points


def _match_callbacks_to_foreshadows(
    all_points: List[CallbackPoint],
) -> List[CallbackPoint]:
    """callback 타입 포인트를 이전 foreshadowing과 매칭하여 resolved 처리합니다."""
    # 미회수 떡밥 목록 (foreshadowing, question, cliffhanger)
    unresolved = [
        p for p in all_points
        if p.callback_type in ('foreshadowing', 'question', 'cliffhanger')
        and not p.resolved
    ]
    # 회수 포인트 목록
    callbacks = [p for p in all_points if p.callback_type == 'callback']

    for cb in callbacks:
        # 가장 오래된 미회수 떡밥과 매칭 (간단한 FIFO 전략)
        for ur in unresolved:
            if ur.episode < cb.episode and not ur.resolved:
                ur.resolved = True
                ur.target_episode = cb.episode
                break

    return all_points


# ── 메인 함수 ────────────────────────────────────

def plan_callbacks(episode_outline: List[Dict]) -> List[CallbackPoint]:
    """각 에피소드에 떡밥/회수 포인트를 설계합니다.

    Args:
        episode_outline: [{"episode": 1, "content": "..."}, ...]
            각 dict에 "episode"(int)와 "content"(str) 필수.

    Returns:
        전체 에피소드의 CallbackPoint 목록
    """
    if not episode_outline:
        return []

    all_points: List[CallbackPoint] = []

    for ep in episode_outline:
        episode_num = ep.get('episode', 0)
        content = ep.get('content', '')
        if not content or not content.strip():
            continue
        points = _extract_points_from_text(episode_num, content)
        all_points.extend(points)

    # 회수-떡밥 매칭
    all_points = _match_callbacks_to_foreshadows(all_points)

    return all_points


def check_callback_resolution(
    episodes: List[Dict],
) -> List[UnresolvedCallback]:
    """미회수 떡밥 목록을 반환합니다.

    Args:
        episodes: [{"episode": 1, "content": "..."}, ...]

    Returns:
        UnresolvedCallback 목록 (3회 이상 미회수 시 urgency=high)
    """
    if not episodes:
        return []

    all_points = plan_callbacks(episodes)
    max_episode = max((ep.get('episode', 0) for ep in episodes), default=0)

    unresolved_list: List[UnresolvedCallback] = []

    for point in all_points:
        if point.callback_type == 'callback':
            continue
        if point.resolved:
            continue

        episodes_waiting = max_episode - point.episode

        if episodes_waiting >= 3:
            urgency = 'high'
        elif episodes_waiting >= 2:
            urgency = 'medium'
        else:
            urgency = 'low'

        unresolved_list.append(UnresolvedCallback(
            point=point,
            episodes_waiting=episodes_waiting,
            urgency=urgency,
        ))

    # urgency 순서: high > medium > low
    urgency_order = {'high': 0, 'medium': 1, 'low': 2}
    unresolved_list.sort(key=lambda x: urgency_order.get(x.urgency, 2))

    return unresolved_list


def suggest_resolution(
    unresolved: List[UnresolvedCallback],
) -> List[Dict]:
    """미회수 떡밥에 대한 회수 제안을 반환합니다.

    Args:
        unresolved: check_callback_resolution의 반환값

    Returns:
        [{"episode_origin": int, "description": str, "urgency": str,
          "suggestion": str, "recommended_episode": int|None}]
    """
    if not unresolved:
        return []

    suggestions: List[Dict] = []

    for item in unresolved:
        point = item.point

        # 회수 제안 메시지 생성
        if item.urgency == 'high':
            suggestion = (
                f'긴급: {item.episodes_waiting}회 동안 미회수 상태입니다. '
                f'즉시 회수하거나 독자에게 힌트를 추가하세요.'
            )
            recommended = point.episode + item.episodes_waiting + 1
        elif item.urgency == 'medium':
            suggestion = (
                f'{item.episodes_waiting}회 경과. '
                f'다음 에피소드에서 관련 내용을 언급해 회수하세요.'
            )
            recommended = point.episode + item.episodes_waiting + 1
        else:
            suggestion = '아직 여유가 있지만, 회수 시점을 계획해두세요.'
            recommended = point.target_episode

        suggestions.append({
            'episode_origin': point.episode,
            'description': point.description,
            'urgency': item.urgency,
            'suggestion': suggestion,
            'recommended_episode': recommended,
        })

    return suggestions
