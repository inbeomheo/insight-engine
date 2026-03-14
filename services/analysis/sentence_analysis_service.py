"""
문장 분석 통합 서비스

8개 개별 서비스를 하나로 통합:
- analyze_variety (문장 다양성)
- analyze_connector_variety (연결어 다양성)
- analyze_sentence_rhythm (문장 리듬)
- analyze_sentence_ending_variety (종결어미 다양성)
- analyze_avg_words_per_sentence (문장당 평균 단어 수)
- score_sentence_complexity (문장 복잡도)
- analyze_sentence_starter_diversity (시작어 다양성)
- analyze_topic_sentence_alignment (주제문 정렬)

모두 규칙 기반 (AI API 호출 없음).
"""
import re
import math
import logging
from collections import Counter
from typing import List, Dict

logger = logging.getLogger(__name__)

# ─── 공통 유틸 ───────────────────────────────────────────

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def _split_sentences(content: str, min_len: int = 5) -> List[str]:
    """마크다운 제목을 제거하고 문장을 분리합니다."""
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= min_len]


# ═══════════════════════════════════════════════════════════
# 1. 문장 다양성 분석 (sentence_variety)
# ═══════════════════════════════════════════════════════════

_LENGTH_CATEGORIES = {
    'very_short': (0, 15),
    'short': (16, 30),
    'medium': (31, 60),
    'long': (61, 100),
    'very_long': (101, 9999),
}

_VARIETY_EMPTY = {
    'sentences': [],
    'length_distribution': {},
    'start_pattern': {'unique_ratio': 0, 'repeated': []},
    'variety_score': 0,
    'stats': {'count': 0, 'avg_length': 0, 'std_dev': 0,
              'min_length': 0, 'max_length': 0},
    'suggestions': [],
}


def _categorize_length(length: int) -> str:
    for cat, (lo, hi) in _LENGTH_CATEGORIES.items():
        if lo <= length <= hi:
            return cat
    return 'very_long'


def _variety_analyze_sentences(sentences: list) -> tuple:
    analyzed = []
    lengths = []
    start_words = []
    length_dist = {cat: 0 for cat in _LENGTH_CATEGORIES}

    for sent in sentences:
        length = len(sent)
        lengths.append(length)
        category = _categorize_length(length)
        length_dist[category] += 1

        start_match = re.match(r'([가-힣]{1,6})', sent)
        start_word = start_match.group(1) if start_match else sent[:3]
        start_words.append(start_word)

        analyzed.append({
            'text': sent[:80] + '...' if len(sent) > 80 else sent,
            'length': length,
            'category': category,
            'start_word': start_word,
        })

    return analyzed, lengths, start_words, length_dist


def _variety_analyze_start_patterns(start_words: list, count: int) -> tuple:
    unique_ratio = round(len(set(start_words)) / count, 2)
    start_freq = {}
    for w in start_words:
        start_freq[w] = start_freq.get(w, 0) + 1
    repeated = [{'word': w, 'count': c} for w, c in start_freq.items() if c >= 3]
    repeated.sort(key=lambda x: x['count'], reverse=True)
    return unique_ratio, repeated


def _variety_calculate_score(dist: dict, count: int, unique_ratio: float,
                             std_dev: float, avg: float) -> int:
    if count <= 1:
        return 100

    score = 30
    used_cats = sum(1 for v in dist.values() if v > 0)
    if used_cats >= 4:
        score += 25
    elif used_cats >= 3:
        score += 20
    elif used_cats >= 2:
        score += 10

    if unique_ratio >= 0.7:
        score += 20
    elif unique_ratio >= 0.5:
        score += 10
    elif unique_ratio >= 0.3:
        score += 5

    cv = std_dev / max(avg, 1)
    if 0.3 <= cv <= 0.7:
        score += 15
    elif 0.2 <= cv <= 0.8:
        score += 10
    elif cv < 0.15:
        score += 0

    dominant = max(dist.values())
    if dominant / count > 0.7:
        score -= 10

    return max(0, min(100, score))


def _variety_generate_suggestions(dist: dict, count: int, unique_ratio: float,
                                  repeated: list, avg: float) -> list:
    suggestions = []
    if count <= 2:
        suggestions.append('문장이 너무 적어 다양성 분석이 제한적입니다.')
        return suggestions

    used_cats = sum(1 for v in dist.values() if v > 0)
    if used_cats <= 2:
        suggestions.append('문장 길이가 편중되어 있습니다. 짧은 문장과 긴 문장을 섞어 리듬감을 만드세요.')
    if dist.get('very_long', 0) > count * 0.3:
        suggestions.append('긴 문장이 많습니다. 핵심 포인트는 짧은 문장으로 강조하세요.')
    if dist.get('very_short', 0) > count * 0.4:
        suggestions.append('짧은 문장이 많습니다. 설명이 필요한 부분은 좀 더 길게 서술하세요.')
    if unique_ratio < 0.4:
        suggestions.append('문장 시작이 반복적입니다. 다양한 표현으로 시작해 보세요.')
    if repeated:
        top = repeated[0]
        suggestions.append(f'"{top["word"]}"(으)로 시작하는 문장이 {top["count"]}개입니다. 다른 표현을 시도하세요.')
    if not suggestions:
        suggestions.append('문장 다양성이 양호합니다.')
    return suggestions


def analyze_variety(content: str) -> dict:
    """문장 다양성을 분석합니다."""
    if not content or not content.strip():
        return {**_VARIETY_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    clean = re.sub(r'#{1,6}\s+', '', content)
    clean = re.sub(r'```[\s\S]*?```', '', clean)
    clean = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', clean)

    raw_sentences = re.split(r'(?<=[.!?。])\s+|\n+', clean)
    sentences = [s.strip() for s in raw_sentences if len(s.strip()) >= 5]

    if not sentences:
        return {**_VARIETY_EMPTY, 'suggestions': ['분석할 문장이 없습니다.']}

    analyzed, lengths, start_words, length_dist = _variety_analyze_sentences(sentences)
    count = len(lengths)
    avg_length = sum(lengths) / count
    variance = sum((l - avg_length) ** 2 for l in lengths) / count
    std_dev = round(math.sqrt(variance), 1)

    unique_ratio, repeated = _variety_analyze_start_patterns(start_words, count)
    variety_score = _variety_calculate_score(length_dist, count, unique_ratio, std_dev, avg_length)
    suggestions = _variety_generate_suggestions(length_dist, count, unique_ratio, repeated, avg_length)

    return {
        'sentences': analyzed,
        'length_distribution': length_dist,
        'start_pattern': {'unique_ratio': unique_ratio, 'repeated': repeated},
        'variety_score': variety_score,
        'stats': {
            'count': count, 'avg_length': round(avg_length, 1),
            'std_dev': std_dev, 'min_length': min(lengths),
            'max_length': max(lengths),
        },
        'suggestions': suggestions,
    }


# ═══════════════════════════════════════════════════════════
# 2. 연결어 다양성 분석 (sentence_connector_variety)
# ═══════════════════════════════════════════════════════════

_KO_CONNECTORS = {
    '순접': ['그리고', '또한', '게다가', '더불어', '아울러', '뿐만 아니라', '나아가'],
    '역접': ['그러나', '하지만', '그렇지만', '반면', '반대로', '오히려', '그럼에도'],
    '인과': ['따라서', '그래서', '그러므로', '때문에', '덕분에', '결과적으로', '이로 인해'],
    '전환': ['한편', '그런데', '그건 그렇고', '어쨌든', '아무튼', '한편으로'],
    '예시': ['예를 들어', '예컨대', '가령', '이를테면', '구체적으로', '특히'],
    '정리': ['결론적으로', '요약하면', '정리하면', '즉', '다시 말해', '결국'],
}

_EN_CONNECTORS = {
    'addition': ['also', 'moreover', 'furthermore', 'additionally', 'besides', 'in addition'],
    'contrast': ['however', 'but', 'nevertheless', 'yet', 'although', 'on the other hand'],
    'cause': ['therefore', 'thus', 'consequently', 'hence', 'as a result', 'so'],
    'transition': ['meanwhile', 'incidentally', 'anyway', 'by the way'],
    'example': ['for example', 'for instance', 'specifically', 'in particular', 'such as'],
    'summary': ['in conclusion', 'to summarize', 'in short', 'overall', 'in other words'],
}

_KO_CONNECTOR_RE = {}
for _cat, _words in _KO_CONNECTORS.items():
    for _w in _words:
        _KO_CONNECTOR_RE[_w] = _cat

_EN_CONNECTOR_RE = {}
for _cat, _words in _EN_CONNECTORS.items():
    for _w in _words:
        _EN_CONNECTOR_RE[_w.lower()] = _cat


def _find_connector(sentence: str) -> tuple:
    stripped = sentence.strip()
    for word, cat in _KO_CONNECTOR_RE.items():
        if stripped.startswith(word):
            return word, cat
    lower = stripped.lower()
    for word, cat in _EN_CONNECTOR_RE.items():
        if lower.startswith(word):
            return word, cat
    return None, None


_CONNECTOR_EMPTY = {
    'connectors': [],
    'category_distribution': {},
    'summary': {'total_sentences': 0, 'connector_count': 0,
                'unique_connectors': 0, 'variety_rate': 0.0},
    'score': 100.0,
    'suggestions': [],
}


def _connector_scan(sentences: list) -> tuple:
    found_connectors = []
    connector_counts = Counter()
    category_counts = Counter()
    for sent in sentences:
        word, cat = _find_connector(sent)
        if word:
            found_connectors.append({
                'word': word, 'category': cat,
                'sentence': sent if len(sent) <= 60 else sent[:57] + '...',
            })
            connector_counts[word] += 1
            category_counts[cat] += 1
    return found_connectors, connector_counts, category_counts


def _connector_calculate_score(total: int, unique: int, variety: float,
                               sent_count: int, counts: Counter) -> float:
    if total == 0:
        return 80.0
    score = 100.0
    if variety < 50:
        score -= (50 - variety) * 0.5
    ratio = total / sent_count * 100 if sent_count > 0 else 0
    if ratio > 50:
        score -= (ratio - 50) * 0.5
    for word, count in counts.items():
        if count >= 3:
            score -= (count - 2) * 5.0
    return round(max(0.0, min(100.0, score)), 1)


def _get_alternatives(word: str, category: str) -> List[str]:
    if category in _KO_CONNECTORS:
        return [w for w in _KO_CONNECTORS[category] if w != word]
    if category in _EN_CONNECTORS:
        return [w for w in _EN_CONNECTORS[category] if w.lower() != word.lower()]
    return []


def _connector_generate_suggestions(total: int, sent_count: int, variety: float,
                                    repeated: Dict, cat_dist: Dict) -> List[str]:
    suggestions = []
    if total == 0:
        suggestions.append('연결어가 사용되지 않았습니다. 문장 간 흐름을 위해 연결어를 추가하세요.')
        return suggestions

    ratio = round(total / sent_count * 100, 1) if sent_count > 0 else 0
    suggestions.append(f'연결어 사용률 {ratio}% ({total}/{sent_count}문장), 다양성 {variety}%.')

    if repeated:
        for word, count in list(repeated.items())[:2]:
            cat = _KO_CONNECTOR_RE.get(word) or _EN_CONNECTOR_RE.get(word.lower(), '')
            alternatives = _get_alternatives(word, cat)
            alt_text = f' → 대안: {", ".join(alternatives[:3])}' if alternatives else ''
            suggestions.append(f'"{word}" {count}회 반복.{alt_text}')

    used_cats = set(cat_dist.keys())
    all_cats = set(_KO_CONNECTORS.keys()) | set(_EN_CONNECTORS.keys())
    missing = all_cats - used_cats
    if missing and len(missing) <= 4:
        labels = {'순접': '순접(그리고)', '역접': '역접(그러나)', '인과': '인과(따라서)',
                  '전환': '전환(한편)', '예시': '예시(예를 들어)', '정리': '정리(결론적으로)',
                  'addition': 'addition', 'contrast': 'contrast', 'cause': 'cause',
                  'transition': 'transition', 'example': 'example', 'summary': 'summary'}
        names = [labels.get(c, c) for c in list(missing)[:3]]
        suggestions.append(f'미사용 카테고리: {", ".join(names)}.')

    return suggestions


def analyze_connector_variety(content: str) -> dict:
    """연결어 다양성을 분석합니다."""
    if not content or not content.strip():
        return dict(_CONNECTOR_EMPTY)

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_CONNECTOR_EMPTY)

    found_connectors, connector_counts, category_counts = _connector_scan(sentences)
    total_connectors = len(found_connectors)
    unique_connectors = len(connector_counts)
    variety_rate = round(
        (unique_connectors / total_connectors * 100) if total_connectors > 0 else 0.0, 1
    )
    cat_dist = dict(category_counts)
    repeated = {w: c for w, c in connector_counts.items() if c >= 3}

    return {
        'connectors': found_connectors,
        'category_distribution': cat_dist,
        'summary': {'total_sentences': len(sentences), 'connector_count': total_connectors,
                     'unique_connectors': unique_connectors, 'variety_rate': variety_rate},
        'score': _connector_calculate_score(total_connectors, unique_connectors, variety_rate,
                                            len(sentences), connector_counts),
        'suggestions': _connector_generate_suggestions(total_connectors, len(sentences),
                                                       variety_rate, repeated, cat_dist),
    }


# ═══════════════════════════════════════════════════════════
# 3. 문장 길이 리듬 분석 (sentence_length_rhythm)
# ═══════════════════════════════════════════════════════════

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
    if not content or not content.strip():
        return {**_RHYTHM_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content, min_len=3)
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


# ═══════════════════════════════════════════════════════════
# 4. 종결어미 다양성 분석 (sentence_ending_variety)
# ═══════════════════════════════════════════════════════════

_KO_ENDINGS = {
    '합니다': re.compile(r'합니다[.!?]?\s*$'),
    '입니다': re.compile(r'입니다[.!?]?\s*$'),
    '됩니다': re.compile(r'됩니다[.!?]?\s*$'),
    '있습니다': re.compile(r'있습니다[.!?]?\s*$'),
    '없습니다': re.compile(r'없습니다[.!?]?\s*$'),
    '했습니다': re.compile(r'했습니다[.!?]?\s*$'),
    '세요': re.compile(r'세요[.!?]?\s*$'),
    '해요': re.compile(r'해요[.!?]?\s*$'),
    '네요': re.compile(r'네요[.!?]?\s*$'),
    '까요': re.compile(r'까요[.!?]?\s*$'),
    '다': re.compile(r'(?:이다|한다|된다|있다|없다)[.!?]?\s*$'),
}

_EN_PERIOD = re.compile(r'\.\s*$')
_EN_QUESTION = re.compile(r'\?\s*$')
_EN_EXCLAIM = re.compile(r'!\s*$')

_ENDING_EMPTY = {
    'ending_data': [],
    'ending_distribution': {},
    'summary': {'total_sentences': 0, 'unique_endings': 0,
                'variety_rate': 0.0, 'dominant_ending': ''},
    'score': 100.0,
    'suggestions': [],
}


def _classify_ending(sentence: str) -> str:
    for name, pattern in _KO_ENDINGS.items():
        if pattern.search(sentence):
            return name
    if _EN_QUESTION.search(sentence):
        return 'question'
    if _EN_EXCLAIM.search(sentence):
        return 'exclamation'
    if _EN_PERIOD.search(sentence):
        return 'period'
    return 'other'


def _ending_classify_all(sentences: List[str]) -> tuple:
    ending_data = []
    ending_counts = Counter()
    for sent in sentences:
        ending = _classify_ending(sent)
        ending_counts[ending] += 1
        ending_data.append({
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
            'ending': ending,
        })

    total = len(sentences)
    unique = len(ending_counts)
    variety_rate = round(unique / total * 100, 1) if total > 0 else 0.0
    dominant = ending_counts.most_common(1)[0][0] if ending_counts else ''
    dominant_ratio = round(
        ending_counts[dominant] / total * 100, 1
    ) if dominant and total > 0 else 0.0
    return ending_data, ending_counts, dominant, dominant_ratio, variety_rate


def _ending_calculate_score(variety: float, dominant_ratio: float,
                            counts: Counter, total: int) -> float:
    if total < 3:
        return 80.0
    score = 100.0
    if dominant_ratio > 80:
        score -= 30.0
    elif dominant_ratio > 70:
        score -= 20.0
    elif dominant_ratio > 60:
        score -= 10.0
    if variety < 20:
        score -= 15.0
    return round(max(0.0, min(100.0, score)), 1)


def _ending_generate_suggestions(dominant: str, ratio: float, variety: float,
                                 counts: Counter) -> List[str]:
    suggestions = []
    if ratio > 70:
        suggestions.append(
            f'종결어미 "{dominant}"가 {ratio}%로 과도합니다. '
            f'다른 어미를 섞어 단조로움을 피하세요.'
        )
    elif ratio > 50:
        suggestions.append(f'종결어미 "{dominant}"가 {ratio}%로 다소 높습니다.')
    else:
        suggestions.append(f'종결어미 다양성 {variety}%로 양호합니다.')

    q_count = counts.get('question', 0) + counts.get('까요', 0)
    if q_count == 0 and sum(counts.values()) >= 5:
        suggestions.append('질문형 문장이 없습니다. 독자 참여를 위해 질문을 추가하세요.')
    return suggestions


def analyze_sentence_ending_variety(content: str) -> dict:
    """문장 종결어미 다양성을 분석합니다."""
    if not content or not content.strip():
        return dict(_ENDING_EMPTY)

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_ENDING_EMPTY)

    ending_data, ending_counts, dominant, dominant_ratio, variety_rate = (
        _ending_classify_all(sentences)
    )
    total = len(sentences)

    return {
        'ending_data': ending_data[:30],
        'ending_distribution': dict(ending_counts),
        'summary': {
            'total_sentences': total,
            'unique_endings': len(ending_counts),
            'variety_rate': variety_rate,
            'dominant_ending': dominant,
        },
        'score': _ending_calculate_score(variety_rate, dominant_ratio, ending_counts, total),
        'suggestions': _ending_generate_suggestions(
            dominant, dominant_ratio, variety_rate, ending_counts
        ),
    }


# ═══════════════════════════════════════════════════════════
# 5. 문장당 평균 단어 수 (avg_words_per_sentence)
# ═══════════════════════════════════════════════════════════

_AVG_WORDS_EMPTY = {
    'sentence_data': [],
    'summary': {'total_sentences': 0, 'total_words': 0,
                'avg_words': 0.0, 'readability_level': 'none'},
    'score': 0.0,
    'suggestions': [],
}


def _avg_words_count(sentence: str) -> int:
    tokens = sentence.split()
    return len([t for t in tokens if len(t) >= 1])


def _avg_words_collect(sentences: List[str]) -> tuple:
    sentence_data = []
    total_words = 0
    long_sentences = 0
    short_sentences = 0
    for sent in sentences:
        wc = _avg_words_count(sent)
        total_words += wc
        if wc > 30:
            length_cat = 'long'
            long_sentences += 1
        elif wc < 5:
            length_cat = 'short'
            short_sentences += 1
        else:
            length_cat = 'normal'
        sentence_data.append({
            'text': sent if len(sent) <= 50 else sent[:47] + '...',
            'word_count': wc,
            'category': length_cat,
        })
    return sentence_data, total_words, long_sentences, short_sentences


def _avg_words_readability(avg: float, long_sentences: int, total: int) -> tuple:
    if 10 <= avg <= 20:
        level = 'optimal'
    elif 5 <= avg < 10 or 20 < avg <= 30:
        level = 'acceptable'
    elif avg < 5:
        level = 'too_short'
    else:
        level = 'too_long'

    optimal_center = 15.0
    deviation = abs(avg - optimal_center)
    if deviation <= 5:
        score = 100.0 - (deviation * 2.0)
    elif deviation <= 10:
        score = 90.0 - ((deviation - 5) ** 1.3 * 4.0)
    else:
        score = max(15.0, 60.0 - ((deviation - 10) ** 1.2 * 3.0))
    if long_sentences > total * 0.3:
        score -= 10.0
    return round(max(0.0, min(100.0, score)), 1), level


def _avg_words_generate_suggestions(avg: float, level: str, long: int,
                                    short: int, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'optimal': '최적 가독성', 'acceptable': '수용 가능',
        'too_short': '너무 짧음', 'too_long': '너무 길음',
    }
    suggestions.append(
        f'문장당 평균 {avg} 단어 ({level_labels.get(level, level)}). '
        f'권장 범위: 10-20 단어.'
    )
    if level == 'too_long':
        suggestions.append(f'긴 문장 {long}개: 접속사 기준으로 문장을 분리하세요.')
    elif level == 'too_short':
        suggestions.append(f'짧은 문장 {short}개: 구체적 설명을 추가하세요.')
    if long > total * 0.3 and total >= 5:
        suggestions.append(
            f'전체의 {round(long / total * 100)}%가 30단어 이상입니다. '
            f'독자 피로를 유발할 수 있습니다.'
        )
    return suggestions


def analyze_avg_words_per_sentence(content: str) -> dict:
    """문장당 평균 단어 수를 분석합니다."""
    if not content or not content.strip():
        return {**_AVG_WORDS_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_AVG_WORDS_EMPTY)

    sentence_data, total_words, long_sentences, short_sentences = _avg_words_collect(sentences)
    total = len(sentences)
    avg = round(total_words / total, 1) if total > 0 else 0.0
    score, level = _avg_words_readability(avg, long_sentences, total)

    return {
        'sentence_data': sentence_data[:30],
        'summary': {
            'total_sentences': total, 'total_words': total_words,
            'avg_words': avg, 'readability_level': level,
            'long_sentences': long_sentences, 'short_sentences': short_sentences,
        },
        'score': score,
        'suggestions': _avg_words_generate_suggestions(avg, level, long_sentences, short_sentences, total),
    }


# ═══════════════════════════════════════════════════════════
# 6. 문장 복잡도 평가 (sentence_complexity_scorer)
# ═══════════════════════════════════════════════════════════

_KO_CLAUSE_MARKERS = re.compile(
    r'(?:하고|하며|하면|하지만|하여|해서|하니|하는데|인데|는데|지만|면서|거나|든지|으므로|이므로|때문에|으니까|니까|으면서|ㄴ데)',
    re.UNICODE
)
_EN_CLAUSE_MARKERS = re.compile(
    r'\b(?:and|but|or|because|although|while|when|if|since|unless|whereas|however|therefore|moreover|furthermore|nevertheless|yet|so|that|which|who|whom|where)\b',
    re.IGNORECASE
)
_NESTING_OPEN = re.compile(r'[(\[{]')
_NESTING_CLOSE = re.compile(r'[)\]}]')
_COMMA_RE = re.compile(r'[,]')

_COMPLEXITY_EMPTY = {
    'sentences': [],
    'summary': {
        'total_sentences': 0, 'avg_complexity': 0.0,
        'distribution': {}, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _complexity_score_sentence(sentence: str) -> Dict:
    word_count = len(sentence.split())
    ko_clauses = len(_KO_CLAUSE_MARKERS.findall(sentence))
    en_clauses = len(_EN_CLAUSE_MARKERS.findall(sentence))
    clause_count = ko_clauses + en_clauses + 1

    comma_count = len(_COMMA_RE.findall(sentence))

    max_depth = 0
    depth = 0
    for ch in sentence:
        if _NESTING_OPEN.match(ch):
            depth += 1
            max_depth = max(max_depth, depth)
        elif _NESTING_CLOSE.match(ch):
            depth = max(0, depth - 1)

    complexity = 0.0
    complexity += min(30.0, clause_count * 8.0)
    complexity += min(20.0, comma_count * 5.0)
    complexity += min(20.0, max_depth * 10.0)
    complexity += min(30.0, max(0, word_count - 10) * 1.5)
    complexity = round(min(100.0, complexity), 1)

    if complexity <= 20:
        category = 'simple'
    elif complexity <= 45:
        category = 'moderate'
    elif complexity <= 70:
        category = 'complex'
    else:
        category = 'very_complex'

    return {
        'text': sentence if len(sentence) <= 60 else sentence[:57] + '...',
        'word_count': word_count,
        'clause_count': clause_count,
        'comma_count': comma_count,
        'nesting_depth': max_depth,
        'complexity': complexity,
        'category': category,
    }


def _complexity_compute_stats(scored: list) -> tuple:
    distribution = {'simple': 0, 'moderate': 0, 'complex': 0, 'very_complex': 0}
    total_complexity = 0.0
    for s in scored:
        distribution[s['category']] += 1
        total_complexity += s['complexity']
    avg = round(total_complexity / len(scored), 1)
    if avg <= 25:
        level = 'easy'
    elif avg <= 45:
        level = 'balanced'
    elif avg <= 65:
        level = 'complex'
    else:
        level = 'very_complex'
    return distribution, avg, level


def _complexity_compute_score(avg: float, distribution: dict) -> float:
    if 20 <= avg <= 45:
        score = 100.0
    elif avg < 20:
        score = 70.0 + avg * 1.5
    else:
        score = max(20.0, 100.0 - (avg - 45) * 2.0)
    if sum(1 for v in distribution.values() if v > 0) >= 3:
        score += 5.0
    return round(max(0.0, min(100.0, score)), 1)


def _complexity_generate_suggestions(avg: float, level: str,
                                     dist: Dict, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'easy': '쉬움', 'balanced': '균형',
        'complex': '복잡', 'very_complex': '매우 복잡',
    }
    suggestions.append(
        f'평균 복잡도 {avg} ({level_labels.get(level, level)}). '
        f'단순 {dist["simple"]}개, 보통 {dist["moderate"]}개, '
        f'복잡 {dist["complex"]}개, 매우 복잡 {dist["very_complex"]}개.'
    )
    if level == 'very_complex':
        suggestions.append('문장이 전반적으로 복잡합니다. 긴 문장을 나누고 접속사를 줄이세요.')
    elif level == 'easy' and total >= 5:
        suggestions.append('문장이 대부분 단순합니다. 복합문이나 종속절을 적절히 사용하면 글의 깊이가 더해집니다.')
    if dist['very_complex'] > total * 0.3:
        suggestions.append(
            f'매우 복잡한 문장이 {dist["very_complex"]}개({round(dist["very_complex"]/total*100)}%)입니다. '
            f'독자 피로를 줄이려면 간결한 문장과 번갈아 배치하세요.'
        )
    return suggestions


def score_sentence_complexity(content: str) -> dict:
    """문장 복잡도를 평가합니다."""
    if not content or not content.strip():
        return {**_COMPLEXITY_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_COMPLEXITY_EMPTY)

    scored = [_complexity_score_sentence(s) for s in sentences]
    distribution, avg_complexity, level = _complexity_compute_stats(scored)
    score = _complexity_compute_score(avg_complexity, distribution)

    return {
        'sentences': scored[:30],
        'summary': {
            'total_sentences': len(scored),
            'avg_complexity': avg_complexity,
            'distribution': distribution,
            'level': level,
        },
        'score': score,
        'suggestions': _complexity_generate_suggestions(avg_complexity, level, distribution, len(scored)),
    }


# ═══════════════════════════════════════════════════════════
# 7. 시작어 다양성 분석 (sentence_starter_diversity)
# ═══════════════════════════════════════════════════════════

_STARTER_EMPTY = {
    'starter_data': [],
    'summary': {
        'total_sentences': 0, 'unique_starters': 0,
        'diversity_ratio': 0.0, 'consecutive_repeats': 0, 'level': 'none',
    },
    'score': 0.0,
    'suggestions': [],
}


def _get_starter(sentence: str) -> str:
    tokens = sentence.split()
    if not tokens:
        return ''
    return tokens[0].lower().strip('\"\'([{')


def _starter_analyze(starters: list, total: int) -> tuple:
    starter_counter = Counter(starters)
    diversity_ratio = round(len(starter_counter) / max(total, 1) * 100, 1)
    consecutive_repeats = 0
    for i in range(1, len(starters)):
        if starters[i] == starters[i - 1] and starters[i]:
            consecutive_repeats += 1
    starter_data = [
        {'starter': word, 'count': count, 'ratio': round(count / total * 100, 1)}
        for word, count in starter_counter.most_common(15)
    ]
    return starter_counter, diversity_ratio, consecutive_repeats, starter_data


def _starter_compute_score(diversity_ratio: float, consecutive_repeats: int) -> tuple:
    if diversity_ratio >= 70:
        level = 'diverse'
    elif diversity_ratio >= 50:
        level = 'moderate'
    elif diversity_ratio >= 30:
        level = 'repetitive'
    else:
        level = 'very_repetitive'
    score = min(100.0, diversity_ratio * 1.3)
    if consecutive_repeats > 0:
        score -= min(20.0, consecutive_repeats * 5.0)
    return round(max(0.0, min(100.0, score)), 1), level


def _starter_generate_suggestions(counter: Counter, ratio: float, level: str,
                                  consec: int, total: int) -> List[str]:
    suggestions = []
    level_labels = {
        'diverse': '다양', 'moderate': '보통',
        'repetitive': '반복적', 'very_repetitive': '매우 반복적',
    }
    suggestions.append(
        f'시작어 다양성 {ratio}% ({level_labels.get(level, level)}). '
        f'총 {total}문장, 고유 시작어 {len(counter)}개.'
    )
    if consec > 0:
        suggestions.append(
            f'연속으로 같은 단어로 시작하는 문장이 {consec}쌍 있습니다. '
            f'문장 구조를 다양하게 바꾸세요.'
        )
    overused = [(w, c) for w, c in counter.most_common(3) if c >= 3]
    if overused:
        words = ', '.join([f'"{w}" ({c}회)' for w, c in overused])
        suggestions.append(f'과다 사용 시작어: {words}.')
    return suggestions


def analyze_sentence_starter_diversity(content: str) -> dict:
    """문장 시작어 다양성을 분석합니다."""
    if not content or not content.strip():
        return {**_STARTER_EMPTY, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    if not sentences:
        return dict(_STARTER_EMPTY)

    starters = [_get_starter(s) for s in sentences]
    total = len(starters)
    starter_counter, diversity_ratio, consec, starter_data = _starter_analyze(starters, total)
    score, level = _starter_compute_score(diversity_ratio, consec)

    return {
        'starter_data': starter_data,
        'summary': {
            'total_sentences': total,
            'unique_starters': len(starter_counter),
            'diversity_ratio': diversity_ratio,
            'consecutive_repeats': consec,
            'level': level,
        },
        'score': score,
        'suggestions': _starter_generate_suggestions(
            starter_counter, diversity_ratio, level, consec, total
        ),
    }


# ═══════════════════════════════════════════════════════════
# 8. 주제문 정렬 분석 (topic_sentence_alignment)
# ═══════════════════════════════════════════════════════════

_WORD_SPLIT_RE = re.compile(r'[가-힣]{2,}|[a-zA-Z]{3,}', re.IGNORECASE)
_PARA_SPLIT = re.compile(r'\n\s*\n')
_SENTENCE_SPLIT_PERIOD = re.compile(r'(?<=[.!?])\s+')

_WEAK_OPENERS = [
    re.compile(r'^(?:그리고|또한|그런데|한편|아무튼|어쨌든)\s', re.IGNORECASE),
    re.compile(r'^(?:Also|And|But|So|Well|Anyway)\s', re.IGNORECASE),
    re.compile(r'^(?:그래서|따라서|그러므로|결국)\s', re.IGNORECASE),
]

_STRONG_OPENERS = [
    re.compile(r'^(?:이\s*(?:글|섹션|장)|본\s*(?:장|절))', re.IGNORECASE),
    re.compile(r'^(?:핵심|요점|중요한\s*것|주요|첫\s*번째)', re.IGNORECASE),
    re.compile(r'^(?:In\s+this\s+section|The\s+(?:main|key|primary))\b', re.IGNORECASE),
    re.compile(r'^(?:Here|This\s+(?:section|chapter|part))\b', re.IGNORECASE),
]

_TOPIC_EMPTY = {
    'score': 100.0,
    'summary': {
        'total_paragraphs': 0, 'aligned_count': 0,
        'misaligned_count': 0, 'weak_opener_count': 0, 'level': 'none',
    },
    'paragraph_details': [],
    'suggestions': [],
}


def _topic_split_paragraphs(content: str) -> List[str]:
    paragraphs = _PARA_SPLIT.split(content)
    result = []
    for p in paragraphs:
        text = p.strip()
        if (text and
            not text.startswith('#') and
            not text.startswith('-') and
            not text.startswith('*') and
            not text.startswith('```') and
            not text.startswith('|') and
            len(text) >= 20):
            result.append(text)
    return result


def _topic_get_keywords(text: str) -> set:
    words = _WORD_SPLIT_RE.findall(text)
    stopwords = {'그것', '이것', '저것', '하는', '되는', '있는', '없는',
                 'the', 'this', 'that', 'with', 'from', 'have', 'been',
                 '하다', '되다', '있다', '없다', '것이', '것을', '것은'}
    return {w.lower() for w in words if w.lower() not in stopwords}


def _topic_analyze_paragraph(paragraph: str) -> Dict:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_PERIOD.split(paragraph)
                 if s.strip() and len(s.strip()) >= 5]

    if len(sentences) < 2:
        return {
            'first_sentence': paragraph[:60],
            'sentence_count': len(sentences),
            'alignment': 'too_short',
            'has_weak_opener': False,
            'has_strong_opener': False,
            'keyword_overlap': 1.0,
        }

    first = sentences[0]
    rest = ' '.join(sentences[1:])

    first_keywords = _topic_get_keywords(first)
    rest_keywords = _topic_get_keywords(rest)

    if not first_keywords:
        overlap = 0.0
    else:
        shared = first_keywords & rest_keywords
        overlap = len(shared) / len(first_keywords) if first_keywords else 0

    has_weak = any(p.search(first) for p in _WEAK_OPENERS)
    has_strong = any(p.search(first) for p in _STRONG_OPENERS)

    if has_strong and overlap >= 0.3:
        alignment = 'strong'
    elif overlap >= 0.3:
        alignment = 'aligned'
    elif has_weak:
        alignment = 'weak'
    elif overlap < 0.1 and len(sentences) >= 3:
        alignment = 'misaligned'
    else:
        alignment = 'neutral'

    return {
        'first_sentence': first[:60],
        'sentence_count': len(sentences),
        'alignment': alignment,
        'has_weak_opener': has_weak,
        'has_strong_opener': has_strong,
        'keyword_overlap': round(overlap, 2),
    }


def _topic_aggregate(details: list) -> tuple:
    aligned = sum(1 for d in details if d['alignment'] in ('strong', 'aligned'))
    misaligned = sum(1 for d in details if d['alignment'] == 'misaligned')
    weak = sum(1 for d in details if d['has_weak_opener'])
    analyzable = [d for d in details if d['alignment'] != 'too_short']
    return aligned, misaligned, weak, analyzable


def _topic_compute_score(aligned: int, misaligned: int, weak: int,
                         analyzable: list) -> tuple:
    if not analyzable:
        return 100.0, 'none'

    if misaligned == 0 and weak == 0:
        level = 'well_aligned'
    elif misaligned <= 1 and weak <= 1:
        level = 'mostly_aligned'
    elif misaligned <= 3:
        level = 'partial'
    else:
        level = 'misaligned'

    score = (aligned / len(analyzable)) * 85.0 + 15.0
    if misaligned > 0:
        score -= min(25.0, misaligned * 8.0)
    if weak > 0:
        score -= min(10.0, weak * 3.0)
    return round(max(0.0, min(100.0, score)), 1), level


def _topic_generate_suggestions(total: int, aligned: int, misaligned: int,
                                weak: int, level: str, details: List[Dict]) -> List[str]:
    suggestions = []
    level_labels = {
        'none': '해당 없음', 'well_aligned': '잘 정렬됨',
        'mostly_aligned': '대부분 정렬', 'partial': '부분적',
        'misaligned': '불일치',
    }
    suggestions.append(
        f'주제문 정렬: {level_labels.get(level, level)}. '
        f'{total}개 문단 중 {aligned}개 정렬, {misaligned}개 불일치.'
    )
    if weak > 0:
        suggestions.append(
            '"그리고", "또한" 같은 연결어로 시작하지 말고, '
            '문단의 핵심을 첫 문장에 담으세요.'
        )
    mis_details = [d for d in details if d['alignment'] == 'misaligned']
    for d in mis_details[:2]:
        suggestions.append(
            f'불일치 문단: "{d["first_sentence"][:40]}..." — '
            f'키워드 겹침 {d["keyword_overlap"]*100:.0f}%.'
        )
    return suggestions


def analyze_topic_sentence_alignment(content: str) -> dict:
    """문단별 주제문 정렬을 분석합니다."""
    if not content or not content.strip():
        return dict(_TOPIC_EMPTY)

    paragraphs = _topic_split_paragraphs(content)
    if not paragraphs:
        return dict(_TOPIC_EMPTY)

    details = [_topic_analyze_paragraph(p) for p in paragraphs]
    aligned, misaligned, weak, analyzable = _topic_aggregate(details)
    score, level = _topic_compute_score(aligned, misaligned, weak, analyzable)

    return {
        'score': score,
        'summary': {
            'total_paragraphs': len(details),
            'aligned_count': aligned,
            'misaligned_count': misaligned,
            'weak_opener_count': weak,
            'level': level,
        },
        'paragraph_details': [d for d in details[:10]
                               if d['alignment'] != 'too_short'],
        'suggestions': _topic_generate_suggestions(
            len(details), aligned, misaligned, weak, level, details
        ),
    }
