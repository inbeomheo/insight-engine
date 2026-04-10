"""
Filler & Hedge Phrase Detector 서비스

콘텐츠에서 군더더기 표현(filler)과 헤지 표현(hedge)을
감지하여 문장 강화를 돕습니다.
규칙 기반 감지 — AI API 호출 없음.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ── 한국어 군더더기(filler) 패턴 ──────────────────────────────
_KO_FILLERS = {
    '사실': '삭제 권장',
    '기본적으로': '삭제 권장',
    '어쨌든': '삭제 권장',
    '말하자면': '삭제 권장',
    '그러니까': '삭제 권장',
    '일단': '삭제 권장',
    '뭐랄까': '삭제 권장',
    '솔직히': '삭제 권장',
    '그냥': '삭제 권장',
    '진짜': '삭제 권장',
    '되게': '삭제 권장',
    '약간은': '삭제 권장',
    '좀': '삭제 권장',
    '아무튼': '삭제 권장',
    '어차피': '삭제 권장',
}

# ── 영어 군더더기(filler) 패턴 ──────────────────────────────
_EN_FILLERS = {
    'basically': '삭제 권장',
    'actually': '삭제 권장',
    'literally': '삭제 권장',
    'you know': '삭제 권장',
    'like': '삭제 권장',
    'just': '삭제 권장',
    'really': '삭제 권장',
    'very': '삭제 권장',
    'quite': '삭제 권장',
    'sort of': '삭제 권장',
    'kind of': '삭제 권장',
    'i mean': '삭제 권장',
    'well': '삭제 권장',
    'honestly': '삭제 권장',
    'right': '삭제 권장',
}

# 사전 컴파일된 영어 filler 패턴 (루프 내 re.compile 반복 방지)
_EN_FILLER_PATTERNS = {
    phrase: re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
    for phrase in _EN_FILLERS
}

# ── 한국어 헤지(hedge) 패턴 ──────────────────────────────
# (phrase, suggestion) — 정규식 기반 항목은 별도 리스트
_KO_HEDGES = {
    '약간': '"약간" 삭제 또는 구체적 수치로 대체',
    '어쩌면': '단정적 표현으로 대체',
    '아마도': '근거를 제시하거나 삭제',
    '경우에 따라': '구체적 조건을 명시',
    '일부에서는': '출처를 명시하거나 삭제',
    '어느 정도': '구체적 수치로 대체',
    '다소': '구체적 표현으로 대체',
}

# 정규식 기반 한국어 헤지 패턴 (어미/조사 결합형)
_KO_HEDGE_REGEX = [
    (re.compile(r'[가-힣]+\s*수도'), '단정적 표현으로 대체'),           # ~ㄹ 수도
    (re.compile(r'[가-힣]+\s*것\s*같'), '단정적 표현으로 대체'),        # ~은/는/인 것 같
    (re.compile(r'[가-힣]+라고\s*할\s*수\s*있'), '직접적 서술로 대체'),  # ~라고 할 수 있
    (re.compile(r'[가-힣]+\s*편이'), '단정적 표현으로 대체'),           # ~인/은/는 편이
]

# ── 영어 헤지(hedge) 패턴 ──────────────────────────────
_EN_HEDGES = {
    'maybe': '삭제하거나 근거 제시',
    'perhaps': '삭제하거나 근거 제시',
    'somewhat': '구체적 표현으로 대체',
    'seems to': '단정적 표현으로 대체 (예: "is")',
    'might': '단정적 표현으로 대체 (예: "will")',
    'could be': '단정적 표현으로 대체 (예: "is")',
    'tends to': '단정적 표현으로 대체',
    'a bit': '삭제 또는 구체적 수치로 대체',
    'a little': '삭제 또는 구체적 수치로 대체',
    'to some extent': '구체적 범위를 명시',
    'in some cases': '구체적 조건을 명시',
    'it appears': '단정적 표현으로 대체',
}

# 사전 컴파일된 영어 hedge 패턴 (루프 내 re.compile 반복 방지)
_EN_HEDGE_PATTERNS = {
    phrase: re.compile(r'\b' + re.escape(phrase) + r'\b', re.IGNORECASE)
    for phrase in _EN_HEDGES
}


def _split_sentences(content: str) -> list[str]:
    """콘텐츠를 문장 단위로 분리합니다."""
    # 마침표, 느낌표, 물음표 또는 줄바꿈으로 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    return [s.strip() for s in raw if s.strip()]


def _detect_in_sentence(sentence: str) -> list[dict]:
    """단일 문장에서 filler/hedge를 감지합니다."""
    detections = []

    # ── 한국어 filler ──
    for phrase, suggestion in _KO_FILLERS.items():
        # 단어 경계: 한국어는 공백/문장시작/조사 앞뒤
        for m in re.finditer(re.escape(phrase), sentence):
            detections.append({
                'phrase': phrase,
                'category': 'filler',
                'sentence': sentence,
                'position': m.start(),
                'suggestion': suggestion,
            })

    # ── 영어 filler (사전 컴파일 패턴 사용) ──
    for phrase, suggestion in _EN_FILLERS.items():
        for m in _EN_FILLER_PATTERNS[phrase].finditer(sentence):
            detections.append({
                'phrase': m.group(),
                'category': 'filler',
                'sentence': sentence,
                'position': m.start(),
                'suggestion': suggestion,
            })

    # ── 한국어 hedge (고정 문자열) ──
    for phrase, suggestion in _KO_HEDGES.items():
        for m in re.finditer(re.escape(phrase), sentence):
            detections.append({
                'phrase': phrase,
                'category': 'hedge',
                'sentence': sentence,
                'position': m.start(),
                'suggestion': suggestion,
            })

    # ── 한국어 hedge (정규식) ──
    for pattern, suggestion in _KO_HEDGE_REGEX:
        for m in pattern.finditer(sentence):
            detections.append({
                'phrase': m.group(),
                'category': 'hedge',
                'sentence': sentence,
                'position': m.start(),
                'suggestion': suggestion,
            })

    # ── 영어 hedge (사전 컴파일 패턴 사용) ──
    for phrase, suggestion in _EN_HEDGES.items():
        for m in _EN_HEDGE_PATTERNS[phrase].finditer(sentence):
            detections.append({
                'phrase': m.group(),
                'category': 'hedge',
                'sentence': sentence,
                'position': m.start(),
                'suggestion': suggestion,
            })

    return detections


_EMPTY_RESULT = {
    'detections': [],
    'summary': {
        'total_fillers': 0,
        'total_hedges': 0,
        'filler_ratio': 0.0,
        'hedge_ratio': 0.0,
        'clarity_score': 100.0,
    },
    'worst_sentences': [],
    'suggestions': [],
}


def _aggregate_detections(all_detections: list, total_sentences: int) -> tuple:
    """감지 결과를 집계하여 통계와 최악의 문장을 반환합니다.

    Returns:
        (total_fillers, total_hedges, filler_ratio, hedge_ratio, clarity_score, worst_sentences)
    """
    total_fillers = sum(1 for d in all_detections if d['category'] == 'filler')
    total_hedges = sum(1 for d in all_detections if d['category'] == 'hedge')

    filler_sentences = set()
    hedge_sentences = set()
    sentence_hit_count: Counter = Counter()

    for d in all_detections:
        sentence_hit_count[d['sentence']] += 1
        if d['category'] == 'filler':
            filler_sentences.add(d['sentence'])
        else:
            hedge_sentences.add(d['sentence'])

    filler_ratio = round(len(filler_sentences) / total_sentences, 4) if total_sentences else 0.0
    hedge_ratio = round(len(hedge_sentences) / total_sentences, 4) if total_sentences else 0.0

    total_issues = total_fillers + total_hedges
    if total_sentences > 0:
        avg_issues = total_issues / total_sentences
        clarity_score = max(0.0, min(100.0, round(100.0 - (avg_issues * 25.0), 1)))
    else:
        clarity_score = 100.0

    worst_sentences = [sent for sent, _ in sentence_hit_count.most_common(3)]

    return total_fillers, total_hedges, filler_ratio, hedge_ratio, clarity_score, worst_sentences


def detect_fillers(content: str) -> dict:
    """콘텐츠에서 군더더기(filler)와 헤지(hedge) 표현을 감지합니다.

    Args:
        content: 분석할 콘텐츠 텍스트

    Returns:
        {
            "detections": [{"phrase", "category", "sentence", "position", "suggestion"}],
            "summary": {"total_fillers", "total_hedges", "filler_ratio", "hedge_ratio", "clarity_score"},
            "worst_sentences": list[str],
            "suggestions": list[str],
        }
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        sentences = _split_sentences(content)
        if not sentences:
            return {**_EMPTY_RESULT, 'suggestions': ['유효한 문장이 없습니다.']}

        all_detections = []
        for sent in sentences:
            all_detections.extend(_detect_in_sentence(sent))

        total_fillers, total_hedges, filler_ratio, hedge_ratio, clarity_score, worst_sentences = (
            _aggregate_detections(all_detections, len(sentences))
        )

        suggestions = _generate_suggestions(total_fillers, total_hedges, clarity_score, all_detections)

        return {
            'detections': all_detections,
            'summary': {
                'total_fillers': total_fillers,
                'total_hedges': total_hedges,
                'filler_ratio': filler_ratio,
                'hedge_ratio': hedge_ratio,
                'clarity_score': clarity_score,
            },
            'worst_sentences': worst_sentences,
            'suggestions': suggestions,
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}



def _generate_suggestions(total_fillers: int, total_hedges: int,
                           clarity_score: float, detections: list) -> list[str]:
    """감지 결과 기반 개선 제안을 생성합니다."""
    suggestions = []

    if total_fillers == 0 and total_hedges == 0:
        suggestions.append('군더더기 표현이 감지되지 않았습니다. 깔끔한 글입니다!')
        return suggestions

    if total_fillers > 0:
        # 가장 빈번한 filler 찾기
        filler_phrases = [d['phrase'] for d in detections if d['category'] == 'filler']
        most_common_filler = Counter(filler_phrases).most_common(1)[0]
        suggestions.append(
            f'군더더기 표현 {total_fillers}개 감지. '
            f'가장 빈번: "{most_common_filler[0]}" ({most_common_filler[1]}회) — 삭제를 권장합니다.'
        )

    if total_hedges > 0:
        hedge_phrases = [d['phrase'] for d in detections if d['category'] == 'hedge']
        most_common_hedge = Counter(hedge_phrases).most_common(1)[0]
        suggestions.append(
            f'헤지 표현 {total_hedges}개 감지. '
            f'가장 빈번: "{most_common_hedge[0]}" ({most_common_hedge[1]}회) — 단정적 표현으로 강화하세요.'
        )

    if clarity_score < 50:
        suggestions.append('명확성 점수가 낮습니다. 불필요한 수식어를 대폭 줄여보세요.')
    elif clarity_score < 75:
        suggestions.append('명확성을 높이려면 군더더기와 헤지 표현을 줄여보세요.')

    return suggestions
