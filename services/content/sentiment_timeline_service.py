"""
감성 타임라인 서비스

문단/섹션별 감성을 분석하여 시계열 데이터를 생성합니다.
규칙 기반 감성 사전으로 AI 호출 없이 즉시 처리.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$', re.MULTILINE)

# 감성 사전 (한국어)
_POSITIVE_WORDS = frozenset([
    '좋은', '훌륭', '우수', '뛰어난', '성공', '성장', '발전', '개선',
    '효과적', '유용', '편리', '만족', '추천', '장점', '긍정', '기회',
    '혁신', '돌파', '진전', '향상', '증가', '활성', '강화', '확대',
    '감사', '기쁨', '희망', '낙관', '안정', '균형', '최적', '완벽',
])

_NEGATIVE_WORDS = frozenset([
    '나쁜', '문제', '위험', '실패', '감소', '하락', '악화', '우려',
    '어려움', '불편', '단점', '부정', '한계', '위기', '손실', '피해',
    '부족', '결핍', '지연', '오류', '버그', '취약', '약점', '걱정',
    '불안', '갈등', '충돌', '비판', '반대', '거부', '퇴보', '침체',
])


def _analyze_paragraph_sentiment(text: str) -> dict:
    """단일 문단의 감성을 분석합니다."""
    lower = text.lower()
    words = re.findall(r'[가-힣]{2,}', lower)

    if not words:
        return {'score': 0.0, 'label': 'neutral', 'positive': 0, 'negative': 0}

    pos_count = sum(1 for w in words if w in _POSITIVE_WORDS)
    neg_count = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = len(words)

    # -1.0 (완전 부정) ~ +1.0 (완전 긍정)
    raw_score = (pos_count - neg_count) / max(1, total) * 5  # 증폭 계수
    score = round(max(-1.0, min(1.0, raw_score)), 3)

    if score > 0.1:
        label = 'positive'
    elif score < -0.1:
        label = 'negative'
    else:
        label = 'neutral'

    return {
        'score': score,
        'label': label,
        'positive': pos_count,
        'negative': neg_count,
    }


def analyze_sentiment_timeline(content: str) -> dict:
    """콘텐츠의 감성 타임라인을 분석합니다.

    Returns:
        {
            'timeline': [{'index': int, 'heading': str, 'score': float, 'label': str, ...}],
            'overall': {'score': float, 'label': str},
            'total_sections': int,
            'positive_ratio': float,
            'trend': str,
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()

    # 섹션 분리 (헤딩 또는 빈 줄 기준)
    sections = _split_into_sections(text)

    if not sections:
        return _empty_result()

    timeline = []
    scores = []

    for i, section in enumerate(sections):
        sentiment = _analyze_paragraph_sentiment(section['body'])
        timeline.append({
            'index': i,
            'heading': section['heading'],
            'score': sentiment['score'],
            'label': sentiment['label'],
            'positive': sentiment['positive'],
            'negative': sentiment['negative'],
        })
        scores.append(sentiment['score'])

    # 전체 평균 감성
    avg_score = round(sum(scores) / len(scores), 3) if scores else 0.0
    if avg_score > 0.1:
        overall_label = 'positive'
    elif avg_score < -0.1:
        overall_label = 'negative'
    else:
        overall_label = 'neutral'

    # 긍정 비율
    positive_count = sum(1 for s in scores if s > 0.1)
    positive_ratio = round(positive_count / len(scores), 2) if scores else 0.0

    # 감성 추세 (전반부 vs 후반부)
    trend = _detect_trend(scores)

    return {
        'timeline': timeline,
        'overall': {'score': avg_score, 'label': overall_label},
        'total_sections': len(timeline),
        'positive_ratio': positive_ratio,
        'trend': trend,
    }


def _split_into_sections(text: str) -> List[dict]:
    """콘텐츠를 분석 단위(섹션)로 분리합니다."""
    lines = text.split('\n')
    sections = []
    current_heading = ''
    current_body_lines: List[str] = []

    for line in lines:
        match = _HEADING_PATTERN.match(line)
        if match:
            if current_body_lines:
                body = '\n'.join(current_body_lines).strip()
                if body:
                    sections.append({'heading': current_heading, 'body': body})
            current_heading = match.group(1).strip()
            current_body_lines = []
        else:
            current_body_lines.append(line)

    # 마지막 섹션
    body = '\n'.join(current_body_lines).strip()
    if body:
        sections.append({'heading': current_heading, 'body': body})

    # 섹션이 없으면 문단 단위로 분리
    if not sections:
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        for i, para in enumerate(paragraphs):
            sections.append({'heading': f'문단 {i + 1}', 'body': para})

    return sections


def _detect_trend(scores: List[float]) -> str:
    """감성 추세를 감지합니다."""
    if len(scores) < 2:
        return 'stable'

    mid = len(scores) // 2
    first_half = sum(scores[:mid]) / max(1, mid)
    second_half = sum(scores[mid:]) / max(1, len(scores) - mid)
    diff = second_half - first_half

    if diff > 0.15:
        return 'improving'
    elif diff < -0.15:
        return 'declining'
    return 'stable'


def _empty_result() -> dict:
    return {
        'timeline': [],
        'overall': {'score': 0.0, 'label': 'neutral'},
        'total_sections': 0,
        'positive_ratio': 0.0,
        'trend': 'stable',
    }
