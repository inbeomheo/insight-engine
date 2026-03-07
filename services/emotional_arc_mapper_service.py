"""
Emotional Arc Mapper 서비스

콘텐츠의 감정 흐름(arc)을 섹션별로 추적합니다.
긍정/부정/중립 감정의 변화를 시각화 데이터로 제공합니다.
규칙 기반 (AI API 호출 없음).
"""
import re
from typing import List, Dict

_HEADING_RE = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')

# 긍정 감정 키워드
_POSITIVE_KO = re.compile(
    r'(?:좋은|훌륭한|뛰어난|효과적|성공|장점|개선|발전|향상|유용|편리|'
    r'쉬운|빠른|안전|만족|추천|감사|기쁜|행복|긍정|최적|완벽)'
)
_POSITIVE_EN = re.compile(
    r'\b(?:good|great|excellent|effective|success|advantage|improve|'
    r'useful|easy|fast|safe|recommend|happy|positive|optimal|perfect|'
    r'best|benefit|powerful|amazing)\b', re.IGNORECASE
)

# 부정 감정 키워드
_NEGATIVE_KO = re.compile(
    r'(?:나쁜|위험|실패|단점|문제|어려운|복잡|느린|불편|부족|'
    r'주의|경고|오류|버그|손실|피해|불안|걱정|부정|취약)'
)
_NEGATIVE_EN = re.compile(
    r'\b(?:bad|dangerous|fail|disadvantage|problem|difficult|complex|'
    r'slow|issue|lack|warning|error|bug|loss|risk|concern|negative|'
    r'vulnerable|worst|critical)\b', re.IGNORECASE
)


def _split_sections(content: str) -> List[Dict]:
    """콘텐츠를 섹션(헤딩 기준)으로 분할합니다."""
    headings = list(_HEADING_RE.finditer(content))

    if not headings:
        return [{'title': '(전체)', 'text': content}]

    sections = []
    for i, match in enumerate(headings):
        title = match.group(2).strip()
        start = match.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(content)
        text = content[start:end].strip()
        if text:
            sections.append({'title': title, 'text': text})

    return sections if sections else [{'title': '(전체)', 'text': content}]


def _score_sentiment(text: str) -> Dict:
    """텍스트의 감정 점수를 산출합니다."""
    pos_ko = len(_POSITIVE_KO.findall(text))
    pos_en = len(_POSITIVE_EN.findall(text))
    neg_ko = len(_NEGATIVE_KO.findall(text))
    neg_en = len(_NEGATIVE_EN.findall(text))

    positive = pos_ko + pos_en
    negative = neg_ko + neg_en
    total = positive + negative

    if total == 0:
        return {'positive': 0, 'negative': 0, 'sentiment': 0.0, 'tone': 'neutral'}

    # -1.0 (매우 부정) ~ +1.0 (매우 긍정)
    sentiment = round((positive - negative) / total, 2)

    if sentiment > 0.3:
        tone = 'positive'
    elif sentiment < -0.3:
        tone = 'negative'
    else:
        tone = 'neutral'

    return {'positive': positive, 'negative': negative,
            'sentiment': sentiment, 'tone': tone}


def map_emotional_arc(content: str) -> dict:
    """콘텐츠의 감정 흐름을 매핑합니다.

    Returns:
        arc, summary, score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'arc': [],
            'summary': {'total_sections': 0, 'overall_tone': 'neutral',
                        'overall_sentiment': 0.0, 'arc_pattern': 'flat'},
            'score': 50.0,
            'suggestions': ['콘텐츠가 비어 있습니다.'],
        }

    sections = _split_sections(content)

    arc = []
    sentiments = []
    for i, section in enumerate(sections):
        scores = _score_sentiment(section['text'])
        arc.append({
            'section': i + 1,
            'title': section['title'] if len(section['title']) <= 40
                     else section['title'][:37] + '...',
            'positive': scores['positive'],
            'negative': scores['negative'],
            'sentiment': scores['sentiment'],
            'tone': scores['tone'],
        })
        sentiments.append(scores['sentiment'])

    # 전체 감정
    avg_sentiment = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0.0
    if avg_sentiment > 0.3:
        overall_tone = 'positive'
    elif avg_sentiment < -0.3:
        overall_tone = 'negative'
    else:
        overall_tone = 'neutral'

    # 아크 패턴 감지
    arc_pattern = _detect_pattern(sentiments)

    # 점수: 감정 변화의 역동성
    score = _calculate_score(sentiments, arc_pattern)

    suggestions = _generate_suggestions(arc, overall_tone, arc_pattern, sentiments)

    return {
        'arc': arc,
        'summary': {
            'total_sections': len(sections),
            'overall_tone': overall_tone,
            'overall_sentiment': avg_sentiment,
            'arc_pattern': arc_pattern,
        },
        'score': score,
        'suggestions': suggestions,
    }


def _detect_pattern(sentiments: List[float]) -> str:
    """감정 흐름 패턴을 감지합니다."""
    if len(sentiments) < 2:
        return 'flat'

    # 추세 분석
    increasing = all(sentiments[i] <= sentiments[i + 1]
                     for i in range(len(sentiments) - 1))
    decreasing = all(sentiments[i] >= sentiments[i + 1]
                     for i in range(len(sentiments) - 1))

    if increasing:
        return 'ascending'  # 점진적 긍정
    if decreasing:
        return 'descending'  # 점진적 부정

    # 변동폭 체크
    max_s = max(sentiments)
    min_s = min(sentiments)
    spread = max_s - min_s

    if spread < 0.2:
        return 'flat'  # 평탄
    if spread > 0.8:
        return 'dramatic'  # 극적 변화

    # V자 또는 역V자
    mid = len(sentiments) // 2
    first_half = sentiments[:mid + 1]
    second_half = sentiments[mid:]

    if min(first_half) < min(second_half) and max(second_half) > max(first_half):
        return 'v_shape'  # 위기→회복
    if max(first_half) > max(second_half) and min(second_half) < min(first_half):
        return 'inverted_v'  # 절정→하강

    return 'fluctuating'  # 변동


def _calculate_score(sentiments: List[float], pattern: str) -> float:
    if not sentiments:
        return 50.0

    # 역동적 흐름이 좋은 글
    spread = max(sentiments) - min(sentiments) if len(sentiments) > 1 else 0

    score = 60.0

    # 변화가 있으면 보너스
    if 0.3 <= spread <= 1.0:
        score += 20.0
    elif spread > 1.0:
        score += 10.0  # 너무 극적

    # 패턴 보너스
    if pattern in ('ascending', 'v_shape'):
        score += 15.0  # 스토리텔링에 유리
    elif pattern == 'flat':
        score -= 10.0  # 단조로움

    return round(max(0.0, min(100.0, score)), 1)


def _generate_suggestions(arc: List[Dict], tone: str, pattern: str,
                           sentiments: List[float]) -> List[str]:
    suggestions = []
    pattern_labels = {
        'flat': '평탄 (감정 변화 없음)',
        'ascending': '상승 (점진적 긍정)',
        'descending': '하강 (점진적 부정)',
        'v_shape': 'V자 (위기→회복)',
        'inverted_v': '역V자 (절정→하강)',
        'dramatic': '극적 변동',
        'fluctuating': '변동',
    }
    suggestions.append(f'감정 아크 패턴: {pattern_labels.get(pattern, pattern)}.')

    if pattern == 'flat':
        suggestions.append(
            '감정 변화가 적어 단조롭습니다. '
            '문제 제기→해결, 위기→극복 등 서사를 추가하세요.'
        )
    elif pattern == 'descending':
        suggestions.append(
            '점점 부정적으로 끝납니다. '
            '결론부에 긍정적 전망이나 해결책을 추가하세요.'
        )

    negative_sections = [a for a in arc if a['tone'] == 'negative']
    if negative_sections:
        names = ', '.join(f'"{s["title"]}"' for s in negative_sections[:2])
        suggestions.append(f'부정 톤 섹션: {names}.')

    return suggestions
