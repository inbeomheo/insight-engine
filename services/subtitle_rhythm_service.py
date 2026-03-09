"""
자막 리듬 최적화 + 트랜스크립트 편집기 (T4.3)
SRT 자막의 줄바꿈/구간/타이밍 최적화 + 텍스트 편집 → 컷 포인트 생성.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# ── 설정 상수 ──
MIN_DURATION_SEC = 0.8        # 최소 자막 표시 시간(초) — 이보다 짧으면 병합 대상
MAX_DURATION_SEC = 7.0        # 최대 자막 표시 시간(초) — 이보다 길면 분할 대상
MAX_CHARS_PER_LINE = 42       # 한 줄 최대 글자 수 — 초과 시 줄바꿈 삽입
OVERLAP_THRESHOLD_MS = 50     # 겹침 허용 한계(ms) — 초과 시 겹침 해소


@dataclass
class SrtEntry:
    """SRT 자막 한 항목"""
    index: int
    start_time: str         # "HH:MM:SS,mmm"
    end_time: str
    text: str


@dataclass
class OptimizedSrt:
    """리듬 최적화 결과"""
    entries: List[SrtEntry]
    changes_made: List[str]     # 적용된 최적화 목록
    original_count: int
    optimized_count: int


@dataclass
class CutPoint:
    """텍스트 편집에서 생성된 컷 포인트"""
    start_time: str
    end_time: str
    reason: str                 # "deleted" | "shortened" | "rearranged"
    original_text: str


# ── 시간 변환 유틸 ──

def _time_to_ms(time_str: str) -> int:
    """SRT 타임코드 → 밀리초 변환. 'HH:MM:SS,mmm' 형식."""
    time_str = time_str.strip()
    match = re.match(r'(\d{1,2}):(\d{2}):(\d{2})[,.](\d{3})', time_str)
    if not match:
        raise ValueError(f"잘못된 타임코드 형식: '{time_str}'")
    h, m, s, ms = (int(g) for g in match.groups())
    return h * 3600000 + m * 60000 + s * 1000 + ms


def _ms_to_time(ms: int) -> str:
    """밀리초 → SRT 타임코드 변환."""
    if ms < 0:
        ms = 0
    h = ms // 3600000
    ms %= 3600000
    m = ms // 60000
    ms %= 60000
    s = ms // 1000
    remaining = ms % 1000
    return f"{h:02d}:{m:02d}:{s:02d},{remaining:03d}"


def _duration_sec(entry: SrtEntry) -> float:
    """자막 항목의 표시 시간(초)."""
    return (_time_to_ms(entry.end_time) - _time_to_ms(entry.start_time)) / 1000.0


# ── 파싱 / 직렬화 ──

def parse_srt(srt_content: str) -> List[SrtEntry]:
    """SRT 문자열 파싱 → SrtEntry 리스트."""
    if not srt_content or not srt_content.strip():
        return []

    # BOM 제거
    content = srt_content.strip().lstrip('\ufeff')

    entries: List[SrtEntry] = []
    # 빈 줄 2개 이상으로 블록 분리 (블록 사이 빈 줄)
    blocks = re.split(r'\n\s*\n', content)

    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue

        # 첫 줄: 인덱스 번호
        index_line = lines[0].strip()
        if not index_line.isdigit():
            continue
        index = int(index_line)

        # 둘째 줄: 타임코드
        time_line = lines[1].strip()
        time_match = re.match(
            r'(\d{1,2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*(\d{1,2}:\d{2}:\d{2}[,.]\d{3})',
            time_line
        )
        if not time_match:
            continue

        start_time = time_match.group(1).replace('.', ',')
        end_time = time_match.group(2).replace('.', ',')

        # 셋째 줄 이후: 자막 텍스트
        text = '\n'.join(lines[2:]).strip()

        entries.append(SrtEntry(
            index=index,
            start_time=start_time,
            end_time=end_time,
            text=text,
        ))

    return entries


def entries_to_srt(entries: List[SrtEntry]) -> str:
    """SrtEntry 리스트를 SRT 문자열로 직렬화."""
    blocks: List[str] = []
    for i, entry in enumerate(entries, 1):
        block = f"{i}\n{entry.start_time} --> {entry.end_time}\n{entry.text}"
        blocks.append(block)
    return '\n\n'.join(blocks) + '\n' if blocks else ''


# ── 최적화 내부 함수 ──

def _fix_line_breaks(entries: List[SrtEntry]) -> tuple[List[SrtEntry], List[str]]:
    """한 줄이 MAX_CHARS_PER_LINE을 초과하면 적절한 위치에서 줄바꿈 삽입."""
    changes: List[str] = []
    result: List[SrtEntry] = []

    for entry in entries:
        new_lines: List[str] = []
        modified = False

        for line in entry.text.split('\n'):
            if len(line) > MAX_CHARS_PER_LINE:
                # 중간 지점의 공백/쉼표/마침표에서 분할
                mid = len(line) // 2
                best_pos = -1
                best_dist = len(line)

                for pos, ch in enumerate(line):
                    if ch in (' ', ',', '.', '，', '。', '、'):
                        dist = abs(pos - mid)
                        if dist < best_dist:
                            best_dist = dist
                            best_pos = pos

                if best_pos > 0:
                    # 구분자가 공백이면 공백 제거, 아니면 구분자 뒤에서 분할
                    if line[best_pos] == ' ':
                        new_lines.append(line[:best_pos])
                        new_lines.append(line[best_pos + 1:])
                    else:
                        new_lines.append(line[:best_pos + 1])
                        new_lines.append(line[best_pos + 1:])
                    modified = True
                else:
                    # 적절한 분할 지점이 없으면 강제 분할
                    new_lines.append(line[:mid])
                    new_lines.append(line[mid:])
                    modified = True
            else:
                new_lines.append(line)

        new_text = '\n'.join(new_lines)
        result.append(SrtEntry(
            index=entry.index,
            start_time=entry.start_time,
            end_time=entry.end_time,
            text=new_text,
        ))
        if modified:
            changes.append(f"#{entry.index}: 긴 줄 줄바꿈 삽입")

    return result, changes


def _merge_short(entries: List[SrtEntry]) -> tuple[List[SrtEntry], List[str]]:
    """MIN_DURATION_SEC 미만인 짧은 자막을 인접 자막과 병합."""
    if not entries:
        return entries, []

    changes: List[str] = []
    result: List[SrtEntry] = []
    skip_next = False

    for i, entry in enumerate(entries):
        if skip_next:
            skip_next = False
            continue

        dur = _duration_sec(entry)
        if dur < MIN_DURATION_SEC and i + 1 < len(entries):
            # 다음 자막과 병합
            next_entry = entries[i + 1]
            merged_text = entry.text + ' ' + next_entry.text
            merged = SrtEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=next_entry.end_time,
                text=merged_text,
            )
            result.append(merged)
            changes.append(
                f"#{entry.index}+#{next_entry.index}: "
                f"짧은 자막 병합 ({dur:.1f}초)"
            )
            skip_next = True
        else:
            result.append(entry)

    return result, changes


def _split_long(entries: List[SrtEntry]) -> tuple[List[SrtEntry], List[str]]:
    """MAX_DURATION_SEC 초과인 긴 자막을 시간 균등 분할."""
    changes: List[str] = []
    result: List[SrtEntry] = []

    for entry in entries:
        dur = _duration_sec(entry)
        if dur > MAX_DURATION_SEC:
            start_ms = _time_to_ms(entry.start_time)
            end_ms = _time_to_ms(entry.end_time)
            mid_ms = (start_ms + end_ms) // 2

            # 텍스트를 문장/공백 기준으로 분할
            text = entry.text.replace('\n', ' ')
            split_pos = len(text) // 2

            # 중간 지점 근처 공백 찾기
            best = -1
            best_dist = len(text)
            for pos, ch in enumerate(text):
                if ch == ' ':
                    d = abs(pos - split_pos)
                    if d < best_dist:
                        best_dist = d
                        best = pos

            if best > 0:
                text1 = text[:best].strip()
                text2 = text[best + 1:].strip()
            else:
                text1 = text[:split_pos].strip()
                text2 = text[split_pos:].strip()

            result.append(SrtEntry(
                index=entry.index,
                start_time=entry.start_time,
                end_time=_ms_to_time(mid_ms),
                text=text1,
            ))
            result.append(SrtEntry(
                index=entry.index,
                start_time=_ms_to_time(mid_ms),
                end_time=entry.end_time,
                text=text2,
            ))
            changes.append(
                f"#{entry.index}: 긴 자막 분할 ({dur:.1f}초 → 2개)"
            )
        else:
            result.append(entry)

    return result, changes


def _resolve_overlaps(entries: List[SrtEntry]) -> tuple[List[SrtEntry], List[str]]:
    """인접 자막 간 타이밍 겹침 해소."""
    if len(entries) < 2:
        return entries, []

    changes: List[str] = []
    result = [entries[0]]

    for i in range(1, len(entries)):
        prev = result[-1]
        curr = entries[i]

        prev_end = _time_to_ms(prev.end_time)
        curr_start = _time_to_ms(curr.start_time)

        overlap = prev_end - curr_start
        if overlap > OVERLAP_THRESHOLD_MS:
            # 이전 자막의 끝 시간을 현재 자막의 시작 직전으로 조정
            adjusted_end = curr_start - 1
            result[-1] = SrtEntry(
                index=prev.index,
                start_time=prev.start_time,
                end_time=_ms_to_time(adjusted_end),
                text=prev.text,
            )
            changes.append(
                f"#{prev.index}↔#{curr.index}: 겹침 해소 ({overlap}ms)"
            )

        result.append(curr)

    return result, changes


def _reindex(entries: List[SrtEntry]) -> List[SrtEntry]:
    """인덱스 번호 재정렬."""
    return [
        SrtEntry(index=i, start_time=e.start_time, end_time=e.end_time, text=e.text)
        for i, e in enumerate(entries, 1)
    ]


# ── 공개 API ──

def optimize_rhythm(srt_content: str) -> OptimizedSrt:
    """SRT 자막 리듬 최적화 — 줄바꿈, 너무 긴/짧은 구간 조정, 겹침 해소."""
    entries = parse_srt(srt_content)
    original_count = len(entries)

    if not entries:
        return OptimizedSrt(
            entries=[],
            changes_made=[],
            original_count=0,
            optimized_count=0,
        )

    all_changes: List[str] = []

    # 1단계: 겹침 해소
    entries, changes = _resolve_overlaps(entries)
    all_changes.extend(changes)

    # 2단계: 짧은 자막 병합
    entries, changes = _merge_short(entries)
    all_changes.extend(changes)

    # 3단계: 긴 자막 분할
    entries, changes = _split_long(entries)
    all_changes.extend(changes)

    # 4단계: 줄바꿈 최적화
    entries, changes = _fix_line_breaks(entries)
    all_changes.extend(changes)

    # 인덱스 재정렬
    entries = _reindex(entries)

    logger.info(
        "자막 리듬 최적화 완료: %d → %d항목, %d건 변경",
        original_count, len(entries), len(all_changes),
    )

    return OptimizedSrt(
        entries=entries,
        changes_made=all_changes,
        original_count=original_count,
        optimized_count=len(entries),
    )


def text_to_cuts(transcript_edits: list[dict]) -> List[CutPoint]:
    """텍스트 편집 목록에서 컷 포인트 생성.

    Args:
        transcript_edits: 편집 항목 리스트.
            각 항목은 {"start": "HH:MM:SS", "end": "HH:MM:SS",
                       "action": "delete"|"shorten"|"rearranged",
                       "text": "원본 텍스트"} 형태.

    Returns:
        CutPoint 리스트.
    """
    cuts: List[CutPoint] = []

    for edit in transcript_edits:
        start = edit.get('start', '00:00:00')
        end = edit.get('end', '00:00:00')
        action = edit.get('action', 'delete')
        text = edit.get('text', '')

        # 간략 시간("HH:MM:SS") → SRT 형식("HH:MM:SS,000") 변환
        if ',' not in start and '.' not in start:
            start = start + ',000'
        if ',' not in end and '.' not in end:
            end = end + ',000'

        # action → reason 매핑 (입력 action을 CutPoint reason으로 변환)
        action_map = {
            'delete': 'deleted',
            'deleted': 'deleted',
            'shorten': 'shortened',
            'shortened': 'shortened',
            'rearranged': 'rearranged',
        }
        reason = action_map.get(action, 'deleted')
        cuts.append(CutPoint(
            start_time=start,
            end_time=end,
            reason=reason,
            original_text=text,
        ))

    logger.info("컷 포인트 %d개 생성", len(cuts))
    return cuts
