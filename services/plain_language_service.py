"""
쉬운말 변환 서비스

콘텐츠의 가독성을 측정하고, 독해 수준에 맞춰
긴 문장 분리 + 한자어/전문용어를 쉬운 대체어로 변환합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class ReadabilityScore:
    """가독성 평가 결과."""
    score: float                       # 0~100 (높을수록 읽기 쉬움)
    level: str                         # easy / normal / hard
    avg_sentence_length: float         # 평균 문장 길이 (글자 수)
    complex_word_ratio: float          # 복합어/전문어 비율 (0~1)
    suggestions: List[str] = field(default_factory=list)


# 한자어/전문용어 → 쉬운 대체어 매핑 (easy 레벨)
_EASY_REPLACEMENTS: List[Tuple[str, str]] = [
    ('활용', '사용'),
    ('수행', '하기'),
    ('구현', '만들기'),
    ('용이', '쉬운'),
    ('상기한', '위에서 말한'),
    ('하기와', '아래의'),
    ('제고', '높이기'),
    ('도모', '꾀하기'),
    ('여부', '인지 아닌지'),
    ('개선', '고치기'),
    ('수립', '세우기'),
    ('도출', '뽑아내기'),
    ('기여', '돕기'),
    ('촉진', '빠르게 하기'),
    ('유의', '주의'),
    ('필수적', '꼭 필요한'),
    ('효율적', '효과적인'),
    ('다양한', '여러 가지'),
    ('적극적', '열심히'),
    ('지속적', '꾸준한'),
    ('명시적', '분명한'),
    ('획기적', '새로운'),
    ('포괄적', '전체적인'),
    ('체계적', '차례대로'),
    ('즉각적', '바로'),
]

# 전문 용어 패턴 (복합어 감지용)
_COMPLEX_WORD_PATTERNS = [
    re.compile(r'[가-힣]+적(?:\s|$|으로|인)'),     # ~적, ~적으로, ~적인
    re.compile(r'[가-힣]+화(?:\s|$|를|가|의)'),     # ~화, ~화를
    re.compile(r'[가-힣]+성(?:\s|$|을|이|의)'),     # ~성, ~성을
]

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?。])\s+')
_CLAUSE_SPLIT = re.compile(r'[,;，；]\s*')


def _split_sentences(content: str) -> List[str]:
    """콘텐츠를 문장 단위로 분리합니다."""
    sentences = _SENTENCE_SPLIT.split(content.strip())
    return [s.strip() for s in sentences if s.strip()]


def _count_complex_words(sentence: str) -> int:
    """문장에서 복합어/전문어 수를 셉니다."""
    count = 0
    for pattern in _COMPLEX_WORD_PATTERNS:
        count += len(pattern.findall(sentence))
    # 대체어 매핑의 원본 단어도 복합어로 간주
    for original, _ in _EASY_REPLACEMENTS:
        if original in sentence:
            count += 1
    return count


def _break_long_sentence(sentence: str, max_length: int = 30) -> str:
    """긴 문장을 절 단위로 분리합니다.

    max_length 이하이면 그대로 반환합니다.
    """
    if len(sentence) <= max_length:
        return sentence

    # 절 단위로 분리 시도
    clauses = _CLAUSE_SPLIT.split(sentence)
    if len(clauses) <= 1:
        return sentence

    # 절을 짧은 문장으로 재조합
    result_parts = []
    current = ''
    for clause in clauses:
        clause = clause.strip()
        if not clause:
            continue
        if current and len(current) + len(clause) > max_length:
            result_parts.append(current.rstrip(',;，；ㅤ '))
            current = clause
        else:
            current = f"{current} {clause}".strip() if current else clause

    if current:
        result_parts.append(current.rstrip(',;，；ㅤ '))

    # 각 파트를 마침표로 연결
    result = '. '.join(part.rstrip('.') for part in result_parts if part)
    if result and not result.endswith('.'):
        result += '.'

    return result


def _apply_easy_replacements(text: str) -> str:
    """한자어/전문용어를 쉬운 대체어로 변환합니다."""
    result = text
    for original, replacement in _EASY_REPLACEMENTS:
        result = result.replace(original, replacement)
    return result


def simplify_text(content: str, level: str = 'easy') -> str:
    """독해 수준별 쉬운말 변환을 수행합니다.

    Args:
        content: 변환할 텍스트
        level: 변환 수준 ("easy": 초등, "normal": 중등, "original": 변환 없음)

    Returns:
        변환된 텍스트
    """
    if not content or not content.strip():
        return content or ''

    if level == 'original':
        return content

    sentences = _split_sentences(content)
    result_sentences = []

    for sentence in sentences:
        processed = sentence

        if level == 'easy':
            # 긴 문장 분리
            processed = _break_long_sentence(processed, max_length=30)
            # 용어 치환
            processed = _apply_easy_replacements(processed)
        elif level == 'normal':
            # 중등 수준: 매우 긴 문장만 분리, 용어 치환은 하지 않음
            processed = _break_long_sentence(processed, max_length=50)

        result_sentences.append(processed)

    return ' '.join(result_sentences)


def assess_readability(content: str) -> ReadabilityScore:
    """콘텐츠의 가독성을 평가합니다.

    Args:
        content: 평가할 텍스트

    Returns:
        ReadabilityScore 객체
    """
    if not content or not content.strip():
        return ReadabilityScore(
            score=100.0,
            level='easy',
            avg_sentence_length=0.0,
            complex_word_ratio=0.0,
            suggestions=[],
        )

    sentences = _split_sentences(content)
    if not sentences:
        return ReadabilityScore(
            score=100.0,
            level='easy',
            avg_sentence_length=0.0,
            complex_word_ratio=0.0,
            suggestions=[],
        )

    # 평균 문장 길이 계산
    total_chars = sum(len(s) for s in sentences)
    avg_sentence_length = round(total_chars / len(sentences), 1)

    # 복합어 비율 계산
    total_complex = sum(_count_complex_words(s) for s in sentences)
    # 대략 단어 수 추정 (한국어는 공백 기준)
    total_words = max(1, sum(len(s.split()) for s in sentences))
    complex_word_ratio = round(min(1.0, total_complex / total_words), 3)

    # 점수 계산 (높을수록 쉬움)
    score = 100.0

    # 긴 문장 감점: 30자 초과 문장 비율
    long_sentences = sum(1 for s in sentences if len(s) > 30)
    long_ratio = long_sentences / len(sentences)
    score -= long_ratio * 30

    # 복합어 감점
    score -= complex_word_ratio * 40

    # 평균 문장 길이 감점 (20자 초과부터)
    if avg_sentence_length > 20:
        score -= (avg_sentence_length - 20) * 0.5

    score = max(0.0, min(100.0, round(score, 1)))

    # 레벨 판정
    if score >= 70:
        level = 'easy'
    elif score >= 40:
        level = 'normal'
    else:
        level = 'hard'

    # 제안 생성
    suggestions = []
    if long_ratio > 0.3:
        suggestions.append(
            f'긴 문장이 {long_sentences}개({round(long_ratio * 100)}%)입니다. '
            f'30자 이내로 줄이면 읽기 쉬워집니다.'
        )
    if complex_word_ratio > 0.2:
        suggestions.append(
            '전문 용어가 많습니다. 쉬운 대체어 사용을 고려하세요.'
        )
    if avg_sentence_length > 40:
        suggestions.append(
            f'평균 문장 길이가 {avg_sentence_length}자입니다. '
            f'짧은 문장으로 나누면 가독성이 높아집니다.'
        )
    if not suggestions and score >= 70:
        suggestions.append('가독성이 양호합니다.')

    return ReadabilityScore(
        score=score,
        level=level,
        avg_sentence_length=avg_sentence_length,
        complex_word_ratio=complex_word_ratio,
        suggestions=suggestions,
    )
