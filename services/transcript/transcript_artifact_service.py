"""
자막 아티팩트 감지 서비스

유튜브 자막 전사에서 남은 아티팩트(구독 요청, 스폰서 멘트,
인사말, 말고침 등)를 규칙 기반으로 감지합니다.
"""
import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# --- 아티팩트 감지 패턴 정의 ---

_ARTIFACT_PATTERNS = {
    'greeting': {
        'patterns': [
            re.compile(r'안녕하세요', re.IGNORECASE),
            re.compile(r'여러분', re.IGNORECASE),
            re.compile(r'반갑습니다', re.IGNORECASE),
            re.compile(r'\bhi\s+everyone\b', re.IGNORECASE),
            re.compile(r'\bwelcome\b', re.IGNORECASE),
            re.compile(r'\bhello\b', re.IGNORECASE),
            re.compile(r'안녕하십니까', re.IGNORECASE),
        ],
        'removable': True,
    },
    'subscribe_cta': {
        'patterns': [
            re.compile(r'구독', re.IGNORECASE),
            re.compile(r'좋아요', re.IGNORECASE),
            re.compile(r'알림', re.IGNORECASE),
            re.compile(r'\bsubscribe\b', re.IGNORECASE),
            re.compile(r'\blike\b', re.IGNORECASE),
            re.compile(r'\bbell\b', re.IGNORECASE),
            re.compile(r'눌러\s*주세요', re.IGNORECASE),
        ],
        'removable': True,
    },
    'sponsor': {
        'patterns': [
            re.compile(r'스폰서', re.IGNORECASE),
            re.compile(r'협찬', re.IGNORECASE),
            re.compile(r'광고', re.IGNORECASE),
            re.compile(r'\bsponsored\b', re.IGNORECASE),
            re.compile(r'이\s*영상은.*후원', re.IGNORECASE),
            re.compile(r'제공받', re.IGNORECASE),
        ],
        'removable': True,
    },
    'filler_speech': {
        'patterns': [
            # 한국어 말더듬 — 단독 또는 반복 패턴
            re.compile(r'(?<![가-힣a-zA-Z])(?:음+|어+|그+|아+)(?![가-힣a-zA-Z])', re.IGNORECASE),
            # 영어 filler words
            re.compile(r'\b(?:um|uh|er)\b', re.IGNORECASE),
            # 영어 "like" filler — 문장 중간에 독립적으로 쓰인 경우
            re.compile(r',\s*like\s*,', re.IGNORECASE),
        ],
        'removable': False,
    },
    'self_reference': {
        'patterns': [
            re.compile(r'제\s*채널', re.IGNORECASE),
            re.compile(r'이\s*영상', re.IGNORECASE),
            re.compile(r'다음\s*영상', re.IGNORECASE),
            re.compile(r'이전\s*영상', re.IGNORECASE),
            re.compile(r'링크는?\s*설명란', re.IGNORECASE),
            re.compile(r'\bmy\s+channel\b', re.IGNORECASE),
            re.compile(r'\bthis\s+video\b', re.IGNORECASE),
        ],
        'removable': False,
    },
    'timestamp_marker': {
        'patterns': [
            # [00:00] 또는 (12:34) 형식
            re.compile(r'[\[\(]\d{1,2}:\d{2}[\]\)]'),
            # HH:MM:SS 형식
            re.compile(r'(?<![a-zA-Z0-9])\d{1,2}:\d{2}:\d{2}(?![a-zA-Z0-9])'),
        ],
        'removable': True,
    },
}


_EMPTY_RESULT = {
    'artifacts': [],
    'summary': {'total': 0, 'by_type': {}, 'artifact_ratio': 0.0},
    'clean_score': 100.0,
    'suggestions': [],
}


def _scan_artifacts(sentences: list) -> list:
    """문장 목록에서 아티팩트를 감지합니다."""
    artifacts = []
    for sentence in sentences:
        for artifact_type, config in _ARTIFACT_PATTERNS.items():
            for pattern in config['patterns']:
                match = pattern.search(sentence)
                if match:
                    artifacts.append({
                        'type': artifact_type,
                        'text': match.group(),
                        'sentence': sentence,
                        'removable': config['removable'],
                    })
                    break
    return artifacts


def detect_transcript_artifacts(content: str) -> dict:
    """자막 전사에서 아티팩트를 감지합니다.

    Args:
        content: 분석할 자막 텍스트

    Returns:
        artifacts, summary, clean_score, suggestions를 포함하는 dict
    """
    if not content or not content.strip():
        return {**_EMPTY_RESULT, 'suggestions': ['콘텐츠가 비어 있습니다.']}

    sentences = _split_sentences(content)
    total_sentences = len(sentences) if sentences else 1
    artifacts = _scan_artifacts(sentences)
    type_counts = Counter(a['type'] for a in artifacts)
    clean_score = _calculate_clean_score(artifacts, total_sentences)

    return {
        'artifacts': artifacts,
        'summary': {
            'total': len(artifacts),
            'by_type': dict(type_counts),
            'artifact_ratio': round(len(artifacts) / total_sentences, 4),
        },
        'clean_score': clean_score,
        'suggestions': _generate_suggestions(artifacts, type_counts, clean_score),
    }


def _split_sentences(content: str) -> list:
    """콘텐츠를 문장 단위로 분리합니다."""
    # 마침표, 느낌표, 물음표, 줄바꿈으로 분리
    raw = re.split(r'(?<=[.!?。])\s+|\n+', content)
    return [s.strip() for s in raw if s.strip()]


def _calculate_clean_score(artifacts: list, total_sentences: int) -> float:
    """아티팩트 수와 심각도를 기반으로 클린 스코어를 계산합니다.

    - removable 아티팩트: 건당 -8점
    - non-removable 아티팩트: 건당 -3점
    - 최소 0, 최대 100
    """
    if not artifacts:
        return 100.0

    penalty = 0.0
    for a in artifacts:
        if a['removable']:
            penalty += 8.0
        else:
            penalty += 3.0

    score = max(0.0, 100.0 - penalty)
    return round(score, 1)


def _generate_suggestions(artifacts: list, type_counts: Counter, clean_score: float) -> list:
    """감지 결과를 기반으로 개선 제안을 생성합니다."""
    suggestions = []

    if not artifacts:
        suggestions.append('아티팩트가 감지되지 않았습니다. 자막이 깨끗합니다.')
        return suggestions

    if type_counts.get('greeting', 0) > 0:
        suggestions.append('인사말이 감지되었습니다. 블로그 콘텐츠에서는 제거를 권장합니다.')

    if type_counts.get('subscribe_cta', 0) > 0:
        suggestions.append('구독/좋아요 요청이 포함되어 있습니다. 글 형식 콘텐츠에서는 제거하세요.')

    if type_counts.get('sponsor', 0) > 0:
        suggestions.append('스폰서/광고 멘트가 감지되었습니다. 별도 표기하거나 제거를 고려하세요.')

    if type_counts.get('filler_speech', 0) > 2:
        suggestions.append('말더듬/말고침이 다수 감지되었습니다. 가독성을 위해 정리를 권장합니다.')

    if type_counts.get('self_reference', 0) > 0:
        suggestions.append('채널/영상 자기 참조가 있습니다. 글 형식에 맞게 수정을 권장합니다.')

    if type_counts.get('timestamp_marker', 0) > 0:
        suggestions.append('타임스탬프 마커가 남아있습니다. 자동 제거 가능합니다.')

    if clean_score < 50:
        suggestions.append('클린 스코어가 낮습니다. 자막 전처리 후 콘텐츠를 생성하세요.')

    return suggestions
