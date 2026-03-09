"""
답변 마커 서비스

자막(transcript)에서 Q&A 구간을 감지하고, 답변 부분을
40~60 단어 블록으로 마킹합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass
from typing import List


@dataclass
class AnswerMoment:
    """Q&A 구간 마커"""
    question: str            # 감지된 질문 텍스트
    answer: str              # 답변 텍스트 (40~60 단어 블록)
    start_position: int      # 답변 시작 위치 (문자 인덱스)
    word_count: int           # 답변 단어 수
    confidence: float         # 감지 신뢰도 (0~100)


# ── 질문 감지 패턴 (한국어) ──

_QUESTION_PATTERNS_KO = [
    # "~무엇인가요?", "~뭔가요?"
    re.compile(r'[^\n.!?]*(?:무엇|뭐|뭘|어떤|어떻게|왜|언제|어디|누가|몇)\s*[^\n.!?]*[?？]'),
    # "~인가요?", "~한가요?", "~일까요?"
    re.compile(r'[^\n.!?]*(?:인가요|한가요|일까요|인지|할까요|해야\s*할까요|나요)[?？]'),
    # "Q:", "질문:", "Q."
    re.compile(r'(?:^|\n)\s*(?:Q[.:]\s*|질문[.:]\s*)(.+?)(?:\n|$)', re.MULTILINE),
    # "~은/는 ~입니까?"
    re.compile(r'[^\n.!?]*(?:입니까|습니까|인가|인지)[?？]'),
    # 의문형 어미로 끝나는 문장
    re.compile(r'[^\n.!?]*(?:할까|될까|있을까|없을까|건가|건지|을까|ㄹ까)[?？]?'),
]

# ── 질문 감지 패턴 (영어) ──

_QUESTION_PATTERNS_EN = [
    # 의문사로 시작하는 문장 + ?
    re.compile(
        r'(?:^|\n)\s*(?:What|How|Why|When|Where|Who|Which|Can|Could|Should|'
        r'Is|Are|Do|Does|Did|Will|Would)\s+[^\n?]*\?',
        re.IGNORECASE | re.MULTILINE,
    ),
    # "Q:" 형식
    re.compile(r'(?:^|\n)\s*Q[.:]\s*(.+?)(?:\n|$)', re.MULTILINE | re.IGNORECASE),
]

# ── 답변 시작 패턴 ──

_ANSWER_START_KO = [
    re.compile(r'(?:^|\n)\s*(?:A[.:]\s*|답변[.:]\s*|답[.:]\s*)', re.MULTILINE),
    re.compile(r'(?:네,?\s*|예,?\s*|아니요,?\s*)'),
    re.compile(r'(?:결론|답|정답|핵심)(?:은|는|이|부터)\s'),
    re.compile(r'(?:간단히|쉽게|한마디로)\s*(?:말하면|설명하면|말씀드리면)'),
]

_ANSWER_START_EN = [
    re.compile(r'(?:^|\n)\s*A[.:]\s*', re.MULTILINE | re.IGNORECASE),
    re.compile(r'\b(?:The answer is|In short|Simply put|Basically|Well,)\b', re.IGNORECASE),
    re.compile(r'\b(?:Yes,?|No,?)\s', re.IGNORECASE),
]


def _count_words_mixed(text: str) -> int:
    """한국어+영어 혼합 단어 수 계산.

    영어: 공백 기준 단어 수
    한국어: 글자 2개 = 약 1단어로 환산
    """
    en_words = len(re.findall(r'[a-zA-Z]+(?:\'[a-zA-Z]+)?', text))
    ko_chars = len(re.findall(r'[가-힣]', text))
    return en_words + (ko_chars + 1) // 2


def _extract_words_block(text: str, start: int, target_min: int = 40, target_max: int = 60) -> tuple:
    """시작 위치부터 target_min~target_max 단어 블록을 추출합니다.

    Args:
        text: 전체 텍스트
        start: 시작 문자 위치
        target_min: 최소 단어 수
        target_max: 최대 단어 수

    Returns:
        (block_text, word_count, actual_start)
    """
    remaining = text[start:]
    if not remaining.strip():
        return '', 0, start

    # 문장 단위로 분리 (마침표/물음표/느낌표/줄바꿈)
    sentences = re.split(r'(?<=[.!?。])\s+|\n{2,}', remaining)
    sentences = [s.strip() for s in sentences if s.strip()]

    block_parts = []
    total_words = 0

    for sent in sentences:
        sent_words = _count_words_mixed(sent)
        if total_words + sent_words > target_max and total_words >= target_min:
            break
        block_parts.append(sent)
        total_words += sent_words
        if total_words >= target_min:
            break

    # 최소치에 못 미치면 가능한 만큼 포함
    if not block_parts and sentences:
        block_parts = [sentences[0]]
        total_words = _count_words_mixed(sentences[0])

    block_text = ' '.join(block_parts)
    return block_text, total_words, start


def _find_answer_start(text: str, question_end: int) -> int:
    """질문 끝 위치 이후에서 답변 시작 위치를 찾습니다."""
    search_region = text[question_end:question_end + 500]

    # 명시적 답변 마커 검색
    for patterns in [_ANSWER_START_KO, _ANSWER_START_EN]:
        for p in patterns:
            m = p.search(search_region)
            if m:
                return question_end + m.end()

    # 마커 없으면 질문 바로 다음 줄의 시작
    next_line = re.search(r'\n\s*\S', search_region)
    if next_line:
        return question_end + next_line.start() + 1

    # 그마저도 없으면 질문 끝 바로 뒤
    return question_end


def _compute_confidence(
    question: str,
    answer: str,
    has_explicit_marker: bool,
    word_count: int,
) -> float:
    """Q&A 감지 신뢰도를 계산합니다 (0~100).

    Args:
        question: 감지된 질문 텍스트
        answer: 추출된 답변 텍스트
        has_explicit_marker: Q:/A: 같은 명시적 마커 존재 여부
        word_count: 답변 단어 수
    """
    score = 50.0  # 기본 점수

    # 명시적 마커 → 높은 신뢰도
    if has_explicit_marker:
        score += 30.0

    # 물음표 존재
    if '?' in question or '？' in question:
        score += 10.0

    # 답변 분량이 적정 범위 (40~60)
    if 40 <= word_count <= 60:
        score += 10.0
    elif 20 <= word_count < 40 or 60 < word_count <= 80:
        score += 5.0

    return max(0.0, min(100.0, round(score, 1)))


def mark_answer_moments(transcript: str) -> List[AnswerMoment]:
    """자막에서 Q&A 구간을 감지하고 40~60 단어 블록으로 마킹합니다.

    Args:
        transcript: 자막/콘텐츠 텍스트

    Returns:
        감지된 AnswerMoment 목록 (start_position 오름차순)
    """
    if not transcript or not transcript.strip():
        return []

    moments: List[AnswerMoment] = []
    seen_positions = set()  # 중복 방지

    all_patterns = _QUESTION_PATTERNS_KO + _QUESTION_PATTERNS_EN

    for pattern in all_patterns:
        for match in pattern.finditer(transcript):
            question_text = match.group().strip()
            question_end = match.end()

            # 너무 짧은 질문 무시 (5자 미만)
            if len(question_text) < 5:
                continue

            # 답변 시작 위치 찾기
            answer_start = _find_answer_start(transcript, question_end)

            # 이미 처리한 근접 위치 (±50자) 건너뛰기
            if any(abs(answer_start - p) < 50 for p in seen_positions):
                continue

            # 답변 블록 추출 (40~60 단어)
            block_text, word_count, actual_start = _extract_words_block(
                transcript, answer_start,
            )

            if not block_text or word_count < 5:
                continue

            # 명시적 마커 여부 체크
            between = transcript[question_end:answer_start]
            has_marker = bool(
                re.search(r'A[.:]|답변[.:]|답[.:]', between, re.IGNORECASE)
            )

            confidence = _compute_confidence(
                question_text, block_text, has_marker, word_count,
            )

            seen_positions.add(actual_start)
            moments.append(AnswerMoment(
                question=question_text,
                answer=block_text,
                start_position=actual_start,
                word_count=word_count,
                confidence=confidence,
            ))

    # position 기준 정렬
    moments.sort(key=lambda m: m.start_position)
    return moments
