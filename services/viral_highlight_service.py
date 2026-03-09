"""바이럴 하이라이트 + 키워드 클립 추출 서비스

자막 구간별 바이럴 가능성을 점수화하고,
키워드 기반으로 관련 클립을 추출합니다.
"""
import re
import math
from dataclasses import dataclass, field


# ──────────────────────────────────────────
# 데이터 클래스
# ──────────────────────────────────────────

@dataclass
class HighlightScore:
    """구간별 바이럴 점수"""
    start_time: str          # "MM:SS"
    end_time: str
    text: str
    hook_score: float        # 0~100 (훅 강도)
    emotion_score: float     # 0~100 (감정 밀도)
    info_density: float      # 0~100 (정보 밀도)
    total_score: float       # 가중 합계 0~100
    viral_potential: str     # "low" | "medium" | "high"


@dataclass
class Clip:
    """키워드 매칭 클립"""
    start_time: str
    end_time: str
    text: str
    matched_keywords: list = field(default_factory=list)
    speaker: str | None = None


# ──────────────────────────────────────────
# 내부 상수 — 훅/감정/정보 밀도 판별 패턴
# ──────────────────────────────────────────

# 훅 강도 판별: 질문형, 감탄형, 긴급 표현, 숫자 강조
_HOOK_PATTERNS = [
    (re.compile(r'[?？]'), 15),                              # 질문형
    (re.compile(r'[!！]{1,}'), 10),                          # 감탄형
    (re.compile(r'(지금|당장|바로|즉시|빨리|급히)'), 12),       # 긴급 표현
    (re.compile(r'(충격|대박|실화|레전드|미쳤|헐|ㄷㄷ)'), 15),  # 자극 표현
    (re.compile(r'(비밀|몰랐|아무도|절대|반드시)'), 10),       # 호기심 유발
    (re.compile(r'\d+[%만억천원배]'), 8),                     # 숫자 강조 (100%, 3만원 등)
    (re.compile(r'(꿀팁|핵심|요약|결론|정리)'), 10),           # 핵심 표현
    (re.compile(r'(처음|최초|유일|세계|역대)'), 8),            # 희소성 표현
]

# 감정 밀도 판별: 긍정/부정/강조 어휘
_EMOTION_WORDS = re.compile(
    r'(좋아|싫어|최고|최악|놀라|감동|화나|슬프|기쁘|행복|'
    r'대단|끔찍|무서|짜증|신기|웃기|황당|감사|사랑|미안|'
    r'후회|자랑|부러|설레|두렵|답답|속상|뿌듯|아깝|한심|'
    r'ㅋㅋ|ㅎㅎ|ㅠㅠ|ㅜㅜ|ㄲㄲ|ㅉㅉ|'
    r'정말|진짜|너무|완전|엄청|매우|굉장히)'
)

# 정보 밀도 판별: 숫자, 고유명사 패턴, 전문용어 지표
_NUMBER_PATTERN = re.compile(r'\d+\.?\d*')
_PROPER_NOUN_INDICATORS = re.compile(
    r'[A-Z][a-zA-Z]{2,}|'       # 영문 고유명사 (대문자 시작)
    r'[가-힣]+(?:은행|대학|회사|그룹|센터|연구소|협회|재단)'  # 한국어 기관명
)


# ──────────────────────────────────────────
# 타임스탬프 유틸리티
# ──────────────────────────────────────────

def _parse_timestamp(ts: str) -> int:
    """MM:SS 또는 HH:MM:SS → 초 단위 정수 변환"""
    parts = ts.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _format_timestamp(seconds: int) -> str:
    """초 → MM:SS 형식 문자열 변환"""
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


# ──────────────────────────────────────────
# 자막 자동 분할
# ──────────────────────────────────────────

_TIMESTAMP_LINE = re.compile(r'^\[?(\d{1,2}:\d{2}(?::\d{2})?)\]?\s*(.*)')

def _auto_segment(transcript: str, chunk_seconds: int = 30) -> list[dict]:
    """타임스탬프 없는 자막을 고정 구간으로 분할.

    자막에 [MM:SS] 패턴이 있으면 파싱, 없으면 문장 단위로 균등 분할.
    """
    lines = [l for l in transcript.strip().split('\n') if l.strip()]
    if not lines:
        return []

    # 타임스탬프가 포함된 라인이 있는지 확인
    timestamped = []
    for line in lines:
        m = _TIMESTAMP_LINE.match(line.strip())
        if m:
            timestamped.append({
                'start': _format_timestamp(_parse_timestamp(m.group(1))),
                'text': m.group(2).strip(),
            })

    # 타임스탬프 라인이 전체의 30% 이상이면 파싱 결과 사용
    if len(timestamped) >= len(lines) * 0.3 and timestamped:
        segments = []
        for i, item in enumerate(timestamped):
            start_sec = _parse_timestamp(item['start'])
            if i + 1 < len(timestamped):
                end_sec = _parse_timestamp(timestamped[i + 1]['start'])
            else:
                # 마지막 세그먼트: 텍스트 길이 기반 추정 (약 3초/문장)
                end_sec = start_sec + max(10, len(item['text']) // 10 * 3)
            segments.append({
                'start': _format_timestamp(start_sec),
                'end': _format_timestamp(end_sec),
                'text': item['text'],
            })
        return segments

    # 타임스탬프 없음: 문장 단위 균등 분할
    full_text = ' '.join(line.strip() for line in lines if line.strip())
    # 문장 분리 (마침표/물음표/느낌표 기준)
    sentences = re.split(r'(?<=[.?!。？！])\s*', full_text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [{
            'start': '00:00',
            'end': _format_timestamp(chunk_seconds),
            'text': full_text,
        }]

    # 문장들을 chunk_seconds 단위 그룹으로 묶기
    # 전체 길이에서 문장당 예상 시간 계산
    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return []

    segments = []
    current_text = []
    current_start = 0

    for sentence in sentences:
        current_text.append(sentence)
        accumulated_chars = sum(len(s) for s in current_text)
        # 예상 시간 = (누적 글자 / 전체 글자) * (총 문장수 * chunk_seconds / 문장수)
        estimated_duration = (accumulated_chars / total_chars) * len(sentences) * (chunk_seconds / max(len(sentences), 1)) * len(sentences)

        if estimated_duration >= chunk_seconds or sentence == sentences[-1]:
            end_time = current_start + chunk_seconds
            segments.append({
                'start': _format_timestamp(current_start),
                'end': _format_timestamp(end_time),
                'text': ' '.join(current_text),
            })
            current_start = end_time
            current_text = []

    return segments


# ──────────────────────────────────────────
# 점수 계산 함수
# ──────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """값을 [lo, hi] 범위로 제한"""
    return max(lo, min(hi, value))


def _calc_hook_score(text: str) -> float:
    """훅 강도 점수 (0~100). 자극적/호기심 유발 표현 기반."""
    score = 0.0
    for pattern, weight in _HOOK_PATTERNS:
        matches = pattern.findall(text)
        # 패턴당 최대 3회까지 가산 (중복 감쇠)
        count = min(len(matches), 3)
        score += weight * count

    # 짧은 문장에 질문이 들어있으면 훅 보너스
    if len(text) < 50 and re.search(r'[?？]', text):
        score += 10

    return _clamp(score)


def _calc_emotion_score(text: str) -> float:
    """감정 밀도 점수 (0~100). 감정 어휘 출현 빈도 기반."""
    if not text:
        return 0.0

    matches = _EMOTION_WORDS.findall(text)
    # 글자 100자당 감정어 수로 정규화
    text_len = max(len(text), 1)
    density = len(matches) / text_len * 100

    # 밀도를 0~100 스케일로 매핑 (5% 이상이면 100)
    score = density * 20  # 5개/100자 = 100점
    return _clamp(score)


def _calc_info_density(text: str) -> float:
    """정보 밀도 점수 (0~100). 숫자/고유명사/전문용어 비율."""
    if not text:
        return 0.0

    text_len = max(len(text), 1)

    # 숫자 포함 비율
    numbers = _NUMBER_PATTERN.findall(text)
    number_score = min(len(numbers) * 15, 40)

    # 고유명사 지표
    proper_nouns = _PROPER_NOUN_INDICATORS.findall(text)
    proper_score = min(len(proper_nouns) * 12, 30)

    # 문장 길이 대비 고유 단어 비율 (어휘 다양성)
    words = text.split()
    if words:
        unique_ratio = len(set(words)) / len(words)
        diversity_score = unique_ratio * 30
    else:
        diversity_score = 0

    score = number_score + proper_score + diversity_score
    return _clamp(score)


def _determine_viral_potential(total_score: float) -> str:
    """총점 기반 바이럴 잠재력 등급 판별"""
    if total_score >= 60:
        return "high"
    elif total_score >= 30:
        return "medium"
    else:
        return "low"


# ──────────────────────────────────────────
# 공개 API
# ──────────────────────────────────────────

# 가중치: 훅 40%, 감정 30%, 정보 30%
_WEIGHT_HOOK = 0.4
_WEIGHT_EMOTION = 0.3
_WEIGHT_INFO = 0.3


def score_highlights(
    transcript: str,
    segments: list[dict] | None = None,
) -> list[HighlightScore]:
    """자막 구간별 바이럴 가능성 점수를 계산합니다.

    Args:
        transcript: 전체 자막 텍스트
        segments: 구간 정보 리스트. None이면 자동 분할.
            [{"start": "00:00", "end": "01:30", "text": "..."}]

    Returns:
        HighlightScore 리스트 (total_score 내림차순 정렬)
    """
    if not transcript or not transcript.strip():
        return []

    # 세그먼트가 없으면 자동 분할
    if segments is None:
        segments = _auto_segment(transcript)

    if not segments:
        return []

    results = []
    for seg in segments:
        text = seg.get('text', '')
        if not text.strip():
            continue

        start_time = seg.get('start', '00:00')
        end_time = seg.get('end', '00:00')

        hook = _calc_hook_score(text)
        emotion = _calc_emotion_score(text)
        info = _calc_info_density(text)

        total = _clamp(
            hook * _WEIGHT_HOOK + emotion * _WEIGHT_EMOTION + info * _WEIGHT_INFO
        )
        # 소수점 첫째 자리 반올림
        total = round(total, 1)
        hook = round(hook, 1)
        emotion = round(emotion, 1)
        info = round(info, 1)

        viral_potential = _determine_viral_potential(total)

        results.append(HighlightScore(
            start_time=start_time,
            end_time=end_time,
            text=text,
            hook_score=hook,
            emotion_score=emotion,
            info_density=info,
            total_score=total,
            viral_potential=viral_potential,
        ))

    # total_score 내림차순 정렬
    results.sort(key=lambda h: h.total_score, reverse=True)
    return results


def extract_keyword_clips(
    transcript: str,
    keywords: list[str],
    speaker: str | None = None,
) -> list[Clip]:
    """키워드 매칭 클립을 추출합니다.

    Args:
        transcript: 전체 자막 텍스트
        keywords: 검색 키워드 리스트
        speaker: 화자 필터 (None이면 전체)

    Returns:
        매칭된 Clip 리스트 (시작 시간순 정렬)
    """
    if not transcript or not transcript.strip():
        return []
    if not keywords:
        return []

    # 유효한 키워드만 필터링 (빈 문자열 제거)
    valid_keywords = [kw.strip() for kw in keywords if kw.strip()]
    if not valid_keywords:
        return []

    # 자막을 세그먼트로 분할
    segments = _auto_segment(transcript)
    if not segments:
        return []

    # 키워드별 정규식 패턴 (대소문자 무시)
    patterns = []
    for kw in valid_keywords:
        try:
            patterns.append((kw, re.compile(re.escape(kw), re.IGNORECASE)))
        except re.error:
            continue

    clips = []
    for seg in segments:
        text = seg.get('text', '')
        if not text.strip():
            continue

        # 화자 필터 적용
        seg_speaker = seg.get('speaker')
        if speaker is not None and seg_speaker != speaker:
            continue

        # 키워드 매칭
        matched = []
        for kw, pattern in patterns:
            if pattern.search(text):
                matched.append(kw)

        if matched:
            clips.append(Clip(
                start_time=seg.get('start', '00:00'),
                end_time=seg.get('end', '00:00'),
                text=text,
                matched_keywords=matched,
                speaker=seg_speaker,
            ))

    # 시작 시간순 정렬
    clips.sort(key=lambda c: _parse_timestamp(c.start_time))
    return clips
