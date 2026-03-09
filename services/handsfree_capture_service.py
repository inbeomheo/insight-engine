"""핸즈프리 음성 캡처 서비스 — 말을 정돈된 텍스트로 변환"""
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


# 한국어 필러 패턴 (말버릇)
_FILLER_PATTERNS = [
    r'\b음+\b', r'\b그+\b', r'\b어+\b', r'\b아+\b',
    r'\b이제\b', r'\b뭐랄까\b', r'\b그러니까\b', r'\b있잖아\b',
    r'\b말하자면\b', r'\b그래서\b(?=\s*그래서)', r'\b근데\b(?=\s*근데)',
    r'\b약간\b(?=\s*약간)', r'\b좀\b(?=\s*좀)',
    r'\b에\b(?=\s*에\b)', r'\b뭐\b(?=\s*뭐\b)',
]

# 독립적으로 제거할 필러 (문장 시작/끝에서)
_STANDALONE_FILLERS = [
    '음', '그', '어', '아', '이제', '뭐랄까', '있잖아', '말하자면',
]


@dataclass
class CapturedText:
    """캡처된 텍스트 결과"""
    text: str = ""
    word_count: int = 0
    sentence_count: int = 0
    cleaned_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    original_length: int = 0


def _remove_fillers(text: str) -> str:
    """필러(말버릇) 패턴 제거"""
    result = text
    for pattern in _FILLER_PATTERNS:
        result = re.sub(pattern, '', result)
    return result


def _remove_repeated_words(text: str) -> str:
    """연속 반복 단어 제거 (예: '정말 정말 정말' → '정말')"""
    return re.sub(r'\b(\w+)(?:\s+\1){1,}\b', r'\1', text)


def _normalize_whitespace(text: str) -> str:
    """연속 공백을 단일 공백으로, 양끝 정리"""
    return re.sub(r'\s+', ' ', text).strip()


def _ensure_sentence_ending(text: str) -> str:
    """문장 끝에 마침표가 없으면 추가"""
    if not text:
        return text
    # 마지막 문자가 구두점이 아니면 마침표 추가
    if text[-1] not in '.!?。':
        text += '.'
    return text


def _split_sentences(text: str) -> list:
    """텍스트를 문장 단위로 분리"""
    # 마침표, 물음표, 느낌표 기준 분리
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _clean_standalone_fillers(text: str) -> str:
    """문장 시작/끝의 독립 필러 제거"""
    words = text.split()
    if not words:
        return text

    # 문장 시작 필러 제거
    while words and words[0] in _STANDALONE_FILLERS:
        words.pop(0)

    # 문장 끝 필러 제거 (구두점 앞)
    while len(words) > 1:
        last = words[-1].rstrip('.!?。')
        if last in _STANDALONE_FILLERS:
            # 구두점 보존
            punct = words[-1][len(last):]
            words.pop()
            if punct and words:
                words[-1] = words[-1] + punct
        else:
            break

    return ' '.join(words)


def capture_speech(raw_text: str) -> CapturedText:
    """말을 정돈된 텍스트로 변환

    Args:
        raw_text: 음성 인식 또는 직접 입력된 원본 텍스트

    Returns:
        CapturedText: 정돈된 텍스트와 메타데이터
    """
    if not raw_text or not raw_text.strip():
        return CapturedText(original_length=len(raw_text) if raw_text else 0)

    original_length = len(raw_text)

    # 1. 필러 제거
    cleaned = _remove_fillers(raw_text)

    # 2. 반복 단어 제거
    cleaned = _remove_repeated_words(cleaned)

    # 3. 공백 정리
    cleaned = _normalize_whitespace(cleaned)

    # 4. 문장 분리 후 각 문장 정리
    sentences = _split_sentences(cleaned)
    refined_sentences = []
    for s in sentences:
        s = _clean_standalone_fillers(s)
        s = _normalize_whitespace(s)
        if s:
            s = _ensure_sentence_ending(s)
            refined_sentences.append(s)

    # 문장이 없으면 전체를 하나의 문장으로 처리
    if not refined_sentences and cleaned:
        cleaned = _clean_standalone_fillers(cleaned)
        cleaned = _normalize_whitespace(cleaned)
        if cleaned:
            cleaned = _ensure_sentence_ending(cleaned)
            refined_sentences = [cleaned]

    final_text = ' '.join(refined_sentences)
    words = final_text.split() if final_text else []

    return CapturedText(
        text=final_text,
        word_count=len(words),
        sentence_count=len(refined_sentences),
        original_length=original_length,
    )


def merge_captures(captures: list) -> CapturedText:
    """여러 캡처 결과를 하나로 병합

    Args:
        captures: CapturedText 객체 리스트

    Returns:
        CapturedText: 병합된 결과
    """
    if not captures:
        return CapturedText()

    texts = [c.text for c in captures if c.text]
    merged_text = ' '.join(texts)
    total_original = sum(c.original_length for c in captures)

    if not merged_text:
        return CapturedText(original_length=total_original)

    # 병합 후 다시 정리
    merged_text = _normalize_whitespace(merged_text)
    sentences = _split_sentences(merged_text)
    words = merged_text.split() if merged_text else []

    return CapturedText(
        text=merged_text,
        word_count=len(words),
        sentence_count=len(sentences),
        original_length=total_original,
    )
