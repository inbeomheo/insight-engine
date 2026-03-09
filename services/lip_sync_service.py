"""
재더빙 립싱크 서비스 — 오디오-비주얼 동기화 메타데이터
"""

import uuid
from dataclasses import dataclass, field


@dataclass
class LipSyncSegment:
    """립싱크 세그먼트"""
    segment_id: str
    start_time: float
    end_time: float
    phonemes: list[str]
    mouth_shapes: list[str]
    text: str


@dataclass
class LipSyncTrack:
    """립싱크 트랙"""
    track_id: str
    language: str
    segments: list[LipSyncSegment]
    total_duration: float


# 한국어 자음/모음 분해 테이블
_KO_INITIALS = list('ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ')
_KO_MEDIALS = list('ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ')
_KO_FINALS = [''] + list('ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ')

# 입모양 매핑
_MOUTH_MAP = {
    'ㅏ': 'A', 'ㅐ': 'E', 'ㅑ': 'A', 'ㅒ': 'E',
    'ㅓ': 'O', 'ㅔ': 'E', 'ㅕ': 'O', 'ㅖ': 'E',
    'ㅗ': 'O', 'ㅘ': 'A', 'ㅙ': 'E', 'ㅚ': 'O',
    'ㅛ': 'O', 'ㅜ': 'U', 'ㅝ': 'O', 'ㅞ': 'E',
    'ㅟ': 'U', 'ㅠ': 'U', 'ㅡ': 'U', 'ㅢ': 'I', 'ㅣ': 'I',
    'a': 'A', 'e': 'E', 'i': 'I', 'o': 'O', 'u': 'U',
    'A': 'A', 'E': 'E', 'I': 'I', 'O': 'O', 'U': 'U',
}


def generate_phonemes(text: str, language: str = 'ko') -> list[str]:
    """텍스트 → 음소 변환"""
    phonemes = []

    if language == 'ko':
        for char in text:
            code = ord(char)
            if 0xAC00 <= code <= 0xD7A3:
                # 한글 음절 분해
                offset = code - 0xAC00
                initial = offset // (21 * 28)
                medial = (offset % (21 * 28)) // 28
                final = offset % 28
                phonemes.append(_KO_INITIALS[initial])
                phonemes.append(_KO_MEDIALS[medial])
                if final > 0:
                    phonemes.append(_KO_FINALS[final])
            elif char.strip():
                phonemes.append(char)
    else:
        # 영어: 단순 규칙 (모음/자음 분리)
        vowels = set('aeiouAEIOU')
        for char in text:
            if char.isalpha():
                phonemes.append(char.lower())
            elif char == ' ':
                phonemes.append('_')

    return phonemes


def map_mouth_shapes(phonemes: list[str]) -> list[str]:
    """음소 → 입모양 매핑"""
    shapes = []
    for p in phonemes:
        shape = _MOUTH_MAP.get(p, 'etc')
        shapes.append(shape)
    return shapes


def create_track(text: str, language: str, duration: float) -> LipSyncTrack:
    """립싱크 트랙 생성"""
    # 문장 단위로 세그먼트 분할
    sentences = [s.strip() for s in text.replace('!', '.').replace('?', '.').split('.') if s.strip()]

    if not sentences:
        return LipSyncTrack(
            track_id=str(uuid.uuid4())[:8],
            language=language,
            segments=[],
            total_duration=duration
        )

    segment_duration = duration / len(sentences)
    segments = []

    for i, sentence in enumerate(sentences):
        phonemes = generate_phonemes(sentence, language)
        shapes = map_mouth_shapes(phonemes)
        seg = LipSyncSegment(
            segment_id=str(uuid.uuid4())[:8],
            start_time=round(i * segment_duration, 3),
            end_time=round((i + 1) * segment_duration, 3),
            phonemes=phonemes,
            mouth_shapes=shapes,
            text=sentence
        )
        segments.append(seg)

    return LipSyncTrack(
        track_id=str(uuid.uuid4())[:8],
        language=language,
        segments=segments,
        total_duration=duration
    )


def validate_sync(track: LipSyncTrack) -> list[str]:
    """동기화 검증 — 겹침, 공백"""
    errors = []
    sorted_segs = sorted(track.segments, key=lambda s: s.start_time)

    for i in range(len(sorted_segs) - 1):
        current = sorted_segs[i]
        next_seg = sorted_segs[i + 1]

        if current.end_time > next_seg.start_time:
            errors.append(f"세그먼트 겹침: {current.segment_id} (끝: {current.end_time}) ↔ {next_seg.segment_id} (시작: {next_seg.start_time})")

        gap = next_seg.start_time - current.end_time
        if gap > 1.0:
            errors.append(f"세그먼트 공백: {current.segment_id} ~ {next_seg.segment_id} ({gap:.3f}초)")

    for seg in track.segments:
        if seg.end_time > track.total_duration:
            errors.append(f"세그먼트가 트랙 길이 초과: {seg.segment_id} (끝: {seg.end_time}, 트랙: {track.total_duration})")

    return errors
