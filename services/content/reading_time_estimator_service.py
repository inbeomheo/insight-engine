"""
콘텐츠 읽기 시간 추정 서비스

언어별(ko/en/ja) WPM/CPM 평균값을 기반으로 읽는 데 걸리는 시간을 추정합니다.
이미지·코드 블록·표·인용 등 비문장 요소의 추가 시간도 반영합니다.
"""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# 언어별 읽기 속도(성인 기준 평균)
# - ko: 평균 500자/분 (한국 독서연구소 메타분석 기반)
# - en: 평균 238단어/분 (Brysbaert, 2019)
# - ja: 평균 600자/분 (히라가나/가타카나 포함)
LANGUAGE_SPEEDS = {
    'ko': {'unit': 'chars', 'speed_per_min': 500, 'label': '한국어'},
    'en': {'unit': 'words', 'speed_per_min': 238, 'label': 'English'},
    'ja': {'unit': 'chars', 'speed_per_min': 600, 'label': '日本語'},
}

# 비문장 요소의 추가 읽기 시간(초)
ELEMENT_OVERHEAD_SEC = {
    'image': 12,       # 이미지 1개당 평균 12초 (Medium 벤치마크)
    'code_block': 30,  # 코드 블록 1개당 30초 (이해 포함)
    'table_row': 5,    # 테이블 행 1개당 5초
    'blockquote': 3,   # 인용 1개당 3초
}

_IMAGE_PATTERN = re.compile(r'!\[[^\]]*\]\([^)]+\)')
_CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```|~~~[\s\S]*?~~~')
_INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')
_TABLE_ROW_PATTERN = re.compile(r'^\s*\|.+\|\s*$', re.MULTILINE)
_BLOCKQUOTE_PATTERN = re.compile(r'^>\s+.+$', re.MULTILINE)
_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\([^)]+\)')
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+', re.MULTILINE)
_BOLD_ITALIC_PATTERN = re.compile(r'[*_]{1,3}([^*_]+)[*_]{1,3}')
_HTML_TAG_PATTERN = re.compile(r'<[^>]+>')
# 표의 구분선(| --- | --- |)만 제거 (실제 데이터 행의 내용은 유지)
_TABLE_SEPARATOR_PATTERN = re.compile(r'^\s*\|?[\s:\-|]+\|?\s*$', re.MULTILINE)


def estimate_reading_time(
    content: str,
    language: str = 'ko',
    wpm_override: Optional[int] = None,
) -> dict:
    """콘텐츠의 예상 읽기 시간을 추정합니다.

    Args:
        content: 마크다운 또는 일반 텍스트 콘텐츠.
        language: 'ko', 'en', 'ja' 중 하나. 기본 'ko'.
        wpm_override: 사용자 지정 속도(단어/분 또는 글자/분). 지정 시 기본값 대체.

    Returns:
        {
            'language': str,
            'unit': 'chars' | 'words',
            'total_units': int,
            'speed_per_min': int,
            'base_seconds': int,          # 텍스트만 읽는 시간
            'overhead_seconds': int,      # 이미지/코드/표 오버헤드
            'total_seconds': int,
            'minutes': int,               # 올림
            'display': str,               # '약 3분' / 'about 3 min'
            'elements': {
                'images': int,
                'code_blocks': int,
                'table_rows': int,
                'blockquotes': int,
            },
        }
    """
    if not content or not content.strip():
        return _empty_result(language)

    lang_cfg = LANGUAGE_SPEEDS.get(language, LANGUAGE_SPEEDS['ko'])
    speed = wpm_override if wpm_override and wpm_override > 0 else lang_cfg['speed_per_min']

    elements = _count_elements(content)
    text_only = _strip_non_text(content)

    if lang_cfg['unit'] == 'words':
        units = len([w for w in re.split(r'\s+', text_only) if w])
    else:
        units = len([c for c in text_only if not c.isspace()])

    base_seconds = round(units / speed * 60) if speed > 0 else 0
    overhead_seconds = (
        elements['images'] * ELEMENT_OVERHEAD_SEC['image']
        + elements['code_blocks'] * ELEMENT_OVERHEAD_SEC['code_block']
        + elements['table_rows'] * ELEMENT_OVERHEAD_SEC['table_row']
        + elements['blockquotes'] * ELEMENT_OVERHEAD_SEC['blockquote']
    )
    total_seconds = base_seconds + overhead_seconds
    minutes = max(1, -(-total_seconds // 60)) if total_seconds else 0

    return {
        'language': language,
        'unit': lang_cfg['unit'],
        'total_units': units,
        'speed_per_min': speed,
        'base_seconds': base_seconds,
        'overhead_seconds': overhead_seconds,
        'total_seconds': total_seconds,
        'minutes': minutes,
        'display': _format_display(minutes, language),
        'elements': elements,
    }


def _count_elements(content: str) -> dict:
    """콘텐츠에서 비문장 요소 개수를 셉니다."""
    code_blocks = len(_CODE_BLOCK_PATTERN.findall(content))
    # 코드 블록 내부는 이미지/표 카운트에서 제외
    stripped = _CODE_BLOCK_PATTERN.sub('', content)
    return {
        'images': len(_IMAGE_PATTERN.findall(stripped)),
        'code_blocks': code_blocks,
        'table_rows': len(_TABLE_ROW_PATTERN.findall(stripped)),
        'blockquotes': len(_BLOCKQUOTE_PATTERN.findall(stripped)),
    }


def _strip_non_text(content: str) -> str:
    """글자/단어 수 계산을 위해 비문장 요소를 제거합니다.

    표/인용/제목 마크업 문자(`|`, `>`, `#`)는 제거하되 내부 텍스트는 유지합니다.
    오버헤드로 별도 계산하는 요소(이미지·코드블록 전체)는 통째로 제거합니다.
    """
    text = _CODE_BLOCK_PATTERN.sub(' ', content)
    text = _INLINE_CODE_PATTERN.sub(' ', text)
    text = _IMAGE_PATTERN.sub(' ', text)
    text = _LINK_PATTERN.sub(r'\1', text)  # 링크 텍스트는 유지
    text = _HEADING_PATTERN.sub('', text)
    text = _BOLD_ITALIC_PATTERN.sub(r'\1', text)
    text = _HTML_TAG_PATTERN.sub(' ', text)
    # 표 구분선 제거 (셀 텍스트는 유지)
    text = _TABLE_SEPARATOR_PATTERN.sub('', text)
    # 남은 구조 문자(|, >)는 공백으로 치환하여 단어 수 왜곡 방지
    text = re.sub(r'[|>]', ' ', text)
    return text


def _format_display(minutes: int, language: str) -> str:
    """사용자 노출용 문자열을 생성합니다."""
    if minutes == 0:
        if language == 'en':
            return 'less than 1 min'
        if language == 'ja':
            return '1分未満'
        return '1분 미만'
    if language == 'en':
        return f'about {minutes} min read'
    if language == 'ja':
        return f'約{minutes}分'
    return f'약 {minutes}분'


def _empty_result(language: str) -> dict:
    lang_cfg = LANGUAGE_SPEEDS.get(language, LANGUAGE_SPEEDS['ko'])
    return {
        'language': language,
        'unit': lang_cfg['unit'],
        'total_units': 0,
        'speed_per_min': lang_cfg['speed_per_min'],
        'base_seconds': 0,
        'overhead_seconds': 0,
        'total_seconds': 0,
        'minutes': 0,
        'display': _format_display(0, language),
        'elements': {'images': 0, 'code_blocks': 0, 'table_rows': 0, 'blockquotes': 0},
    }


def get_supported_languages() -> list:
    """지원 언어 목록을 반환합니다."""
    return [
        {'code': code, 'label': cfg['label'], 'unit': cfg['unit'],
         'speed_per_min': cfg['speed_per_min']}
        for code, cfg in LANGUAGE_SPEEDS.items()
    ]
