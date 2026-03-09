"""AI 비디오 편집 에이전트 서비스

자연어 편집 명령을 파싱하여 편집 액션 목록을 생성한다.
규칙 기반으로 cut, trim, merge, speed 등의 편집 작업을 계획한다.
"""
import re
import uuid
from dataclasses import dataclass, field


@dataclass
class EditResult:
    """편집 명령 처리 결과"""
    video_id: str
    command: str
    actions: list  # [{"type": "cut"|"trim"|"merge"|"speed", "params": {...}}]
    preview_description: str
    estimated_duration: str


# 시간 표현 정규식 패턴
_TIME_PATTERN = r'(\d{1,2}):(\d{2})(?::(\d{2}))?'

# 편집 명령 키워드 매핑 (한국어 + 영어)
_CUT_KEYWORDS = ['자르기', '잘라', '삭제', '제거', 'cut', 'delete', 'remove']
_TRIM_KEYWORDS = ['트림', '다듬기', '앞부분', '뒷부분', '처음', '끝', 'trim']
_MERGE_KEYWORDS = ['합치기', '병합', '이어붙이기', '연결', 'merge', 'join', 'concat']
_SPEED_KEYWORDS = ['속도', '빠르게', '느리게', '배속', 'speed', 'slow', 'fast']


def process_edit_command(video_id: str, command: str) -> EditResult:
    """자연어 편집 명령 파싱 → 편집 액션 목록 생성 (규칙 기반)

    Args:
        video_id: 대상 영상 ID
        command: 자연어 편집 명령 (예: "1:30부터 2:00까지 잘라줘")

    Returns:
        EditResult: 파싱된 편집 액션 목록
    """
    if not video_id or not video_id.strip():
        raise ValueError("video_id는 비어 있을 수 없습니다")
    if not command or not command.strip():
        raise ValueError("편집 명령은 비어 있을 수 없습니다")

    command_lower = command.lower().strip()
    actions = []

    # 시간 범위 추출
    times = _extract_times(command)

    # 명령 유형 감지 및 액션 생성
    if _matches_keywords(command_lower, _CUT_KEYWORDS):
        actions.extend(_build_cut_actions(times, command_lower))
    elif _matches_keywords(command_lower, _TRIM_KEYWORDS):
        actions.extend(_build_trim_actions(times, command_lower))
    elif _matches_keywords(command_lower, _MERGE_KEYWORDS):
        actions.extend(_build_merge_actions(times, command_lower))
    elif _matches_keywords(command_lower, _SPEED_KEYWORDS):
        actions.extend(_build_speed_actions(times, command_lower))
    else:
        # 시간 범위가 있으면 cut으로 추정, 없으면 빈 결과
        if len(times) >= 2:
            actions.extend(_build_cut_actions(times, command_lower))

    # 예상 소요 시간 계산
    estimated = _estimate_duration(actions)
    preview = _build_preview(actions, command)

    return EditResult(
        video_id=video_id,
        command=command,
        actions=actions,
        preview_description=preview,
        estimated_duration=estimated,
    )


def _extract_times(text: str) -> list:
    """텍스트에서 시간 표현(MM:SS 또는 HH:MM:SS)을 추출하여 초 단위 리스트 반환"""
    matches = re.findall(_TIME_PATTERN, text)
    result = []
    for m in matches:
        hours = 0
        if m[2]:  # HH:MM:SS 형식
            hours = int(m[0])
            minutes = int(m[1])
            seconds = int(m[2])
        else:  # MM:SS 형식
            minutes = int(m[0])
            seconds = int(m[1])
        total = hours * 3600 + minutes * 60 + seconds
        result.append(total)
    return result


def _matches_keywords(text: str, keywords: list) -> bool:
    """텍스트에 키워드가 포함되어 있는지 확인"""
    return any(kw in text for kw in keywords)


def _format_seconds(seconds: int) -> str:
    """초를 MM:SS 형식으로 변환"""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"


def _build_cut_actions(times: list, command: str) -> list:
    """cut 액션 생성 — 특정 구간 제거"""
    actions = []
    if len(times) >= 2:
        # 시간 쌍을 순서대로 묶어서 cut 구간 생성
        for i in range(0, len(times) - 1, 2):
            start = min(times[i], times[i + 1])
            end = max(times[i], times[i + 1])
            actions.append({
                "type": "cut",
                "params": {
                    "start": _format_seconds(start),
                    "end": _format_seconds(end),
                    "duration_removed": end - start,
                }
            })
    elif len(times) == 1:
        # 단일 시간이면 해당 지점부터 끝까지 cut
        actions.append({
            "type": "cut",
            "params": {
                "start": _format_seconds(times[0]),
                "end": "end",
                "duration_removed": None,
            }
        })
    return actions


def _build_trim_actions(times: list, command: str) -> list:
    """trim 액션 생성 — 앞/뒤 다듬기"""
    actions = []
    # 앞부분/처음 키워드 + 시간
    is_front = any(kw in command for kw in ['앞부분', '처음', '앞', '시작', 'start', 'front'])
    is_back = any(kw in command for kw in ['뒷부분', '끝', '뒤', '마지막', 'end', 'back'])

    if times:
        if is_front or (not is_back):
            actions.append({
                "type": "trim",
                "params": {
                    "position": "start",
                    "trim_to": _format_seconds(times[0]),
                }
            })
        if is_back and len(times) > 0:
            t = times[-1] if len(times) > 1 else times[0]
            actions.append({
                "type": "trim",
                "params": {
                    "position": "end",
                    "trim_from": _format_seconds(t),
                }
            })
    else:
        # 시간 없이 트림 명령만 있는 경우
        actions.append({
            "type": "trim",
            "params": {
                "position": "both",
                "trim_to": "auto",
            }
        })
    return actions


def _build_merge_actions(times: list, command: str) -> list:
    """merge 액션 생성 — 구간 병합"""
    actions = []
    if len(times) >= 2:
        segments = []
        for i in range(0, len(times) - 1, 2):
            segments.append({
                "start": _format_seconds(times[i]),
                "end": _format_seconds(times[i + 1]),
            })
        actions.append({
            "type": "merge",
            "params": {
                "segments": segments,
                "transition": "crossfade",
            }
        })
    else:
        actions.append({
            "type": "merge",
            "params": {
                "segments": [],
                "transition": "cut",
            }
        })
    return actions


def _build_speed_actions(times: list, command: str) -> list:
    """speed 액션 생성 — 속도 변경"""
    # 배속 값 추출 (예: "2배속", "0.5배", "1.5x")
    speed_match = re.search(r'(\d+\.?\d*)\s*[배x]', command)
    speed_factor = float(speed_match.group(1)) if speed_match else 2.0

    # "느리게" 키워드면 0.5배
    if any(kw in command for kw in ['느리게', 'slow']):
        speed_factor = min(speed_factor, 1.0)
        if speed_factor >= 1.0:
            speed_factor = 0.5

    actions = []
    if len(times) >= 2:
        actions.append({
            "type": "speed",
            "params": {
                "start": _format_seconds(times[0]),
                "end": _format_seconds(times[1]),
                "factor": speed_factor,
            }
        })
    else:
        # 전체 영상 속도 변경
        actions.append({
            "type": "speed",
            "params": {
                "start": "0:00",
                "end": "end",
                "factor": speed_factor,
            }
        })
    return actions


def _estimate_duration(actions: list) -> str:
    """편집 작업 예상 소요 시간 (단순 추정)"""
    if not actions:
        return "0초"

    # 액션당 기본 처리 시간 추정 (초)
    base_times = {
        "cut": 5,
        "trim": 3,
        "merge": 10,
        "speed": 8,
    }
    total = sum(base_times.get(a.get("type", ""), 5) for a in actions)

    if total < 60:
        return f"{total}초"
    return f"{total // 60}분 {total % 60}초"


def _build_preview(actions: list, command: str) -> str:
    """편집 결과 미리보기 설명 생성"""
    if not actions:
        return f"명령 '{command}'에서 인식 가능한 편집 작업이 없습니다."

    descriptions = []
    for action in actions:
        action_type = action.get("type", "unknown")
        params = action.get("params", {})

        if action_type == "cut":
            start = params.get("start", "?")
            end = params.get("end", "?")
            descriptions.append(f"{start}~{end} 구간 제거")
        elif action_type == "trim":
            pos = params.get("position", "?")
            pos_label = {"start": "앞부분", "end": "뒷부분", "both": "앞뒤"}.get(pos, pos)
            descriptions.append(f"{pos_label} 다듬기")
        elif action_type == "merge":
            seg_count = len(params.get("segments", []))
            descriptions.append(f"{seg_count}개 구간 병합")
        elif action_type == "speed":
            factor = params.get("factor", 1.0)
            descriptions.append(f"{factor}배속 변환")

    return " → ".join(descriptions)
