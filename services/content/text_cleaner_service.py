"""
텍스트 정리(Cleaner) 서비스

텍스트 아티팩트를 자동 정리합니다.
스마트 따옴표→일반 따옴표, 인코딩 오류 수정,
이중 공백 제거, 불필요한 유니코드 문자 정리 등.
"""
import logging
import re
import unicodedata

logger = logging.getLogger(__name__)

# 스마트 따옴표 → 일반 따옴표
_SMART_QUOTES = {
    '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
    '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
    '\u201c': '"',  # LEFT DOUBLE QUOTATION MARK
    '\u201d': '"',  # RIGHT DOUBLE QUOTATION MARK
    '\u2032': "'",  # PRIME
    '\u2033': '"',  # DOUBLE PRIME
}

# 특수 대시/하이픈 → 일반 하이픈
_DASHES = {
    '\u2013': '-',  # EN DASH
    '\u2014': '-',  # EM DASH
    '\u2015': '-',  # HORIZONTAL BAR
    '\u2212': '-',  # MINUS SIGN
}

# 특수 공백 → 일반 공백
_SPECIAL_SPACES = {
    '\u00a0': ' ',  # NO-BREAK SPACE
    '\u2002': ' ',  # EN SPACE
    '\u2003': ' ',  # EM SPACE
    '\u2009': ' ',  # THIN SPACE
    '\u200a': ' ',  # HAIR SPACE
    '\u3000': ' ',  # IDEOGRAPHIC SPACE (전각 공백)
}

# 보이지 않는 제어 문자
_INVISIBLE_CHARS = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff\u2060]')


def clean_text(content: str, options: dict = None) -> dict:
    """텍스트 아티팩트를 정리합니다.

    Args:
        content: 원본 텍스트
        options: 정리 옵션 (없으면 전체 적용)
            - smart_quotes: bool (스마트 따옴표 변환)
            - dashes: bool (특수 대시 변환)
            - special_spaces: bool (특수 공백 변환)
            - double_spaces: bool (이중 공백 제거)
            - invisible_chars: bool (보이지 않는 문자 제거)
            - trailing_whitespace: bool (줄 끝 공백 제거)
            - normalize_unicode: bool (유니코드 NFC 정규화)

    Returns:
        {
            'cleaned': str,
            'changes': [{'type': str, 'count': int}],
            'total_changes': int,
            'char_diff': int,
        }
    """
    if not content:
        return {'cleaned': '', 'changes': [], 'total_changes': 0, 'char_diff': 0}

    opts = options or {}
    # 기본: 모든 옵션 활성화
    do_quotes = opts.get('smart_quotes', True)
    do_dashes = opts.get('dashes', True)
    do_spaces = opts.get('special_spaces', True)
    do_double = opts.get('double_spaces', True)
    do_invisible = opts.get('invisible_chars', True)
    do_trailing = opts.get('trailing_whitespace', True)
    do_normalize = opts.get('normalize_unicode', True)

    text = content
    original_len = len(text)
    changes = []

    # 1) 스마트 따옴표
    if do_quotes:
        count = sum(text.count(k) for k in _SMART_QUOTES)
        if count:
            for old, new in _SMART_QUOTES.items():
                text = text.replace(old, new)
            changes.append({'type': 'smart_quotes', 'count': count})

    # 2) 특수 대시
    if do_dashes:
        count = sum(text.count(k) for k in _DASHES)
        if count:
            for old, new in _DASHES.items():
                text = text.replace(old, new)
            changes.append({'type': 'dashes', 'count': count})

    # 3) 특수 공백
    if do_spaces:
        count = sum(text.count(k) for k in _SPECIAL_SPACES)
        if count:
            for old, new in _SPECIAL_SPACES.items():
                text = text.replace(old, new)
            changes.append({'type': 'special_spaces', 'count': count})

    # 4) 보이지 않는 문자
    if do_invisible:
        found = _INVISIBLE_CHARS.findall(text)
        if found:
            text = _INVISIBLE_CHARS.sub('', text)
            changes.append({'type': 'invisible_chars', 'count': len(found)})

    # 5) 이중 공백
    if do_double:
        count = len(re.findall(r'  +', text))
        if count:
            text = re.sub(r'  +', ' ', text)
            changes.append({'type': 'double_spaces', 'count': count})

    # 6) 줄 끝 공백
    if do_trailing:
        count = len(re.findall(r'[ \t]+$', text, re.MULTILINE))
        if count:
            text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
            changes.append({'type': 'trailing_whitespace', 'count': count})

    # 7) 유니코드 NFC 정규화
    if do_normalize:
        normalized = unicodedata.normalize('NFC', text)
        if normalized != text:
            diff_count = sum(1 for a, b in zip(text, normalized) if a != b)
            text = normalized
            if diff_count:
                changes.append({'type': 'unicode_normalize', 'count': diff_count})

    total = sum(c['count'] for c in changes)

    return {
        'cleaned': text,
        'changes': changes,
        'total_changes': total,
        'char_diff': len(text) - original_len,
    }
