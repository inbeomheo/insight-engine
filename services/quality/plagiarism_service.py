"""
표절/중복 감지 서비스

콘텐츠에서 핵심 문장을 추출하고 n-gram 기반 자기중복 분석을 수행합니다.
외부 검색 의존 없이 텍스트 내부 중복과 구조적 반복을 탐지합니다.
"""
import logging
import re
from collections import Counter

logger = logging.getLogger(__name__)

# 최소 문장 길이 (이 이하는 분석 제외)
_MIN_SENTENCE_LENGTH = 15
# n-gram 크기 (단어 단위)
_NGRAM_SIZE = 5
# 중복으로 판정하는 n-gram 반복 횟수
_DUPLICATE_THRESHOLD = 2


_EMPTY_RESULT = {
    'score': 0,
    'duplicate_ratio': 0.0,
    'repeated_phrases': [],
    'similar_sentences': [],
    'verdict': 'clean',
}


def check_plagiarism(content: str) -> dict:
    """콘텐츠의 내부 중복/반복을 분석합니다.

    Args:
        content: 분석할 텍스트 (마크다운 가능)

    Returns:
        {
            "score": int (0-100, 0=중복 없음, 100=완전 중복),
            "duplicate_ratio": float,
            "repeated_phrases": list[{"phrase": str, "count": int}],
            "similar_sentences": list[{"sentence_a": str, "sentence_b": str, "similarity": float}],
            "verdict": "clean" | "minor" | "significant",
        }
    """
    if not content or not content.strip():
        return dict(_EMPTY_RESULT)

    plain = _strip_markdown(content)
    sentences = _split_sentences(plain)
    if len(sentences) < 2:
        return dict(_EMPTY_RESULT)

    repeated_phrases = _find_repeated_ngrams(plain)
    similar_pairs = _find_similar_sentences(sentences)
    score, verdict = _compute_score_and_verdict(repeated_phrases, similar_pairs)

    return {
        'score': score,
        'duplicate_ratio': _compute_duplicate_ratio(plain, repeated_phrases),
        'repeated_phrases': repeated_phrases[:10],
        'similar_sentences': similar_pairs[:5],
        'verdict': verdict,
    }


def _compute_score_and_verdict(repeated_phrases: list, similar_pairs: list) -> tuple:
    """n-gram 반복과 유사 문장 수로 점수와 판정을 계산합니다."""
    score = min(min(len(repeated_phrases) * 10, 50) + min(len(similar_pairs) * 15, 50), 100)
    if score < 20:
        verdict = 'clean'
    elif score < 50:
        verdict = 'minor'
    else:
        verdict = 'significant'
    return score, verdict


def _compute_duplicate_ratio(plain: str, repeated_phrases: list) -> float:
    """반복 구문의 단어 비율을 계산합니다."""
    total_words = len(plain.split())
    if total_words == 0:
        return 0.0
    repeated_word_count = sum(
        len(p['phrase'].split()) * (p['count'] - 1) for p in repeated_phrases
    )
    return round(repeated_word_count / total_words, 3)


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
    """텍스트를 문장 단위로 분리합니다."""
    # 한국어/영어 문장 구분
    parts = re.split(r'[.!?。]\s+|\n+', text)
    return [s.strip() for s in parts if len(s.strip()) >= _MIN_SENTENCE_LENGTH]


def _find_repeated_ngrams(text: str) -> list:
    """반복되는 n-gram을 찾습니다."""
    words = text.split()
    if len(words) < _NGRAM_SIZE:
        return []

    ngrams = []
    for i in range(len(words) - _NGRAM_SIZE + 1):
        ngram = ' '.join(words[i:i + _NGRAM_SIZE])
        ngrams.append(ngram)

    counter = Counter(ngrams)
    repeated = [
        {'phrase': phrase, 'count': count}
        for phrase, count in counter.most_common(20)
        if count >= _DUPLICATE_THRESHOLD
    ]
    return repeated


def _find_similar_sentences(sentences: list) -> list:
    """문장 간 유사도를 계산하여 유사한 쌍을 반환합니다."""
    similar = []

    for i in range(len(sentences)):
        for j in range(i + 1, min(i + 10, len(sentences))):
            sim = _jaccard_similarity(sentences[i], sentences[j])
            if sim >= 0.6:
                similar.append({
                    'sentence_a': sentences[i][:100],
                    'sentence_b': sentences[j][:100],
                    'similarity': round(sim, 3),
                })

    # 유사도 높은 순 정렬
    similar.sort(key=lambda x: x['similarity'], reverse=True)
    return similar


def _jaccard_similarity(text_a: str, text_b: str) -> float:
    """두 텍스트의 Jaccard 유사도를 계산합니다."""
    set_a = set(text_a.split())
    set_b = set(text_b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0
