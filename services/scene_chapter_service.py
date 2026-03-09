"""장면 챕터 감지 서비스

자막 텍스트에서 장면 전환을 감지하여 챕터를 자동 분할한다.
AI 호출 없이 규칙 기반으로 동작한다.
"""
import re
from dataclasses import dataclass, field


@dataclass
class SceneChapter:
    """장면 챕터"""
    chapter_number: int
    start_time: str
    end_time: str
    title: str
    scene_type: str            # "intro" | "main" | "transition" | "outro"
    keywords: list


# 장면 전환 감지 키워드 (가중치 포함)
_TRANSITION_MARKERS = {
    # 도입부
    '안녕하세요': ('intro', 3),
    '반갑습니다': ('intro', 3),
    '오늘은': ('intro', 2),
    '시작하겠습니다': ('intro', 2),
    # 전환
    '다음으로': ('transition', 3),
    '이제': ('transition', 2),
    '그러면': ('transition', 2),
    '그럼': ('transition', 2),
    '한편': ('transition', 2),
    '또한': ('transition', 1),
    '자 그러면': ('transition', 3),
    '두번째': ('transition', 3),
    '세번째': ('transition', 3),
    '네번째': ('transition', 3),
    '첫번째': ('transition', 3),
    '마지막으로': ('transition', 3),
    # 마무리
    '마치겠습니다': ('outro', 3),
    '감사합니다': ('outro', 3),
    '다음 영상': ('outro', 2),
    '구독': ('outro', 2),
    '좋아요': ('outro', 2),
    '정리하면': ('outro', 2),
    '요약하면': ('outro', 2),
}

# 최소 챕터 길이 (초)
_MIN_CHAPTER_DURATION = 15


def detect_scene_chapters(
    transcript: str,
    max_chapters: int = 10,
) -> list:
    """자막에서 장면 전환 감지하여 챕터 분할

    Args:
        transcript: 자막 텍스트 (타임스탬프 포함/미포함 모두 지원)
        max_chapters: 최대 챕터 수 (기본 10)

    Returns:
        list[SceneChapter]: 챕터 목록 (시간순)
    """
    if not transcript or len(transcript.strip()) < 50:
        return []

    max_chapters = max(1, min(max_chapters, 30))

    # 자막 파싱 — 타임스탬프 포함 여부에 따라 분기
    segments = _parse_transcript(transcript)
    if not segments:
        return []

    # 장면 전환점 감지
    breakpoints = _detect_breakpoints(segments)

    # 전환점 기반 챕터 생성
    chapters = _build_chapters(segments, breakpoints, max_chapters)

    return chapters


def _parse_transcript(transcript: str) -> list:
    """자막을 세그먼트 리스트로 파싱

    Returns:
        [{"start_sec": int, "end_sec": int, "text": str}, ...]
    """
    # 타임스탬프 포함 자막 ([MM:SS] 텍스트)
    timed_pattern = re.findall(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+)', transcript)
    if timed_pattern:
        segments = []
        for i, (time_str, text) in enumerate(timed_pattern):
            start_sec = _parse_time(time_str)
            if i + 1 < len(timed_pattern):
                end_sec = _parse_time(timed_pattern[i + 1][0])
            else:
                end_sec = start_sec + 10
            segments.append({
                "start_sec": start_sec,
                "end_sec": end_sec,
                "text": text.strip(),
            })
        return segments

    # 타임스탬프 없는 일반 텍스트 — 문장 기반 분할
    sentences = re.split(r'(?<=[.!?。])\s+', transcript)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return []

    # 문장당 약 5초 추정
    sec_per_sentence = 5
    segments = []
    for i, sent in enumerate(sentences):
        segments.append({
            "start_sec": i * sec_per_sentence,
            "end_sec": (i + 1) * sec_per_sentence,
            "text": sent,
        })
    return segments


def _detect_breakpoints(segments: list) -> list:
    """장면 전환점 감지

    각 세그먼트를 분석하여 전환 점수를 계산하고,
    임계값 이상인 위치를 전환점으로 반환한다.

    Returns:
        [(segment_index, scene_type, score), ...]
    """
    breakpoints = []

    for i, seg in enumerate(segments):
        text = seg["text"]
        score = 0
        detected_type = "main"

        # 전환 키워드 매칭
        for marker, (scene_type, weight) in _TRANSITION_MARKERS.items():
            if marker in text:
                score += weight
                detected_type = scene_type

        # 문장 시작 패턴 (새 주제) — 추가 점수
        if re.match(r'^(그래서|결론적으로|요약하면|정리하면)', text):
            score += 2
            detected_type = "transition"

        # 번호 패턴 (목록형 콘텐츠: "1.", "2)", "#1" 등)
        if re.match(r'^[\d#]+[.):\s]', text):
            score += 2
            detected_type = "main"

        if score >= 2:
            breakpoints.append((i, detected_type, score))

    return breakpoints


def _build_chapters(
    segments: list,
    breakpoints: list,
    max_chapters: int,
) -> list:
    """전환점 기반으로 챕터 구성

    전환점이 너무 많으면 점수 높은 순으로 선별한다.
    """
    if not breakpoints:
        # 전환점이 없으면 균등 분할
        return _build_even_chapters(segments, max_chapters)

    # 점수 기반 정렬 후 상위 max_chapters개 선택
    sorted_bp = sorted(breakpoints, key=lambda x: x[2], reverse=True)
    selected = sorted_bp[:max_chapters]
    # 시간순 재정렬
    selected.sort(key=lambda x: x[0])

    # 챕터 경계 구성
    boundaries = [0]  # 시작
    for idx, scene_type, score in selected:
        if idx > boundaries[-1]:
            boundaries.append(idx)
    # 마지막 세그먼트까지 포함
    if boundaries[-1] < len(segments) - 1:
        boundaries.append(len(segments))

    # 챕터 생성
    chapters = []
    for i in range(len(boundaries) - 1):
        start_idx = boundaries[i]
        end_idx = boundaries[i + 1] - 1
        if end_idx < start_idx:
            end_idx = start_idx

        start_sec = segments[start_idx]["start_sec"]
        end_sec = segments[end_idx]["end_sec"]

        # 너무 짧은 챕터는 건너뛰기
        if end_sec - start_sec < _MIN_CHAPTER_DURATION and len(chapters) > 0:
            # 이전 챕터에 병합
            chapters[-1].end_time = _format_seconds(end_sec)
            continue

        # 장면 유형 결정
        scene_type = _determine_scene_type(i, len(boundaries) - 1, selected, start_idx)

        # 챕터 텍스트 수집
        chapter_texts = [segments[j]["text"] for j in range(start_idx, min(end_idx + 1, len(segments)))]
        combined_text = " ".join(chapter_texts)

        # 제목 생성
        title = _generate_chapter_title(combined_text, i + 1, scene_type)

        # 키워드 추출
        keywords = _extract_keywords(combined_text)

        chapters.append(SceneChapter(
            chapter_number=i + 1,
            start_time=_format_seconds(start_sec),
            end_time=_format_seconds(end_sec),
            title=title,
            scene_type=scene_type,
            keywords=keywords,
        ))

    # 챕터 번호 재정렬
    for i, ch in enumerate(chapters):
        ch.chapter_number = i + 1

    return chapters


def _build_even_chapters(segments: list, max_chapters: int) -> list:
    """전환점이 없을 때 균등 분할"""
    total_segments = len(segments)
    chapter_count = min(max_chapters, max(1, total_segments // 5))

    if chapter_count <= 1:
        combined = " ".join(s["text"] for s in segments)
        return [SceneChapter(
            chapter_number=1,
            start_time=_format_seconds(segments[0]["start_sec"]),
            end_time=_format_seconds(segments[-1]["end_sec"]),
            title=_generate_chapter_title(combined, 1, "main"),
            scene_type="main",
            keywords=_extract_keywords(combined),
        )]

    chunk_size = max(1, total_segments // chapter_count)
    chapters = []

    for i in range(chapter_count):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size - 1, total_segments - 1)
        if i == chapter_count - 1:
            end_idx = total_segments - 1

        chapter_texts = [segments[j]["text"] for j in range(start_idx, end_idx + 1)]
        combined = " ".join(chapter_texts)

        # 첫 챕터는 intro, 마지막은 outro
        if i == 0:
            scene_type = "intro"
        elif i == chapter_count - 1:
            scene_type = "outro"
        else:
            scene_type = "main"

        chapters.append(SceneChapter(
            chapter_number=i + 1,
            start_time=_format_seconds(segments[start_idx]["start_sec"]),
            end_time=_format_seconds(segments[end_idx]["end_sec"]),
            title=_generate_chapter_title(combined, i + 1, scene_type),
            scene_type=scene_type,
            keywords=_extract_keywords(combined),
        ))

    return chapters


def _determine_scene_type(
    chapter_idx: int,
    total_chapters: int,
    breakpoints: list,
    start_segment_idx: int,
) -> str:
    """챕터의 장면 유형 결정"""
    if chapter_idx == 0:
        return "intro"
    if chapter_idx == total_chapters - 1:
        return "outro"

    # 전환점 정보에서 유형 탐색
    for bp_idx, scene_type, _ in breakpoints:
        if bp_idx == start_segment_idx:
            if scene_type in ("intro", "outro", "transition"):
                return scene_type
            return "main"

    return "main"


def _generate_chapter_title(text: str, number: int, scene_type: str) -> str:
    """챕터 제목 생성 (규칙 기반)

    텍스트의 첫 문장 또는 핵심 구절을 제목으로 사용한다.
    """
    if scene_type == "intro":
        return "도입"
    if scene_type == "outro":
        return "마무리"

    # 첫 문장에서 제목 추출
    first_sentence = re.split(r'[.!?。]', text)[0].strip()
    if len(first_sentence) > 30:
        first_sentence = first_sentence[:30] + "…"

    if not first_sentence:
        return f"챕터 {number}"

    return first_sentence


def _extract_keywords(text: str) -> list:
    """텍스트에서 핵심 키워드 추출 (빈도 기반)"""
    # 불용어
    stopwords = {
        '이', '그', '저', '을', '를', '에', '의', '는', '은', '가',
        '와', '과', '도', '로', '으로', '에서', '까지', '부터', '에게',
        '한다', '있다', '없다', '된다', '하는', '있는', '없는', '되는',
        '것', '수', '때', '중', '더', '잘', '매우', '아주', '다',
    }

    # 한글 단어 추출 (2자 이상)
    words = re.findall(r'[가-힣]{2,}', text)
    filtered = [w for w in words if w not in stopwords]

    # 빈도 기반 정렬
    freq = {}
    for w in filtered:
        freq[w] = freq.get(w, 0) + 1
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)

    return [w for w, _ in sorted_words[:5]]


def _parse_time(time_str: str) -> int:
    """시간 문자열을 초 단위로 변환"""
    parts = time_str.split(':')
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    return 0


def _format_seconds(seconds: int) -> str:
    """초를 MM:SS 형식으로 변환"""
    m = seconds // 60
    s = seconds % 60
    return f"{m}:{s:02d}"
