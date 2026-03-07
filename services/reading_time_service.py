"""
읽기 시간 예측 서비스

콘텐츠의 읽기 시간, 난이도, 최적 분량을 계산합니다.
한국어 기준 분당 500자 (영어 200~250 WPM).
"""
import re
import logging
import math

logger = logging.getLogger(__name__)

# 읽기 속도 (분당 글자수)
_READING_SPEEDS = {
    'slow': 350,      # 느린 독자
    'average': 500,    # 평균 독자 (한국어)
    'fast': 700,       # 빠른 독자
}

# 콘텐츠 유형별 읽기 속도 보정
_TYPE_MODIFIERS = {
    'general': 1.0,
    'technical': 0.7,    # 기술 콘텐츠는 30% 느리게
    'casual': 1.2,       # 가벼운 콘텐츠는 20% 빠르게
    'academic': 0.6,     # 학술은 40% 느리게
}


def estimate_reading_time(content: str, content_type: str = 'general') -> dict:
    """콘텐츠의 읽기 시간을 예측합니다.

    Args:
        content: 분석할 콘텐츠
        content_type: 콘텐츠 유형 (general, technical, casual, academic)

    Returns:
        {
            "reading_time": {
                "minutes": int,
                "seconds": int,
                "display": str (예: "3분 20초"),
                "range": {"slow": str, "fast": str},
            },
            "word_stats": {
                "char_count": int,
                "word_count": int,
                "sentence_count": int,
                "paragraph_count": int,
            },
            "difficulty": {
                "level": "easy" | "medium" | "hard",
                "score": int (1~10),
                "factors": list[str],
            },
            "recommendations": list[str],
        }
    """
    if not content or not content.strip():
        return {
            'reading_time': {'minutes': 0, 'seconds': 0, 'display': '0분', 'range': {'slow': '0분', 'fast': '0분'}},
            'word_stats': {'char_count': 0, 'word_count': 0, 'sentence_count': 0, 'paragraph_count': 0},
            'difficulty': {'level': 'easy', 'score': 1, 'factors': []},
            'recommendations': ['콘텐츠가 비어 있습니다.'],
        }

    if content_type not in _TYPE_MODIFIERS:
        content_type = 'general'

    plain = _strip_markdown(content)

    # 통계
    char_count = len(plain)
    words = plain.split()
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r'[.!?。]\s*|\n+', plain) if len(s.strip()) >= 3]
    sentence_count = max(len(sentences), 1)
    paragraphs = [p.strip() for p in plain.split('\n\n') if p.strip()]
    paragraph_count = max(len(paragraphs), 1)

    # 읽기 시간 계산
    modifier = _TYPE_MODIFIERS[content_type]
    reading_times = {}
    for speed_name, cpm in _READING_SPEEDS.items():
        adjusted_cpm = cpm * modifier
        total_seconds = math.ceil(char_count / adjusted_cpm * 60)
        reading_times[speed_name] = total_seconds

    avg_seconds = reading_times['average']
    minutes = avg_seconds // 60
    seconds = avg_seconds % 60

    if minutes == 0:
        display = f'{seconds}초'
    elif seconds == 0:
        display = f'{minutes}분'
    else:
        display = f'{minutes}분 {seconds}초'

    slow_min = math.ceil(reading_times['slow'] / 60)
    fast_min = max(1, reading_times['fast'] // 60)

    # 난이도 분석
    difficulty = _analyze_difficulty(plain, sentences, char_count)

    # 추천
    recommendations = _generate_recommendations(char_count, minutes, difficulty)

    return {
        'reading_time': {
            'minutes': minutes,
            'seconds': seconds,
            'display': display,
            'range': {
                'slow': f'{slow_min}분',
                'fast': f'{fast_min}분',
            },
        },
        'word_stats': {
            'char_count': char_count,
            'word_count': word_count,
            'sentence_count': sentence_count,
            'paragraph_count': paragraph_count,
        },
        'difficulty': difficulty,
        'recommendations': recommendations,
    }


def _analyze_difficulty(text: str, sentences: list, char_count: int) -> dict:
    """콘텐츠 난이도를 분석합니다."""
    score = 5  # 기본 중간
    factors = []

    # 평균 문장 길이
    avg_len = sum(len(s) for s in sentences) / max(len(sentences), 1)
    if avg_len > 50:
        score += 2
        factors.append('문장이 길어 읽기 어렵습니다')
    elif avg_len < 20:
        score -= 1

    # 전문 용어/영문 비율
    english_ratio = len(re.findall(r'[a-zA-Z]{3,}', text)) / max(len(text.split()), 1)
    if english_ratio > 0.15:
        score += 2
        factors.append('영문/전문 용어가 많습니다')

    # 코드 블록 존재
    if '```' in text or re.search(r'`[^`]+`', text):
        score += 1
        factors.append('코드/기술 표현이 포함되어 있습니다')

    # 수식/특수 기호
    if re.search(r'[=<>{}()\[\]]{3,}', text):
        score += 1
        factors.append('수식 또는 특수 기호가 포함되어 있습니다')

    score = max(1, min(10, score))

    if score <= 3:
        level = 'easy'
    elif score <= 6:
        level = 'medium'
    else:
        level = 'hard'

    return {
        'level': level,
        'score': score,
        'factors': factors,
    }


def _generate_recommendations(char_count: int, minutes: int, difficulty: dict) -> list:
    recs = []

    if char_count < 300:
        recs.append('콘텐츠가 짧습니다. SEO를 위해 최소 800자 이상 작성을 권장합니다.')
    elif char_count > 5000:
        recs.append('긴 콘텐츠입니다. 목차(TOC)를 추가하면 탐색이 편리합니다.')

    if minutes >= 10:
        recs.append('읽기 시간이 10분 이상입니다. 핵심 요약을 상단에 배치하세요.')
    elif minutes <= 1:
        recs.append('1분 이내 분량입니다. 더 자세한 내용을 추가하면 좋겠습니다.')

    if difficulty['level'] == 'hard':
        recs.append('난이도가 높습니다. 용어 설명이나 예시를 추가하면 가독성이 향상됩니다.')

    if not recs:
        recs.append('적절한 분량과 난이도입니다.')

    return recs


def _strip_markdown(text: str) -> str:
    text = re.sub(r'#{1,6}\s+', '', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)
    text = re.sub(r'```[\s\S]*?```', '', text)
    text = re.sub(r'`(.+?)`', r'\1', text)
    return text.strip()
