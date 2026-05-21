"""연결어 다양성 분석 (sentence_connector_variety)."""
import logging
from collections import Counter
from typing import Dict, List

from services.analysis.sentence._common import split_sentences

logger = logging.getLogger(__name__)

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
    try:
        if not content or not content.strip():
            return dict(_CONNECTOR_EMPTY)

        sentences = split_sentences(content)
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
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}
