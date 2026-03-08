"""
가독성 점수 분석 서비스

한국어 텍스트의 가독성을 분석합니다.
- 평균 문장 길이
- 어휘 다양성 (TTR)
- 한자/외래어 비율
- 문단 구조
"""
import logging
import re

logger = logging.getLogger(__name__)

# 한자 유니코드 범위
_HANJA_PATTERN = re.compile(r'[\u4e00-\u9fff]')
# 외래어 (가타카나 등)
_KATAKANA_PATTERN = re.compile(r'[\u30a0-\u30ff]')
# 영문 단어
_ENGLISH_WORD_PATTERN = re.compile(r'[a-zA-Z]{2,}')


def analyze_readability(text: str) -> dict:
    """텍스트의 가독성을 분석합니다.

    Args:
        text: 분석할 텍스트 (마크다운 가능)

    Returns:
        {
            "score": int (0-100),
            "grade": "A" | "B" | "C" | "D",
            "details": {
                "avg_sentence_length": float,
                "vocabulary_diversity": float,
                "foreign_ratio": float,
                "paragraph_count": int,
                "sentence_count": int,
                "char_count": int,
            },
            "suggestions": list[str],
        }
    """
    if not text or not text.strip():
        return {
            'score': 0,
            'grade': 'D',
            'details': _empty_details(),
            'suggestions': ['텍스트가 비어 있습니다.'],
        }

    # 마크다운 제거
    plain = _strip_markdown(text)

    # 기본 통계
    paragraphs = [p.strip() for p in plain.split('\n\n') if p.strip()]
    sentences = _split_sentences(plain)
    words = plain.split()
    char_count = len(plain)

    sentence_count = max(len(sentences), 1)
    avg_sentence_length = round(sum(len(s) for s in sentences) / sentence_count, 1)

    # 어휘 다양성 (Type-Token Ratio)
    unique_words = set(words)
    ttr = round(len(unique_words) / len(words), 3) if words else 0.0

    # 한자/외래어 비율
    hanja_count = len(_HANJA_PATTERN.findall(plain))
    english_count = sum(len(m) for m in _ENGLISH_WORD_PATTERN.findall(plain))
    foreign_chars = hanja_count + english_count
    foreign_ratio = round(foreign_chars / char_count, 3) if char_count > 0 else 0.0

    # 점수 계산
    score, suggestions = _calculate_score(
        avg_sentence_length=avg_sentence_length,
        ttr=ttr,
        foreign_ratio=foreign_ratio,
        paragraph_count=len(paragraphs),
        sentence_count=sentence_count,
        char_count=char_count,
    )

    # 등급
    if score >= 80:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    elif score >= 40:
        grade = 'C'
    else:
        grade = 'D'

    return {
        'score': score,
        'grade': grade,
        'details': {
            'avg_sentence_length': avg_sentence_length,
            'vocabulary_diversity': ttr,
            'foreign_ratio': foreign_ratio,
            'paragraph_count': len(paragraphs),
            'sentence_count': sentence_count,
            'char_count': char_count,
        },
        'suggestions': suggestions,
    }


def _empty_details() -> dict:
    return {
        'avg_sentence_length': 0.0,
        'vocabulary_diversity': 0.0,
        'foreign_ratio': 0.0,
        'paragraph_count': 0,
        'sentence_count': 0,
        'char_count': 0,
    }


def _strip_markdown(text: str) -> str:
    """마크다운 문법을 제거합니다."""
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'^[-*+]\s+', '', text, flags=re.MULTILINE)
    return text.strip()


def _split_sentences(text: str) -> list:
    """문장 분리."""
    parts = re.split(r'[.!?。]\s*|\n+', text)
    return [s.strip() for s in parts if len(s.strip()) >= 5]


def _calculate_score(
    avg_sentence_length: float,
    ttr: float,
    foreign_ratio: float,
    paragraph_count: int,
    sentence_count: int,
    char_count: int,
) -> tuple:
    """가독성 점수와 제안을 생성합니다."""
    score = 60  # 기본 점수
    suggestions = []

    # 1) 평균 문장 길이 (한국어 기준 20-40자가 적정)
    if avg_sentence_length < 10:
        score -= 5
        suggestions.append('문장이 너무 짧습니다. 내용을 보충하세요.')
    elif avg_sentence_length <= 40:
        score += 15
    elif avg_sentence_length <= 60:
        score += 5
        suggestions.append('문장이 다소 깁니다. 50자 이내로 나누면 가독성이 향상됩니다.')
    else:
        score -= 10
        suggestions.append('문장이 매우 깁니다. 짧게 나누는 것을 권장합니다.')

    # 2) 어휘 다양성 (0.3~0.7이 적정)
    if ttr < 0.2:
        score -= 10
        suggestions.append('어휘 반복이 많습니다. 동의어나 다양한 표현을 사용하세요.')
    elif ttr <= 0.7:
        score += 10
    else:
        score += 5

    # 3) 외래어 비율 (0.3 이상이면 가독성 저하)
    if foreign_ratio > 0.3:
        score -= 10
        suggestions.append('외래어/영문 비율이 높습니다. 한국어 표현으로 대체를 검토하세요.')
    elif foreign_ratio <= 0.15:
        score += 5

    # 4) 문단 구조
    if paragraph_count <= 1 and char_count > 300:
        score -= 10
        suggestions.append('문단을 나누면 가독성이 크게 향상됩니다.')
    elif paragraph_count >= 3:
        score += 5

    # 클램핑
    score = max(0, min(100, score))

    if not suggestions:
        suggestions.append('가독성이 양호합니다.')

    return score, suggestions
