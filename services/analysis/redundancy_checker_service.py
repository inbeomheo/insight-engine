"""
중복/반복 표현 감지 서비스

콘텐츠에서 반복되는 문구, 중복 문장, 불필요한 반복을
감지하고 간결한 대안을 제안합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 한국어 반복 강조 패턴 (제거 대상)
_REDUNDANT_PATTERNS = [
    (r'매우\s+매우', '매우'),
    (r'가장\s+최고', '최고'),
    (r'다시\s+반복', '반복'),
    (r'미리\s+사전에', '사전에'),
    (r'함께\s+같이', '함께'),
    (r'서로\s+상호', '상호'),
    (r'현재\s+지금', '현재'),
    (r'완전히\s+전부', '완전히'),
    (r'각각\s+개별', '각각'),
]

# 과도 사용 경고 단어
_OVERUSE_WORDS = [
    '정말', '매우', '상당히', '꽤', '아주', '너무', '엄청',
    '특히', '사실', '기본적으로', '일반적으로', '보통',
]


_EMPTY_RESULT = {
    'repeated_phrases': [],
    'redundant_patterns': [],
    'overused_words': [],
    'similar_sentences': [],
    'score': 100,
    'suggestions': [],
}


def check_redundancy(content: str) -> dict:
    """콘텐츠의 중복/반복 표현을 감지합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            "repeated_phrases": [{"phrase": str, "count": int, "severity": str}],
            "redundant_patterns": [{"original": str, "suggestion": str, "line": str}],
            "overused_words": [{"word": str, "count": int, "ratio": float}],
            "similar_sentences": [{"sentence_a": str, "sentence_b": str, "similarity": float}],
            "score": int (0~100, 높을수록 깔끔),
            "suggestions": list[str],
        }
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        repeated_phrases = _find_repeated_phrases(content)
        redundant_patterns = _find_redundant_patterns(content)
        overused_words = _find_overused_words(content)
        similar_sentences = _find_similar_sentences(content)

        return {
            'repeated_phrases': repeated_phrases,
            'redundant_patterns': redundant_patterns,
            'overused_words': overused_words,
            'similar_sentences': similar_sentences,
            'score': _calculate_score(repeated_phrases, redundant_patterns, overused_words, similar_sentences),
            'suggestions': _generate_suggestions(repeated_phrases, redundant_patterns, overused_words, similar_sentences),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}


def _find_repeated_phrases(content: str) -> list:
    """3단어 이상 반복 문구를 찾습니다."""
    # 한국어 단어 분리
    words = re.findall(r'[가-힣a-zA-Z]+', content)
    if len(words) < 6:
        return []

    # 3-gram, 4-gram 생성
    phrases = {}
    for n in (3, 4):
        for i in range(len(words) - n + 1):
            phrase = ' '.join(words[i:i+n])
            if len(phrase) >= 6:  # 너무 짧은 것 제외
                phrases[phrase] = phrases.get(phrase, 0) + 1

    # 2회 이상 반복된 것만
    repeated = []
    for phrase, count in sorted(phrases.items(), key=lambda x: x[1], reverse=True):
        if count >= 2:
            severity = 'high' if count >= 4 else 'medium' if count >= 3 else 'low'
            repeated.append({
                'phrase': phrase,
                'count': count,
                'severity': severity,
            })

    return repeated[:10]  # 상위 10개


def _find_redundant_patterns(content: str) -> list:
    """중복 강조 패턴을 찾습니다."""
    found = []
    for pattern, suggestion in _REDUNDANT_PATTERNS:
        matches = re.finditer(pattern, content)
        for m in matches:
            # 주변 컨텍스트
            start = max(0, m.start() - 10)
            end = min(len(content), m.end() + 10)
            context = content[start:end].strip()
            found.append({
                'original': m.group(),
                'suggestion': suggestion,
                'line': context,
            })
    return found


def _find_overused_words(content: str) -> list:
    """과도하게 사용된 단어를 찾습니다."""
    words = re.findall(r'[가-힣]{2,}', content)
    total = len(words)
    if total < 20:
        return []

    results = []
    for target in _OVERUSE_WORDS:
        count = sum(1 for w in words if target in w)
        if count >= 3:
            ratio = round(count / total * 100, 2)
            results.append({
                'word': target,
                'count': count,
                'ratio': ratio,
            })

    return sorted(results, key=lambda x: x['count'], reverse=True)


def _find_similar_sentences(content: str) -> list:
    """유사한 문장 쌍을 찾습니다."""
    sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', content)
                 if len(s.strip()) >= 10]

    if len(sentences) < 2:
        return []

    similar = []
    for i in range(len(sentences)):
        for j in range(i + 1, min(i + 10, len(sentences))):  # 근접 문장만
            sim = _jaccard_similarity(sentences[i], sentences[j])
            if sim >= 0.5:
                similar.append({
                    'sentence_a': sentences[i][:60],
                    'sentence_b': sentences[j][:60],
                    'similarity': round(sim, 2),
                })

    return sorted(similar, key=lambda x: x['similarity'], reverse=True)[:5]


def _jaccard_similarity(a: str, b: str) -> float:
    """두 문장의 자카드 유사도를 계산합니다."""
    words_a = set(re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', a))
    words_b = set(re.findall(r'[가-힣]{2,}|[a-zA-Z]{2,}', b))
    if not words_a or not words_b:
        return 0
    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _calculate_score(phrases: list, patterns: list, overused: list, similar: list) -> int:
    """중복 없을수록 높은 점수 (0~100)."""
    score = 100

    # 반복 문구 감점
    for p in phrases:
        if p['severity'] == 'high':
            score -= 8
        elif p['severity'] == 'medium':
            score -= 5
        else:
            score -= 2

    # 중복 패턴 감점
    score -= len(patterns) * 5

    # 과다 사용 감점
    score -= len(overused) * 3

    # 유사 문장 감점
    for s in similar:
        if s['similarity'] >= 0.7:
            score -= 8
        else:
            score -= 4

    return max(0, min(100, score))


def _generate_suggestions(phrases: list, patterns: list, overused: list, similar: list) -> list:
    suggestions = []

    if phrases:
        top = phrases[0]
        suggestions.append(f'"{top["phrase"]}"이(가) {top["count"]}번 반복됩니다. 동의어나 다른 표현으로 대체하세요.')

    if patterns:
        suggestions.append(f'중복 강조 표현 {len(patterns)}개가 감지되었습니다. 간결하게 줄여 보세요.')

    if overused:
        words = ', '.join(f'"{w["word"]}"' for w in overused[:3])
        suggestions.append(f'{words} 등이 과다 사용되었습니다. 변화를 주세요.')

    if similar:
        suggestions.append(f'유사한 문장 쌍 {len(similar)}개가 있습니다. 중복을 제거하거나 통합하세요.')

    if not suggestions:
        suggestions.append('중복이나 반복 표현이 없습니다. 깔끔한 글입니다.')

    return suggestions
