"""
감정 톤 매퍼 서비스

콘텐츠의 문단별 감정 흐름을 분석하여
감정 곡선(arc)과 톤 분포를 제공합니다.
"""
import re
import logging

logger = logging.getLogger(__name__)

# 감정 사전 (카테고리별 단어 + 강도)
_EMOTION_LEXICON = {
    'joy': {
        'label': '기쁨',
        'words': [
            '기쁘', '행복', '즐거', '좋은', '훌륭', '멋진', '아름다',
            '사랑', '감사', '축하', '성공', '달성', '완벽', '최고',
            '환상', '만족', '기대', '설레', '웃음', '재미',
        ],
    },
    'sadness': {
        'label': '슬픔',
        'words': [
            '슬프', '안타깝', '아쉽', '유감', '눈물', '이별',
            '외로', '고통', '괴로', '우울', '힘든', '어려운',
            '실망', '좌절', '상실', '그리', '서글',
        ],
    },
    'anger': {
        'label': '분노',
        'words': [
            '분노', '화가', '짜증', '열받', '억울', '부당',
            '불공정', '배신', '모욕', '증오', '폭력', '잔혹',
        ],
    },
    'fear': {
        'label': '두려움',
        'words': [
            '두려', '무서', '걱정', '불안', '위험', '공포',
            '긴장', '초조', '겁', '위협', '경고', '주의',
        ],
    },
    'surprise': {
        'label': '놀라움',
        'words': [
            '놀라', '충격', '의외', '반전', '예상', '깜짝',
            '뜻밖', '갑자기', '경이', '신기', '대박', '헐',
        ],
    },
    'trust': {
        'label': '신뢰',
        'words': [
            '믿음', '신뢰', '확신', '보장', '안전', '검증',
            '정확', '사실', '진실', '솔직', '투명', '공정',
        ],
    },
    'anticipation': {
        'label': '기대',
        'words': [
            '기대', '희망', '전망', '미래', '가능성', '잠재',
            '발전', '성장', '기회', '혁신', '변화', '도약',
        ],
    },
    'neutral': {
        'label': '중립',
        'words': [],  # 기본 감정
    },
}


_EMPTY_RESULT = {
    'arc': [],
    'overall': {'dominant_emotion': 'neutral', 'emotion_label': '중립',
                'valence': 0, 'distribution': {}},
    'flow_pattern': 'none',
    'score': 0,
    'suggestions': [],
}


def _analyze_paragraphs(paragraphs: list) -> tuple:
    """문단별 감정을 분석하고 전체 감정을 집계합니다.

    Returns:
        (arc, total_emotions)
    """
    arc = []
    total_emotions = {}

    for idx, para in enumerate(paragraphs):
        emotions = _score_paragraph(para)
        dominant = max(emotions, key=emotions.get) if emotions else 'neutral'
        valence = _calculate_valence(emotions)

        arc.append({
            'index': idx,
            'dominant_emotion': dominant,
            'emotion_label': _EMOTION_LEXICON.get(dominant, {}).get('label', '중립'),
            'valence': round(valence, 2),
            'emotions': emotions,
        })

        for emo, score in emotions.items():
            total_emotions[emo] = total_emotions.get(emo, 0) + score

    return arc, total_emotions


def map_emotional_tone(content: str) -> dict:
    """콘텐츠의 감정 흐름을 매핑합니다.

    Args:
        content: 분석할 콘텐츠

    Returns:
        {
            "arc": [{"index": int, "dominant_emotion": str, "emotion_label": str,
                      "valence": float, "emotions": dict}],
            "overall": {"dominant_emotion": str, "emotion_label": str,
                        "valence": float, "distribution": dict},
            "flow_pattern": str,
            "score": int (0~100),
            "suggestions": list[str],
        }
    """
    try:
        if not content or not content.strip():
            return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

        paragraphs = [p.strip() for p in re.split(r'\n\s*\n|\n', content) if len(p.strip()) >= 5]
        if not paragraphs:
            return {**_EMPTY_RESULT, 'suggestions': ['분석할 문단이 없습니다.']}

        arc, total_emotions = _analyze_paragraphs(paragraphs)

        overall_dominant = max(total_emotions, key=total_emotions.get) if total_emotions else 'neutral'
        total_score = sum(total_emotions.values()) or 1
        distribution = {k: round(v / total_score * 100, 1)
                        for k, v in sorted(total_emotions.items(), key=lambda x: x[1], reverse=True)}
        flow_pattern = _detect_flow_pattern(arc)

        return {
            'arc': arc,
            'overall': {
                'dominant_emotion': overall_dominant,
                'emotion_label': _EMOTION_LEXICON.get(overall_dominant, {}).get('label', '중립'),
                'valence': round(_calculate_valence(total_emotions), 2),
                'distribution': distribution,
            },
            'flow_pattern': flow_pattern,
            'score': _calculate_tone_score(arc, distribution, flow_pattern),
            'suggestions': _generate_suggestions(arc, distribution, flow_pattern),
        }
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        return {"error": str(e)}



def _score_paragraph(text: str) -> dict:
    """문단의 감정 점수를 계산합니다."""
    scores = {}
    for category, data in _EMOTION_LEXICON.items():
        if category == 'neutral':
            continue
        count = 0
        for word in data['words']:
            if word in text:
                count += 1
        if count > 0:
            scores[category] = count

    if not scores:
        scores['neutral'] = 1

    return scores


def _calculate_valence(emotions: dict) -> float:
    """감정의 긍부정 밸런스(-1 ~ +1)를 계산합니다."""
    positive = {'joy', 'trust', 'anticipation', 'surprise'}
    negative = {'sadness', 'anger', 'fear'}

    pos_score = sum(emotions.get(e, 0) for e in positive)
    neg_score = sum(emotions.get(e, 0) for e in negative)
    total = pos_score + neg_score

    if total == 0:
        return 0
    return (pos_score - neg_score) / total


def _detect_flow_pattern(arc: list) -> str:
    """감정 흐름 패턴을 감지합니다."""
    if len(arc) <= 1:
        return 'flat'

    valences = [p['valence'] for p in arc]

    # 변화량 계산
    changes = [valences[i+1] - valences[i] for i in range(len(valences)-1)]

    if all(c >= -0.1 for c in changes):
        return 'rising'       # 점점 긍정적
    elif all(c <= 0.1 for c in changes):
        return 'falling'      # 점점 부정적
    elif len(valences) >= 3:
        mid = len(valences) // 2
        first_half = sum(valences[:mid]) / mid
        second_half = sum(valences[mid:]) / (len(valences) - mid)
        if first_half < second_half - 0.3:
            return 'valley'   # U자형 (부정→긍정)
        elif first_half > second_half + 0.3:
            return 'peak'     # 역U자 (긍정→부정)

    # 변동성 체크
    variance = sum(c**2 for c in changes) / len(changes)
    if variance > 0.3:
        return 'volatile'     # 변동이 큼

    return 'steady'           # 안정적


def _calculate_tone_score(arc: list, distribution: dict, pattern: str) -> int:
    """감정 톤 다양성과 흐름 점수 (0~100)."""
    score = 40

    # 감정 다양성
    emotion_types = len(distribution)
    if emotion_types >= 4:
        score += 20
    elif emotion_types >= 3:
        score += 15
    elif emotion_types >= 2:
        score += 10

    # 흐름 패턴 보너스
    engaging_patterns = {'rising', 'valley'}
    if pattern in engaging_patterns:
        score += 20  # 독자 참여 유도형
    elif pattern == 'steady':
        score += 10
    elif pattern == 'volatile':
        score += 5

    # 중립 비율이 너무 높으면 감점
    neutral_pct = distribution.get('neutral', 0)
    if neutral_pct > 70:
        score -= 15
    elif neutral_pct > 50:
        score -= 5

    return max(0, min(100, score))


def _generate_suggestions(arc: list, distribution: dict, pattern: str) -> list:
    """분석 결과에 따른 제안."""
    suggestions = []

    if len(arc) <= 1:
        suggestions.append('문단이 너무 적어 감정 흐름을 분석하기 어렵습니다.')
        return suggestions

    neutral_pct = distribution.get('neutral', 0)
    if neutral_pct > 60:
        suggestions.append('중립적 톤이 지배적입니다. 감정적 표현을 추가하면 독자 몰입도가 높아집니다.')

    if pattern == 'falling':
        suggestions.append('감정이 점점 부정적으로 흐릅니다. 결론부를 긍정적/희망적으로 마무리해 보세요.')

    if pattern == 'volatile':
        suggestions.append('감정 변화가 급격합니다. 자연스러운 전환을 위해 연결 문장을 추가하세요.')

    if 'joy' not in distribution and 'anticipation' not in distribution:
        suggestions.append('긍정적 감정이 부족합니다. 성공 사례나 희망적 전망을 추가해 보세요.')

    if not suggestions:
        suggestions.append('감정 흐름이 적절합니다.')

    return suggestions
