"""
참고문헌 포맷터 서비스

참고문헌/출처를 다양한 인용 스타일로 포맷팅합니다.
APA 7th, MLA 9th, 시카고, 한국어 학술 스타일 지원.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

SUPPORTED_STYLES = ['apa', 'mla', 'chicago', 'korean']


def format_citation(source: dict, style: str = 'apa') -> dict:
    """단일 출처를 지정 스타일로 포맷팅합니다.

    Args:
        source: {
            'author': str,         # 저자 (필수)
            'title': str,          # 제목 (필수)
            'year': str|int,       # 출판년도
            'url': str,            # URL (웹 소스)
            'publisher': str,      # 출판사
            'journal': str,        # 학술지명
            'volume': str,         # 권
            'pages': str,          # 페이지
            'accessed': str,       # 접근일
        }
        style: 인용 스타일 (apa/mla/chicago/korean)

    Returns:
        {'formatted': str, 'style': str}
    """
    if not source or not isinstance(source, dict):
        return {'formatted': '', 'style': style}

    style = str(style).lower() if style else 'apa'
    if style not in SUPPORTED_STYLES:
        style = 'apa'

    author = str(source.get('author', '') or '')
    title = str(source.get('title', '') or '')
    year = str(source.get('year', '') or '')
    url = str(source.get('url', '') or '')
    publisher = str(source.get('publisher', '') or '')
    journal = str(source.get('journal', '') or '')
    volume = str(source.get('volume', '') or '')
    pages = str(source.get('pages', '') or '')
    accessed = str(source.get('accessed', '') or '')

    if not author and not title:
        return {'formatted': '', 'style': style}

    if style == 'apa':
        formatted = _format_apa(author, title, year, url, publisher, journal, volume, pages)
    elif style == 'mla':
        formatted = _format_mla(author, title, year, url, publisher, journal, volume, pages)
    elif style == 'chicago':
        formatted = _format_chicago(author, title, year, url, publisher, journal, volume, pages)
    else:
        formatted = _format_korean(author, title, year, url, publisher, journal, volume, pages, accessed)

    return {'formatted': formatted.strip(), 'style': style}


def format_bibliography(sources: List[dict], style: str = 'apa') -> dict:
    """여러 출처를 정렬하여 참고문헌 목록을 생성합니다.

    Returns:
        {
            'bibliography': str,
            'entries': [str],
            'total': int,
            'style': str,
        }
    """
    if not sources:
        return {'bibliography': '', 'entries': [], 'total': 0, 'style': style}

    entries = []
    for source in sources:
        result = format_citation(source, style)
        if result['formatted']:
            entries.append(result['formatted'])

    # 알파벳/가나다 순 정렬
    entries.sort()

    bibliography = '\n\n'.join(entries)

    return {
        'bibliography': bibliography,
        'entries': entries,
        'total': len(entries),
        'style': style,
    }


def _format_apa(author, title, year, url, publisher, journal, volume, pages):
    """APA 7th Edition 스타일."""
    parts = []
    if author:
        parts.append(f'{author}.')
    if year:
        parts.append(f'({year}).')
    if title:
        if journal:
            parts.append(f'{title}.')
        else:
            parts.append(f'*{title}*.')
    if journal:
        vol_info = f', *{volume}*' if volume else ''
        page_info = f', {pages}' if pages else ''
        parts.append(f'*{journal}*{vol_info}{page_info}.')
    elif publisher:
        parts.append(f'{publisher}.')
    if url:
        parts.append(url)
    return ' '.join(parts)


def _format_mla(author, title, year, url, publisher, journal, volume, pages):
    """MLA 9th Edition 스타일."""
    parts = []
    if author:
        parts.append(f'{author}.')
    if title:
        if journal:
            parts.append(f'"{title}."')
        else:
            parts.append(f'*{title}*.')
    if journal:
        vol_info = f', vol. {volume}' if volume else ''
        page_info = f', pp. {pages}' if pages else ''
        year_info = f', {year}' if year else ''
        parts.append(f'*{journal}*{vol_info}{year_info}{page_info}.')
    elif publisher:
        parts.append(f'{publisher}, {year}.' if year else f'{publisher}.')
    if url:
        parts.append(url + '.')
    return ' '.join(parts)


def _format_chicago(author, title, year, url, publisher, journal, volume, pages):
    """시카고 스타일 (Notes-Bibliography)."""
    parts = []
    if author:
        parts.append(f'{author}.')
    if title:
        parts.append(f'*{title}*.')
    if publisher and year:
        parts.append(f'{publisher}, {year}.')
    elif year:
        parts.append(f'{year}.')
    if journal:
        vol_info = f' {volume}' if volume else ''
        page_info = f': {pages}' if pages else ''
        year_part = f' ({year})' if year else ''
        parts.append(f'*{journal}*{vol_info}{year_part}{page_info}.')
    if url:
        parts.append(url + '.')
    return ' '.join(parts)


def _format_korean(author, title, year, url, publisher, journal, volume, pages, accessed):
    """한국어 학술 인용 스타일."""
    parts = []
    if author:
        parts.append(f'{author}.')
    if year:
        parts.append(f'({year}).')
    if title:
        parts.append(f'「{title}」.')
    if journal:
        vol_info = f', {volume}권' if volume else ''
        page_info = f', {pages}쪽' if pages else ''
        parts.append(f'『{journal}』{vol_info}{page_info}.')
    elif publisher:
        parts.append(f'{publisher}.')
    if url:
        accessed_info = f' (접근일: {accessed})' if accessed else ''
        parts.append(f'{url}{accessed_info}.')
    return ' '.join(parts)


def get_citation_styles() -> list:
    """지원하는 인용 스타일 목록."""
    return [
        {'id': 'apa', 'name': 'APA 7th Edition', 'description': '미국심리학회 스타일'},
        {'id': 'mla', 'name': 'MLA 9th Edition', 'description': '현대언어학회 스타일'},
        {'id': 'chicago', 'name': 'Chicago', 'description': '시카고 스타일 (Notes-Bibliography)'},
        {'id': 'korean', 'name': '한국어 학술', 'description': '한국 학술지 표준 인용 형식'},
    ]
