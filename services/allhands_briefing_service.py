"""타운홀/올핸즈 미팅 자막에서 브리핑 팩을 생성하는 서비스

미팅 자막을 분석하여 핵심 결정사항, 액션 아이템, 클립 구간 등을 추출한다.
순수 Python 텍스트 파싱 — AI 호출 없음.
"""
import re
from dataclasses import dataclass, field


# ── 결정 사항 탐지 키워드 ──────────────────────────────────
_DECISION_PATTERNS: list[re.Pattern] = [
    re.compile(r'결정[했되]|확정[했되]|합의[했되]|decided|agreed', re.IGNORECASE),
    re.compile(r'결론[은으]?\s*[:：]', re.IGNORECASE),
    re.compile(r'최종적으로|최종\s*결정', re.IGNORECASE),
    re.compile(r'승인[했되]|approved', re.IGNORECASE),
    re.compile(r'채택[했되]|선정[했되]', re.IGNORECASE),
    re.compile(r'으로\s*(하겠|할게|합시다|하자|가겠|갑시다|가자)', re.IGNORECASE),
    re.compile(r'방향으로\s*진행', re.IGNORECASE),
]

# ── 액션 아이템 탐지 키워드 ─────────────────────────────────
_ACTION_ITEM_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?:담당|책임)\s*[:\-]?\s*(\S+)', re.IGNORECASE),
    re.compile(r'(\S+)\s*(?:님|씨|팀장|매니저|리드|담당자)[이가]\s*(?:해|맡|진행|처리|준비|확인|검토|작성|보고|제출|완료|정리)', re.IGNORECASE),
    re.compile(r'(\S+)\s*(?:will|should|needs?\s+to|must)\s+', re.IGNORECASE),
    re.compile(r'(?:TODO|할\s*일|과제|task)\s*[:\-]', re.IGNORECASE),
    re.compile(r'(?:~까지|까지|by|deadline|기한)\s*[:\-]?\s*(\S+)', re.IGNORECASE),
]

# 소유자(담당자) 추출 패턴
_OWNER_PATTERN = re.compile(
    r'(\S+?)\s*(?:님|씨|팀장|매니저|리드|담당자|팀|부서)',
    re.IGNORECASE,
)
_OWNER_PATTERN_EN = re.compile(
    r'(?:^|\s)([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:will|should|needs?|must|is\s+responsible)',
    re.IGNORECASE,
)

# 마감일 추출 패턴
_DEADLINE_PATTERNS: list[re.Pattern] = [
    re.compile(r'(\d{1,2}[/.\-]\d{1,2}(?:[/.\-]\d{2,4})?)'),   # 날짜
    re.compile(r'(\d+월\s*\d+일)'),                                # 한국어 날짜
    re.compile(r'(이번\s*주|다음\s*주|이번\s*달|다음\s*달|내일|오늘)'),  # 상대 날짜
    re.compile(r'(next\s+(?:week|month|monday|friday))', re.IGNORECASE),
    re.compile(r'(~까지|까지)\s*(\S+)'),
]

# ── 토픽/주제 전환 탐지 ────────────────────────────────────
_TOPIC_PATTERNS: list[re.Pattern] = [
    re.compile(r'다음\s*(?:주제|안건|이슈|항목|토픽)', re.IGNORECASE),
    re.compile(r'(?:주제|안건|이슈)\s*[:\-]\s*(.+)', re.IGNORECASE),
    re.compile(r'(?:다음으로|그럼|자\s*그러면|넘어가)', re.IGNORECASE),
    re.compile(r'(?:next\s+(?:topic|item|agenda))', re.IGNORECASE),
    re.compile(r'(?:moving\s+on|let\'s\s+(?:talk|discuss|move))', re.IGNORECASE),
]

# ── 타임스탬프 패턴 ──────────────────────────────────────
_TIMESTAMP_PATTERN = re.compile(r'\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?')


@dataclass
class BriefingPack:
    """올핸즈 미팅 브리핑 팩"""
    key_decisions: list[str] = field(default_factory=list)
    action_items: list[dict] = field(default_factory=list)
    clip_segments: list[dict] = field(default_factory=list)
    summary: str = ''
    attendee_topics: list[str] = field(default_factory=list)


def create_briefing_pack(transcript: str) -> BriefingPack:
    """타운홀/올핸즈 미팅 자막에서 브리핑 팩을 생성한다.

    Args:
        transcript: 미팅 자막 텍스트

    Returns:
        BriefingPack: 핵심 결정, 액션 아이템, 클립 구간 3개+ 포함

    Raises:
        ValueError: 자막이 비어있는 경우
    """
    if not transcript or not transcript.strip():
        raise ValueError('자막 텍스트가 비어있습니다')

    lines = _split_lines(transcript)

    # 1) 핵심 결정사항 추출
    key_decisions = _extract_decisions(lines)

    # 2) 액션 아이템 추출
    action_items = _extract_action_items(lines)

    # 3) 토픽별 클립 구간 추출 (3개+ 보장)
    clip_segments = _extract_clip_segments(lines, transcript)

    # 4) 참석자 토픽 추출
    attendee_topics = _extract_attendee_topics(lines)

    # 5) 요약 생성
    summary = _generate_summary(key_decisions, action_items, attendee_topics)

    return BriefingPack(
        key_decisions=key_decisions,
        action_items=action_items,
        clip_segments=clip_segments,
        summary=summary,
        attendee_topics=attendee_topics,
    )


# ── 내부 함수 ────────────────────────────────────────────────

def _split_lines(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리"""
    raw_lines = text.strip().split('\n')
    result = []
    for line in raw_lines:
        stripped = line.strip()
        if stripped:
            result.append(stripped)
    return result


def _extract_decisions(lines: list[str]) -> list[str]:
    """결정 사항 키워드가 포함된 문장 추출"""
    decisions = []
    seen = set()
    for line in lines:
        for pattern in _DECISION_PATTERNS:
            if pattern.search(line):
                # 타임스탬프 제거 후 정리
                clean = _strip_timestamp(line)
                if clean and clean not in seen:
                    decisions.append(clean)
                    seen.add(clean)
                break
    return decisions


def _extract_action_items(lines: list[str]) -> list[dict]:
    """액션 아이템 추출 — owner, task, deadline 구조화"""
    items = []
    seen_tasks = set()

    for line in lines:
        is_action = False
        for pattern in _ACTION_ITEM_PATTERNS:
            if pattern.search(line):
                is_action = True
                break

        if not is_action:
            continue

        clean = _strip_timestamp(line)
        if not clean or clean in seen_tasks:
            continue

        owner = _extract_owner(clean)
        deadline = _extract_deadline(clean)
        task = _clean_task_text(clean)

        if task:
            items.append({
                'owner': owner,
                'task': task,
                'deadline': deadline,
            })
            seen_tasks.add(clean)

    return items


def _extract_clip_segments(lines: list[str], full_text: str) -> list[dict]:
    """토픽 전환 지점을 감지하여 클립 구간 추출 (3개+ 보장)

    타임스탬프가 있으면 활용하고, 없으면 문장 인덱스 기반으로 추정.
    """
    # 타임스탬프가 있는 라인 수집
    timestamped: list[tuple[str, str]] = []  # (timestamp, line)
    for line in lines:
        m = _TIMESTAMP_PATTERN.search(line)
        if m:
            timestamped.append((m.group(1), line))

    has_timestamps = len(timestamped) >= 3

    # 토픽 전환 지점 감지
    topic_points: list[dict] = []
    for i, line in enumerate(lines):
        is_topic = False
        topic_name = ''
        for pattern in _TOPIC_PATTERNS:
            m = pattern.search(line)
            if m:
                is_topic = True
                topic_name = m.group(1).strip() if m.lastindex and m.group(1) else ''
                break

        # 결정 사항 문장도 중요 구간으로 간주
        if not is_topic:
            for pattern in _DECISION_PATTERNS:
                if pattern.search(line):
                    is_topic = True
                    break

        if is_topic:
            timestamp = _find_nearest_timestamp(line, lines, i, has_timestamps)
            clean_topic = topic_name or _extract_topic_name(line)
            topic_points.append({
                'index': i,
                'timestamp': timestamp,
                'topic': clean_topic,
                'line': line,
            })

    # 3개 미만이면 균등 분할로 보강
    if len(topic_points) < 3:
        topic_points = _pad_topic_points(topic_points, lines, has_timestamps)

    # 클립 구간 생성 (시작-끝 쌍)
    segments = []
    for i, tp in enumerate(topic_points):
        start_ts = tp['timestamp']
        # 다음 토픽 시작 전까지가 끝 (없으면 +2분 추정)
        if i + 1 < len(topic_points):
            end_ts = topic_points[i + 1]['timestamp']
        else:
            end_ts = _add_minutes(start_ts, 2)

        segments.append({
            'start': start_ts,
            'end': end_ts,
            'topic': tp['topic'] or f'주제 {i + 1}',
        })

    return segments[:10]  # 최대 10개로 제한


def _extract_attendee_topics(lines: list[str]) -> list[str]:
    """참석자별 언급 토픽 추출"""
    topics = []
    seen = set()

    for line in lines:
        # "주제: ..." 또는 "안건: ..." 패턴
        m = re.search(r'(?:주제|안건|이슈|agenda|topic)\s*[:\-]\s*(.+)', line, re.IGNORECASE)
        if m:
            topic = m.group(1).strip()
            if topic and topic not in seen:
                topics.append(topic)
                seen.add(topic)

    # 토픽이 부족하면 결정 사항에서 추출
    if len(topics) < 2:
        for line in lines:
            for pattern in _TOPIC_PATTERNS:
                m = pattern.search(line)
                if m:
                    text = _strip_timestamp(line)
                    if text and text not in seen and len(text) > 3:
                        topics.append(text)
                        seen.add(text)
                    break

    return topics


def _generate_summary(decisions: list[str], action_items: list[dict],
                      topics: list[str]) -> str:
    """브리핑 요약 생성"""
    parts = []

    if decisions:
        parts.append(f'주요 결정 {len(decisions)}건')
    if action_items:
        parts.append(f'액션 아이템 {len(action_items)}건')
    if topics:
        parts.append(f'논의 주제 {len(topics)}건')

    if parts:
        return f'미팅 브리핑: {", ".join(parts)} 도출.'
    return '미팅 브리핑 요약'


# ── 유틸리티 ────────────────────────────────────────────────

def _strip_timestamp(text: str) -> str:
    """문장에서 타임스탬프 제거"""
    cleaned = _TIMESTAMP_PATTERN.sub('', text).strip()
    # 앞뒤 구두점/공백 정리
    return cleaned.strip('[] \t')


def _extract_owner(text: str) -> str:
    """텍스트에서 담당자 추출"""
    m = _OWNER_PATTERN.search(text)
    if m:
        return m.group(1).strip()
    m = _OWNER_PATTERN_EN.search(text)
    if m:
        return m.group(1).strip()
    return '미정'


def _extract_deadline(text: str) -> str:
    """텍스트에서 마감일 추출"""
    for pattern in _DEADLINE_PATTERNS:
        m = pattern.search(text)
        if m:
            # 마지막 그룹 반환
            return m.group(m.lastindex or 1).strip()
    return '미정'


def _clean_task_text(text: str) -> str:
    """액션 아이템에서 불필요한 접두어 제거"""
    # "TODO:", "할 일:" 등 제거
    cleaned = re.sub(r'^(?:TODO|할\s*일|과제|task)\s*[:\-]\s*', '', text, flags=re.IGNORECASE)
    return cleaned.strip()


def _find_nearest_timestamp(line: str, lines: list[str], index: int,
                            has_timestamps: bool) -> str:
    """해당 라인 또는 인근 라인에서 타임스탬프 추출"""
    # 현재 라인에서 찾기
    m = _TIMESTAMP_PATTERN.search(line)
    if m:
        return m.group(1)

    if has_timestamps:
        # 앞뒤 3줄 범위에서 검색
        for offset in range(1, 4):
            for idx in [index - offset, index + offset]:
                if 0 <= idx < len(lines):
                    m = _TIMESTAMP_PATTERN.search(lines[idx])
                    if m:
                        return m.group(1)

    # 타임스탬프 없으면 인덱스 기반 추정 (라인당 약 10초)
    total_seconds = index * 10
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f'{minutes}:{seconds:02d}'


def _extract_topic_name(line: str) -> str:
    """라인에서 토픽 이름 추출"""
    clean = _strip_timestamp(line)
    # 전환 키워드 제거
    clean = re.sub(
        r'(?:다음\s*(?:주제|안건|이슈|항목|토픽)|다음으로|그럼|자\s*그러면|넘어가|'
        r'next\s+(?:topic|item|agenda)|moving\s+on|let\'s\s+(?:talk|discuss|move))',
        '', clean, flags=re.IGNORECASE,
    ).strip()
    # 앞뒤 구두점 정리
    clean = clean.strip('.,;:!?- ')
    return clean if len(clean) > 1 else '미분류 주제'


def _pad_topic_points(existing: list[dict], lines: list[str],
                      has_timestamps: bool) -> list[dict]:
    """3개 미만일 때 균등 분할로 보강

    라인 수가 부족해도 반드시 3개를 채운다 (같은 라인 재사용 허용하지 않고
    가용 라인을 모두 사용한 뒤에도 부족하면 가상 구간을 추가).
    """
    existing_indices = {tp['index'] for tp in existing}
    padded = list(existing)

    if not lines:
        # 라인이 없으면 가상 구간으로 채움
        while len(padded) < 3:
            num = len(padded) + 1
            padded.append({
                'index': num - 1,
                'timestamp': f'{(num - 1) * 2}:00',
                'topic': f'주제 {num}',
                'line': '',
            })
        return padded

    # 사용 가능한 라인 인덱스 (기존에 없는 것만)
    available = [i for i in range(len(lines)) if i not in existing_indices]

    if available:
        # 균등 간격으로 선택
        needed = 3 - len(padded)
        step = max(1, len(available) // (needed + 1))
        pick_indices = []
        for i in range(1, needed + 1):
            pos = min(i * step, len(available) - 1)
            # 중복 방지: 이미 선택한 위치면 다음으로
            while pos in pick_indices and pos < len(available) - 1:
                pos += 1
            pick_indices.append(pos)

        for pos in pick_indices:
            if len(padded) >= 3:
                break
            idx = available[pos]
            ts = _find_nearest_timestamp(lines[idx], lines, idx, has_timestamps)
            topic = _extract_topic_name(lines[idx])
            padded.append({
                'index': idx,
                'timestamp': ts,
                'topic': topic if len(topic) > 1 else f'주제 {len(padded) + 1}',
                'line': lines[idx],
            })
            existing_indices.add(idx)

    # 그래도 부족하면 가상 구간 추가
    while len(padded) < 3:
        num = len(padded) + 1
        last_idx = padded[-1]['index'] if padded else 0
        padded.append({
            'index': last_idx + 1,
            'timestamp': f'{num * 2}:00',
            'topic': f'주제 {num}',
            'line': '',
        })

    # 인덱스 순 정렬
    padded.sort(key=lambda x: x['index'])
    return padded


def _add_minutes(timestamp: str, minutes: int) -> str:
    """타임스탬프에 분을 더한다"""
    parts = timestamp.split(':')
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            total_min = h * 60 + m + minutes
            return f'{total_min // 60}:{total_min % 60:02d}:{s:02d}'
        elif len(parts) == 2:
            m, s = int(parts[0]), int(parts[1])
            new_m = m + minutes
            return f'{new_m}:{s:02d}'
    except (ValueError, IndexError):
        pass
    return timestamp
