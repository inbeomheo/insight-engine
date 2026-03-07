"""
Context-Free Extractability Analyzer 서비스

문장/문단을 본문에서 떼어내도 의미가 유지되는지 분석합니다.
AI 답변/요약에 인용되기 쉬운 "독립형 설명" 비율을 평가합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+')

# 문맥 의존 지시어 (이것, 그것, 위에서, 아래에서 등)
_CONTEXT_DEPENDENT = [
    re.compile(r'(?:이것|그것|저것|이런|그런|저런|이러한|그러한)', re.IGNORECASE),
    re.compile(r'(?:위에서|아래에서|앞에서|뒤에서|앞서|다음에서)', re.IGNORECASE),
    re.compile(r'(?:이\s*(?:경우|방법|기능|부분)|그\s*(?:결과|이유|때문))', re.IGNORECASE),
    re.compile(r'\b(?:this|that|these|those|above|below|former|latter|aforementioned)\b', re.IGNORECASE),
    re.compile(r'\b(?:as\s+mentioned|see\s+(?:above|below)|refer\s+to)\b', re.IGNORECASE),
]

# 독립 설명 신호 (정의문, 팩트 서술)
_EXTRACTABLE_SIGNALS = [
    # 정의문: "X는 Y이다"
    re.compile(r'(?:[가-힣A-Za-z]+(?:은|는|이란|이라|란)\s+.{10,}(?:이다|입니다|합니다|됩니다))', re.IGNORECASE),
    # 수치 포함 팩트
    re.compile(r'(?:\d+(?:\.\d+)?(?:%|퍼센트|배|개|건|명|원|달러|\$|GB|MB|초|분|시간))', re.IGNORECASE),
    # 영어 정의문
    re.compile(r'\b[A-Z][a-z]+(?:\s+[a-z]+){0,3}\s+(?:is|are|refers?\s+to|means?)\s+', re.IGNORECASE),
]


def _is_context_dependent(sentence: str) -> bool:
    """문맥 의존적인 문장인지 판별합니다."""
    for pat in _CONTEXT_DEPENDENT:
        if pat.search(sentence):
            return True
    return False


def _is_extractable(sentence: str) -> bool:
    """독립적으로 추출 가능한 문장인지 판별합니다."""
    # 최소 길이
    if len(sentence) < 15:
        return False
    # 문맥 의존이면 추출 불가
    if _is_context_dependent(sentence):
        return False
    # 독립 설명 신호가 있으면 추출 가능
    for pat in _EXTRACTABLE_SIGNALS:
        if pat.search(sentence):
            return True
    # 충분한 길이 + 문맥 비의존 = 부분적으로 추출 가능
    return len(sentence) >= 30 and not _is_context_dependent(sentence)


def analyze_extractability(content: str) -> dict:
    """콘텐츠의 문맥 독립 추출 가능성을 분석합니다.

    Returns:
        score, summary, flagged_spans, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'score': 0.0,
            'summary': {
                'total_sentences': 0,
                'extractable_count': 0,
                'dependent_count': 0,
                'extractable_ratio': 0.0,
                'level': 'none',
            },
            'flagged_spans': [],
            'suggestions': [],
        }

    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(content) if s.strip() and len(s.strip()) >= 10]

    if not sentences:
        return {
            'score': 50.0,
            'summary': {
                'total_sentences': 0,
                'extractable_count': 0,
                'dependent_count': 0,
                'extractable_ratio': 0.0,
                'level': 'none',
            },
            'flagged_spans': [],
            'suggestions': [],
        }

    extractable = []
    dependent = []

    for s in sentences:
        if _is_context_dependent(s):
            dependent.append(s[:60])
        elif _is_extractable(s):
            extractable.append(s[:60])

    total = len(sentences)
    ext_ratio = round(len(extractable) / max(total, 1) * 100, 1)
    dep_ratio = round(len(dependent) / max(total, 1) * 100, 1)

    # 레벨 판정
    if ext_ratio >= 60:
        level = 'excellent'
    elif ext_ratio >= 40:
        level = 'good'
    elif ext_ratio >= 20:
        level = 'fair'
    else:
        level = 'poor'

    # 점수 계산
    score = min(100.0, ext_ratio * 1.5)
    # 문맥 의존 비율 감점
    if dep_ratio > 30:
        score -= (dep_ratio - 30) * 0.5

    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(
        total, len(extractable), len(dependent),
        ext_ratio, dep_ratio, level, dependent[:3]
    )

    return {
        'score': score,
        'summary': {
            'total_sentences': total,
            'extractable_count': len(extractable),
            'dependent_count': len(dependent),
            'extractable_ratio': ext_ratio,
            'level': level,
        },
        'flagged_spans': dependent[:10],
        'suggestions': suggestions,
    }


def _generate_suggestions(total: int, ext: int, dep: int,
                           ext_ratio: float, dep_ratio: float,
                           level: str, examples: List[str]) -> List[str]:
    suggestions = []

    level_labels = {
        'excellent': '우수', 'good': '양호',
        'fair': '보통', 'poor': '미흡',
    }
    suggestions.append(
        f'추출 가능 비율: {ext_ratio}% ({level_labels.get(level, level)}). '
        f'독립형 {ext}건, 문맥의존 {dep}건 / 전체 {total}건.'
    )

    if dep_ratio > 20:
        suggestions.append(
            '"이것", "위에서", "그 결과" 같은 지시어를 줄이고 '
            '구체적 명사로 바꾸면 AI 인용 가능성이 높아집니다.'
        )

    if ext_ratio < 40:
        suggestions.append(
            '정의문("X는 Y이다"), 수치 포함 팩트를 늘리면 '
            'AI 답변에 인용되기 쉬워집니다.'
        )

    for ex in examples[:2]:
        suggestions.append(f'문맥 의존 문장: "{ex}..."')

    return suggestions
