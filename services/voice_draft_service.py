"""음성 초안 정제 서비스 — 말투 정제 + 문단 구성"""
import re
from dataclasses import dataclass, field

from services.handsfree_capture_service import capture_speech, _STANDALONE_FILLERS


# 핵심 포인트 키워드
_KEY_POINT_KEYWORDS = [
    '중요한', '핵심', '결론', '요약하면', '정리하면',
    '반드시', '꼭', '기억해', '포인트', '주목',
    '특히', '무엇보다', '가장',
]

# 문단당 문장 수
_SENTENCES_PER_PARAGRAPH = 5


@dataclass
class RefinedDraft:
    """정제된 초안 결과"""
    title: str = ""
    body: str = ""
    paragraphs: list = field(default_factory=list)
    word_count: int = 0
    refinement_score: int = 0


def _extract_title(text: str) -> str:
    """첫 문장에서 제목 추출 (마크다운 기호 제거)"""
    if not text:
        return ""

    # 첫 문장 추출
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    if not sentences:
        return ""

    title = sentences[0].strip()

    # 마크다운 기호 제거 (#, *, _, `, ~, >, -, [, ])
    title = re.sub(r'^[#*>~\-]+\s*', '', title)
    title = re.sub(r'[*_`~\[\]]+', '', title)

    # 끝 구두점 제거
    title = title.rstrip('.!?。')

    # 너무 길면 잘라내기 (50자)
    if len(title) > 50:
        title = title[:50] + '...'

    return title


def _split_into_paragraphs(text: str) -> list:
    """텍스트를 문단으로 분리 (5문장씩)"""
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return []

    paragraphs = []
    for i in range(0, len(sentences), _SENTENCES_PER_PARAGRAPH):
        chunk = sentences[i:i + _SENTENCES_PER_PARAGRAPH]
        paragraphs.append(' '.join(chunk))

    return paragraphs


def _calculate_refinement_score(original: str, refined: str) -> int:
    """필러 제거율 기반 정제 점수 (0~100)

    원본에서 필러 단어가 차지하는 비율 대비 제거된 양을 계산.
    필러가 전혀 없으면 100, 필러가 많이 제거되면 높은 점수.
    """
    if not original or not original.strip():
        return 0

    original_words = original.split()
    if not original_words:
        return 0

    # 원본에서 필러 단어 수 세기
    filler_count = 0
    for word in original_words:
        clean_word = word.strip('.!?。,')
        if clean_word in _STANDALONE_FILLERS:
            filler_count += 1

    if filler_count == 0:
        # 필러가 없으면 기본 정제 완료
        return 100

    # 정제된 텍스트에서 남은 필러 수
    refined_words = refined.split() if refined else []
    remaining_fillers = 0
    for word in refined_words:
        clean_word = word.strip('.!?。,')
        if clean_word in _STANDALONE_FILLERS:
            remaining_fillers += 1

    removed = filler_count - remaining_fillers
    score = int((removed / filler_count) * 100) if filler_count > 0 else 100

    return max(0, min(100, score))


def refine_voice_draft(raw_speech: str) -> RefinedDraft:
    """말투 정제 + 문단 구성

    Args:
        raw_speech: 음성으로 입력된 원본 텍스트

    Returns:
        RefinedDraft: 정제된 초안
    """
    if not raw_speech or not raw_speech.strip():
        return RefinedDraft()

    # 1. handsfree_capture_service로 기본 정제
    captured = capture_speech(raw_speech)

    if not captured.text:
        return RefinedDraft(refinement_score=0)

    body = captured.text

    # 2. 제목 추출
    title = _extract_title(body)

    # 3. 문단 구성
    paragraphs = _split_into_paragraphs(body)

    # 4. 정제 점수 계산
    score = _calculate_refinement_score(raw_speech, body)

    words = body.split() if body else []

    return RefinedDraft(
        title=title,
        body=body,
        paragraphs=paragraphs,
        word_count=len(words),
        refinement_score=score,
    )


def extract_key_points(draft: RefinedDraft) -> list:
    """핵심 포인트 추출 — 키워드 포함 문장 반환

    Args:
        draft: RefinedDraft 객체

    Returns:
        키워드를 포함하는 문장 리스트
    """
    if not draft.body:
        return []

    sentences = re.split(r'(?<=[.!?。])\s+', draft.body)
    key_points = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        for keyword in _KEY_POINT_KEYWORDS:
            if keyword in sentence:
                key_points.append(sentence)
                break  # 하나의 키워드라도 매치하면 추가

    return key_points
