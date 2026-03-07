"""
Adverb Overuse Detector 서비스

콘텐츠에서 부사 남용을 감지하고 강한 대체 표현을 제안합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict


# ── 한국어 부사 사전 ──
_KOREAN_ADVERBS = {
    '매우', '정말', '아주', '너무', '굉장히', '엄청', '상당히',
    '대단히', '무척', '몹시', '꽤', '참', '진짜', '완전히',
    '절대로', '반드시', '꼭', '항상', '늘', '자주', '가끔',
    '다소', '약간', '조금', '살짝', '겨우', '결코', '전혀',
    '이미', '벌써', '곧', '바로', '즉시', '급히', '빨리',
    '천천히', '서서히', '점점', '더욱', '훨씬', '가장',
}

# ── 영어 -ly 부사 패턴 ──
_LY_ADVERB_PATTERN = re.compile(r'\b([a-zA-Z]{3,}ly)\b')

# -ly로 끝나지만 부사가 아닌 단어 (제외)
_LY_EXCEPTIONS = {
    'only', 'early', 'family', 'apply', 'supply', 'reply',
    'holy', 'july', 'italy', 'daily', 'rally', 'ally',
    'belly', 'bully', 'jelly', 'lily', 'fly', 'multiply',
    'ugly', 'lonely', 'friendly', 'lovely', 'lively',
    'likely', 'unlikely', 'namely', 'assembly',
}

# ── 약한 동사+부사 조합 → 강한 대체어 ──
_WEAK_COMBOS_KO = [
    (re.compile(r'매우\s+좋'), '탁월하다/우수하다'),
    (re.compile(r'매우\s+나쁘'), '최악이다/열악하다'),
    (re.compile(r'매우\s+크'), '거대하다/막대하다'),
    (re.compile(r'매우\s+작'), '미미하다/극소하다'),
    (re.compile(r'매우\s+빠르'), '신속하다/즉각적이다'),
    (re.compile(r'매우\s+느리'), '더디다/지체되다'),
    (re.compile(r'정말\s+좋'), '훌륭하다/뛰어나다'),
    (re.compile(r'정말\s+중요'), '핵심적이다/필수적이다'),
    (re.compile(r'너무\s+많'), '과다하다/넘치다'),
    (re.compile(r'너무\s+적'), '부족하다/미흡하다'),
    (re.compile(r'아주\s+좋'), '우수하다/뛰어나다'),
    (re.compile(r'굉장히\s+중요'), '결정적이다/핵심적이다'),
]

_WEAK_COMBOS_EN = [
    (re.compile(r'\bvery\s+good\b', re.IGNORECASE), 'excellent/superb'),
    (re.compile(r'\bvery\s+bad\b', re.IGNORECASE), 'terrible/awful'),
    (re.compile(r'\bvery\s+big\b', re.IGNORECASE), 'enormous/massive'),
    (re.compile(r'\bvery\s+small\b', re.IGNORECASE), 'tiny/minuscule'),
    (re.compile(r'\bvery\s+fast\b', re.IGNORECASE), 'rapid/swift'),
    (re.compile(r'\bvery\s+slow\b', re.IGNORECASE), 'sluggish/crawling'),
    (re.compile(r'\bvery\s+important\b', re.IGNORECASE), 'crucial/vital'),
    (re.compile(r'\bvery\s+happy\b', re.IGNORECASE), 'thrilled/elated'),
    (re.compile(r'\bvery\s+easy\b', re.IGNORECASE), 'effortless/simple'),
    (re.compile(r'\bvery\s+hard\b', re.IGNORECASE), 'arduous/grueling'),
    (re.compile(r'\breally\s+good\b', re.IGNORECASE), 'excellent/outstanding'),
    (re.compile(r'\breally\s+important\b', re.IGNORECASE), 'essential/critical'),
]


def _count_words(content: str) -> int:
    """전체 단어 수 (한국어 어절 + 영문 단어)."""
    english = re.findall(r'[A-Za-z]+(?:[-/][A-Za-z]+)*', content)
    korean = re.findall(r'[가-힣]+', content)
    return len(english) + len(korean)


def _find_korean_adverbs(content: str) -> Dict[str, int]:
    """한국어 부사 빈도를 반환합니다."""
    counts: Dict[str, int] = {}
    for adv in _KOREAN_ADVERBS:
        # 단어 경계 매칭: 앞뒤에 한글이 없어야 독립 부사로 인정
        pattern = r'(?<![가-힣])' + re.escape(adv) + r'(?![가-힣])'
        n = len(re.findall(pattern, content))
        if n > 0:
            counts[adv] = n
    return counts


def _find_english_adverbs(content: str) -> Dict[str, int]:
    """영어 -ly 부사 빈도를 반환합니다."""
    counts: Dict[str, int] = {}
    for match in _LY_ADVERB_PATTERN.finditer(content):
        word = match.group(1).lower()
        if word not in _LY_EXCEPTIONS:
            counts[word] = counts.get(word, 0) + 1
    return counts


def _find_weak_combinations(content: str) -> List[Dict[str, str]]:
    """약한 부사+동사 조합을 찾아 대체어를 제안합니다."""
    combos = []
    seen = set()
    for pattern, suggestion in _WEAK_COMBOS_KO + _WEAK_COMBOS_EN:
        for match in pattern.finditer(content):
            original = match.group(0)
            key = original.lower()
            if key not in seen:
                seen.add(key)
                combos.append({
                    'original': original,
                    'suggestion': suggestion,
                })
    return combos


def detect_adverb_overuse(content: str) -> dict:
    """콘텐츠에서 부사 남용을 감지합니다.

    Args:
        content: 분석할 텍스트 콘텐츠

    Returns:
        adverbs, weak_combinations, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'adverbs': [],
            'weak_combinations': [],
            'summary': {'total_adverbs': 0, 'adverb_density': 0.0, 'weak_combos': 0},
            'score': 100.0,
            'suggestions': [],
        }

    # 부사 감지
    ko_adverbs = _find_korean_adverbs(content)
    en_adverbs = _find_english_adverbs(content)

    # 부사 목록 구성
    adverbs = []
    for word, count in ko_adverbs.items():
        adverbs.append({
            'text': word, 'type': 'korean', 'count': count, 'suggestion': '',
        })
    for word, count in en_adverbs.items():
        adverbs.append({
            'text': word, 'type': 'english_ly', 'count': count, 'suggestion': '',
        })
    adverbs.sort(key=lambda a: a['count'], reverse=True)

    # 약한 조합 감지
    weak_combinations = _find_weak_combinations(content)

    # 밀도 계산
    total_adverb_count = sum(a['count'] for a in adverbs)
    word_count = _count_words(content)
    density = round((total_adverb_count / word_count * 100) if word_count > 0 else 0.0, 2)

    # 점수 계산
    if density <= 2.0:
        score = 100.0
    elif density <= 5.0:
        score = 100.0 - (density - 2.0) * (20.0 / 3.0)
    elif density <= 10.0:
        score = 80.0 - (density - 5.0) * 8.0
    else:
        score = max(0.0, 40.0 - (density - 10.0) * 4.0)
    score = round(max(0.0, min(100.0, score)), 1)

    suggestions = _generate_suggestions(adverbs, density, weak_combinations)

    return {
        'adverbs': adverbs,
        'weak_combinations': weak_combinations,
        'summary': {
            'total_adverbs': total_adverb_count,
            'adverb_density': density,
            'weak_combos': len(weak_combinations),
        },
        'score': score,
        'suggestions': suggestions,
    }


def _generate_suggestions(
    adverbs: List[Dict], density: float, weak_combos: List[Dict]
) -> List[str]:
    """분석 결과 기반 제안을 생성합니다."""
    suggestions = []
    if not adverbs:
        return suggestions

    if density > 5.0:
        suggestions.append(
            f'부사 밀도가 {density}%로 높습니다 (적정: 2-5%). '
            f'불필요한 부사를 줄이고 동사를 강화하세요.'
        )
    elif density > 2.0:
        suggestions.append(f'부사 밀도 {density}%는 적정 범위 내입니다.')

    overused = [a for a in adverbs if a['count'] >= 3]
    if overused:
        names = ', '.join(f'"{a["text"]}"({a["count"]}회)' for a in overused[:3])
        suggestions.append(f'자주 반복되는 부사: {names}. 동의어로 교체하거나 삭제를 고려하세요.')

    if weak_combos:
        suggestions.append(
            f'약한 부사+동사 조합이 {len(weak_combos)}개 있습니다. '
            f'더 강한 단일 동사로 교체하면 문장이 간결해집니다.'
        )
    return suggestions
