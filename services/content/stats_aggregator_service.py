"""
콘텐츠 통계 집계 서비스

여러 콘텐츠의 통계를 일괄 집계합니다.
총 단어수, 평균 읽기 시간, 스타일 분포 등.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_WORD_PATTERN = re.compile(r'[\w가-힣]+')
_KO_CHAR_PATTERN = re.compile(r'[가-힣]')

_READING_SPEED_KO = 500  # 분당 글자


def _content_stats(content: str) -> dict:
    """단일 콘텐츠의 기본 통계."""
    if not content or not content.strip():
        return {'word_count': 0, 'char_count': 0, 'heading_count': 0, 'reading_minutes': 0.0}

    text = content.strip()
    word_count = len(_WORD_PATTERN.findall(text))
    char_count = len(text)
    heading_count = len(_HEADING_PATTERN.findall(text))
    ko_chars = len(_KO_CHAR_PATTERN.findall(text))
    reading_minutes = round(max(0.5, ko_chars / _READING_SPEED_KO), 1)

    return {
        'word_count': word_count,
        'char_count': char_count,
        'heading_count': heading_count,
        'reading_minutes': reading_minutes,
    }


def aggregate_stats(contents: List[dict]) -> dict:
    """여러 콘텐츠의 통계를 집계합니다.

    Args:
        contents: [{'content': str, 'style': str(optional), 'title': str(optional)}, ...]

    Returns:
        {
            'summary': {
                'total_contents': int,
                'total_words': int,
                'total_chars': int,
                'avg_words': float,
                'avg_reading_minutes': float,
                'total_reading_minutes': float,
                'total_headings': int,
            },
            'per_content': [{'title': str, 'word_count': int, ...}],
            'style_distribution': {style: count},
            'length_distribution': {'short': int, 'medium': int, 'long': int},
        }
    """
    if not contents:
        return _empty_result()

    per_content = []
    style_counts = {}
    length_dist = {'short': 0, 'medium': 0, 'long': 0}

    total_words = 0
    total_chars = 0
    total_headings = 0
    total_reading = 0.0

    for idx, item in enumerate(contents):
        content = item.get('content', '')
        title = item.get('title', f'콘텐츠 {idx + 1}')
        style = item.get('style', 'unknown')

        stats = _content_stats(content)
        stats['title'] = title
        stats['style'] = style
        per_content.append(stats)

        total_words += stats['word_count']
        total_chars += stats['char_count']
        total_headings += stats['heading_count']
        total_reading += stats['reading_minutes']

        # 스타일 분포
        style_counts[style] = style_counts.get(style, 0) + 1

        # 길이 분포
        wc = stats['word_count']
        if wc < 200:
            length_dist['short'] += 1
        elif wc < 800:
            length_dist['medium'] += 1
        else:
            length_dist['long'] += 1

    count = len(contents)
    avg_words = round(total_words / count, 1) if count > 0 else 0
    avg_reading = round(total_reading / count, 1) if count > 0 else 0

    return {
        'summary': {
            'total_contents': count,
            'total_words': total_words,
            'total_chars': total_chars,
            'avg_words': avg_words,
            'avg_reading_minutes': avg_reading,
            'total_reading_minutes': round(total_reading, 1),
            'total_headings': total_headings,
        },
        'per_content': per_content,
        'style_distribution': style_counts,
        'length_distribution': length_dist,
    }


def _empty_result() -> dict:
    return {
        'summary': {
            'total_contents': 0, 'total_words': 0, 'total_chars': 0,
            'avg_words': 0, 'avg_reading_minutes': 0, 'total_reading_minutes': 0,
            'total_headings': 0,
        },
        'per_content': [],
        'style_distribution': {},
        'length_distribution': {'short': 0, 'medium': 0, 'long': 0},
    }
