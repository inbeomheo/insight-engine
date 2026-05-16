"""
발행 전 체크리스트 자동 생성 서비스

콘텐츠를 분석하여 발행 전 확인해야 할 항목을
규칙 기반으로 자동 체크합니다.
"""
import logging
import re
from typing import List

logger = logging.getLogger(__name__)

_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_IMAGE_PATTERN = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
_META_KEYWORDS = re.compile(r'(SEO|메타|키워드|태그|설명|description|title)', re.IGNORECASE)


def _check_item(name: str, label: str, passed: bool, detail: str = '') -> dict:
    """체크리스트 항목을 생성합니다."""
    return {
        'name': name,
        'label': label,
        'passed': passed,
        'detail': detail,
    }


def generate_checklist(content: str, title: str = '',
                       has_meta: bool = False,
                       has_hashtags: bool = False,
                       has_thumbnail: bool = False) -> dict:
    """발행 전 체크리스트를 생성합니다.

    Args:
        content: 콘텐츠 본문
        title: 제목 (빈 문자열이면 미설정)
        has_meta: 메타 디스크립션 설정 여부
        has_hashtags: 해시태그 설정 여부
        has_thumbnail: 대표 이미지 설정 여부

    Returns:
        {
            'items': [{'name': str, 'label': str, 'passed': bool, 'detail': str}],
            'passed_count': int,
            'total_count': int,
            'score': float,
            'ready_to_publish': bool,
        }
    """
    if not content or not content.strip():
        return _empty_result()

    text = content.strip()
    items: List[dict] = []

    # 1) 제목 확인
    has_title = bool(title and title.strip())
    title_length = len(title.strip()) if has_title else 0
    title_ok = 5 <= title_length <= 100
    items.append(_check_item(
        'title', '제목 설정',
        title_ok,
        f'{title_length}자' if has_title else '제목이 없습니다',
    ))

    # 2) 콘텐츠 길이
    char_count = len(text)
    length_ok = char_count >= 300
    items.append(_check_item(
        'content_length', '콘텐츠 최소 길이 (300자)',
        length_ok,
        f'{char_count}자',
    ))

    # 3) 헤딩 구조
    heading_count = len(_HEADING_PATTERN.findall(text))
    items.append(_check_item(
        'headings', '헤딩 구조 포함',
        heading_count >= 1,
        f'{heading_count}개 헤딩',
    ))

    # 4) 이미지 alt 텍스트
    images = _IMAGE_PATTERN.findall(text)
    if images:
        missing_alt = sum(1 for alt, _ in images if not alt.strip())
        alt_ok = missing_alt == 0
        items.append(_check_item(
            'image_alt', '이미지 alt 텍스트',
            alt_ok,
            f'{len(images)}개 이미지, {missing_alt}개 alt 누락' if not alt_ok else f'{len(images)}개 이미지 모두 OK',
        ))

    # 5) 링크 유효성 (빈 링크 확인)
    links = _LINK_PATTERN.findall(text)
    if links:
        empty_links = sum(1 for _, url in links if not url.strip() or url.strip() == '#')
        items.append(_check_item(
            'links', '링크 URL 설정',
            empty_links == 0,
            f'{len(links)}개 링크, {empty_links}개 빈 URL' if empty_links else f'{len(links)}개 링크 모두 OK',
        ))

    # 6) 메타 디스크립션
    items.append(_check_item(
        'meta_description', '메타 디스크립션',
        has_meta,
        '설정됨' if has_meta else '미설정',
    ))

    # 7) 해시태그/태그
    items.append(_check_item(
        'hashtags', '해시태그/태그',
        has_hashtags,
        '설정됨' if has_hashtags else '미설정',
    ))

    # 8) 대표 이미지
    items.append(_check_item(
        'thumbnail', '대표 이미지',
        has_thumbnail,
        '설정됨' if has_thumbnail else '미설정',
    ))

    # 9) 금칙어 확인
    forbidden = ['놀라운', '혁신적', '획기적', '최고의', '게임체인저', '압도적']
    found_forbidden = [w for w in forbidden if w in text]
    items.append(_check_item(
        'forbidden_words', '금칙어 미사용',
        len(found_forbidden) == 0,
        f'발견: {", ".join(found_forbidden)}' if found_forbidden else '없음',
    ))

    # 10) 맞춤법 기본 확인 (연속 공백, 연속 마침표)
    has_double_space = '  ' in text
    has_double_period = '..' in text and '...' not in text
    typo_ok = not has_double_space and not has_double_period
    items.append(_check_item(
        'formatting', '서식 오류 없음',
        typo_ok,
        '연속 공백 발견' if has_double_space else ('연속 마침표 발견' if has_double_period else 'OK'),
    ))

    passed_count = sum(1 for i in items if i['passed'])
    total_count = len(items)
    score = round(passed_count / total_count, 2) if total_count > 0 else 0.0

    return {
        'items': items,
        'passed_count': passed_count,
        'total_count': total_count,
        'score': score,
        'ready_to_publish': score >= 0.7,
    }


def _empty_result() -> dict:
    return {
        'items': [_check_item('content_length', '콘텐츠 존재', False, '콘텐츠가 비어 있습니다')],
        'passed_count': 0,
        'total_count': 1,
        'score': 0.0,
        'ready_to_publish': False,
    }
