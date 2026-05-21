"""문장 길이 리듬 분석 (sentence_length_rhythm)."""
import logging
from typing import Dict, List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

_RHYTHM_EMPTY = {
    'length_data': [],
    'rhythm_analysis': {},
    'summary': {'total_sentences': 0, 'avg_length': 0.0,
                'std_deviation': 0.0, 'rhythm_quality': 'none'},
    'score': 0.0,
    'suggestions': [],
}


def _rhythm_build_length_data(sentences: List[str]) -> tuple:
    lengths = [len(s) for s in sentences]
    avg = sum(lengths) / len(lengths)
    variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
    std_dev = round(variance ** 0.5, 1)

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
            'index': i + 1, 'length': length, 'category': category,
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
        })

    return length_data, lengths, avg, std_dev


def _rhythm_count_consecutive_same(data: List[Dict]) -> int:
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


def _rhythm_assess(std_dev: float, consecutive: int, total: int) -> str:
    if total < 3:
        return 'insufficient'
    if std_dev >= 20 and consecutive <= 3:
        return 'dynamic'
    if std_dev >= 10 and consecutive <= 4:
        return 'moderate'
    if std_dev < 10 or consecutive >= 5:
        return 'monotonous'
    return 'moderate'


def _rhythm_calculate_score(std_dev: float, consecutive: int, total: int,
                            dist: Dict) -> float:
    if total < 3:
        return 50.0
    score = 70.0
    if 15 <= std_dev <= 30:
        score += 20.0
    elif 10 <= std_dev < 15:
        score += 10.0
    elif std_dev < 10:
        score -= 15.0
    elif std_dev > 40:
        score -= 5.0
    if consecutive >= 5:
        score -= 15.0
    elif consecutive >= 4:
        score -= 5.0
    categories_used = len(dist)
    if categories_used >= 3:
        score += 10.0
    return round(max(0.0, min(100.0, score)), 1)


def _rhythm_generate_suggestions(avg: float, std_dev: float, consecutive: int,
                                 quality: str, dist: Dict) -> List[str]:
    suggestions = []
    quality_labels = {
        'dynamic': '역동적 (좋은 리듬)', 'moderate': '보통',
        'monotonous': '단조로움', 'insufficient': '문장 부족',
    }
    suggestions.append(
        f'문장 리듬: {quality_labels.get(quality, quality)}. '
        f'평균 길이 {round(avg, 1)}자, 표준편차 {std_dev}.'
    )
    if quality == 'monotonous':
        suggestions.append('문장 길이가 비슷합니다. 짧은 강조문과 긴 설명문을 섞어 리듬을 만드세요.')
    if consecutive >= 5:
        suggestions.append(f'같은 길이 카테고리 {consecutive}문장 연속: 의도적으로 길이를 변화시키세요.')
    if dist.get('very_long', 0) > 3:
        suggestions.append(f'매우 긴 문장(80자+) {dist["very_long"]}개: 문장을 분리하세요.')
    return suggestions


def analyze_sentence_rhythm(content: str) -> dict:
    """문장 길이 리듬을 분석합니다."""
    try:
        if not content or not content.strip():
            return {**_RHYTHM_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = split_sentences(content, min_len=3)
        if not sentences:
            return dict(_RHYTHM_EMPTY)

        length_data, lengths, avg, std_dev = _rhythm_build_length_data(sentences)
        consecutive_same = _rhythm_count_consecutive_same(length_data)
        category_dist = {}
        for d in length_data:
            category_dist[d['category']] = category_dist.get(d['category'], 0) + 1

        rhythm_quality = _rhythm_assess(std_dev, consecutive_same, len(sentences))

        return {
            'length_data': length_data[:50],
            'rhythm_analysis': {
                'category_distribution': category_dist,
                'max_consecutive_same': consecutive_same,
                'length_range': max(lengths) - min(lengths) if lengths else 0,
            },
            'summary': {
                'total_sentences': len(sentences), 'avg_length': round(avg, 1),
                'std_deviation': std_dev, 'rhythm_quality': rhythm_quality,
            },
            'score': _rhythm_calculate_score(std_dev, consecutive_same, len(sentences), category_dist),
            'suggestions': _rhythm_generate_suggestions(avg, std_dev, consecutive_same,
                                                        rhythm_quality, category_dist),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
