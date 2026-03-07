"""
Sentence Length Rhythm Analyzer 서비스

문장 길이의 리듬(변화 패턴)을 분석합니다.
단조로운 문장 길이는 독자의 몰입을 방해합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str) -> List[str]:
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= 3]


def analyze_sentence_rhythm(content: str) -> dict:
    """문장 길이 리듬을 분석합니다.

    Returns:
        length_data, rhythm_analysis, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'length_data': [],
            'rhythm_analysis': {},
            'summary': {'total_sentences': 0, 'avg_length': 0.0,
                        'std_deviation': 0.0, 'rhythm_quality': 'none'},
            'score': 0.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    sentences = _split_sentences(content)
    if not sentences:
        return {
            'length_data': [],
            'rhythm_analysis': {},
            'summary': {'total_sentences': 0, 'avg_length': 0.0,
                        'std_deviation': 0.0, 'rhythm_quality': 'none'},
            'score': 0.0,
            'suggestions': [],
        }

    # 문장 길이 데이터
    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)

    # 표준편차
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std_dev = round(variance ** 0.5, 1)

    # 길이 카테고리
    length_data = []
    for i, (sent, length) in enumerate(zip(sentences, lengths)):
        if length < 20:
            category = 'short'
        elif length < 50:
            category = 'medium'
        elif length < 80:
            category = 'long'
        else:
            category = 'very_long'

        length_data.append({
            'index': i + 1,
            'length': length,
            'category': category,
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
        })

    # 리듬 분석
    consecutive_same = _count_consecutive_same(length_data)
    category_dist = {}
    for d in length_data:
        cat = d['category']
        category_dist[cat] = category_dist.get(cat, 0) + 1

    # 리듬 품질
    rhythm_quality = _assess_rhythm(std_dev, consecutive_same, len(sentences))

    rhythm_analysis = {
        'category_distribution': category_dist,
        'max_consecutive_same': consecutive_same,
        'length_range': max(lengths) - min(lengths) if lengths else 0,
    }

    score = _calculate_score(std_dev, consecutive_same, len(sentences), category_dist)

    suggestions = _generate_suggestions(
        avg, std_dev, consecutive_same, rhythm_quality, category_dist
    )

    return {
        'length_data': length_data[:50],  # 최대 50개
        'rhythm_analysis': rhythm_analysis,
        'summary': {
            'total_sentences': len(sentences),
            'avg_length': round(avg, 1),
            'std_deviation': std_dev,
            'rhythm_quality': rhythm_quality,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _count_consecutive_same(data: List[Dict]) -> int:
    """같은 카테고리가 연속되는 최대 횟수."""
    if not data:
        return 0
    max_count = 1
    current = 1
    for i in range(1, len(data)):
        if data[i]['category'] == data[i - 1]['category']:
            current += 1
            max_count = max(max_count, current)
        else:
            current = 1
    return max_count


def _assess_rhythm(std_dev: float, consecutive: int, total: int) -> str:
    if total < 3:
        return 'insufficient'
    if std_dev >= 20 and consecutive <= 3:
        return 'dynamic'
    if std_dev >= 10 and consecutive <= 4:
        return 'moderate'
    if std_dev < 10 or consecutive >= 5:
        return 'monotonous'
    return 'moderate'


def _calculate_score(std_dev: float, consecutive: int, total: int,
                     dist: Dict) -> float:
    if total < 3:
        return 50.0

    score = 70.0

    # 표준편차 보너스 (다양성)
    if 15 <= std_dev <= 30:
        score += 20.0
    elif 10 <= std_dev < 15:
        score += 10.0
    elif std_dev < 10:
        score -= 15.0  # 단조로움
    elif std_dev > 40:
        score -= 5.0  # 너무 극단적

    # 연속 동일 카테고리 페널티
    if consecutive >= 5:
        score -= 15.0
    elif consecutive >= 4:
        score -= 5.0

    # 카테고리 다양성 보너스
    categories_used = len(dist)
    if categories_used >= 3:
        score += 10.0

    return round(max(0.0, min(100.0, score)), 1)


def _generate_suggestions(avg: float, std_dev: float, consecutive: int,
                           quality: str, dist: Dict) -> List[str]:
    suggestions = []
    quality_labels = {
        'dynamic': '역동적 (좋은 리듬)',
        'moderate': '보통',
        'monotonous': '단조로움',
        'insufficient': '문장 부족',
    }
    suggestions.append(
        f'문장 리듬: {quality_labels.get(quality, quality)}. '
        f'평균 길이 {round(avg, 1)}자, 표준편차 {std_dev}.'
    )

    if quality == 'monotonous':
        suggestions.append(
            '문장 길이가 비슷합니다. 짧은 강조문과 긴 설명문을 섞어 리듬을 만드세요.'
        )

    if consecutive >= 5:
        suggestions.append(
            f'같은 길이 카테고리 {consecutive}문장 연속: 의도적으로 길이를 변화시키세요.'
        )

    if dist.get('very_long', 0) > 3:
        suggestions.append(
            f'매우 긴 문장(80자+) {dist["very_long"]}개: 문장을 분리하세요.'
        )

    return suggestions
