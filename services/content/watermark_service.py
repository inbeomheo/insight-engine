"""
콘텐츠 워터마크 서비스

보이지 않는 워터마크(영폭 문자)를 삽입하거나
가시적 출처 표기를 추가합니다.
"""
import hashlib
import logging
import re
import time

logger = logging.getLogger(__name__)

# 영폭 문자 (Zero-Width Characters)
_ZWC_MAP = {
    '0': '\u200b',  # ZERO WIDTH SPACE
    '1': '\u200c',  # ZERO WIDTH NON-JOINER
}

_ZWC_CHARS = frozenset(_ZWC_MAP.values())


def _encode_to_zwc(text: str) -> str:
    """텍스트를 영폭 문자열로 인코딩합니다."""
    binary = ''.join(format(b, '08b') for b in text.encode('utf-8'))
    return ''.join(_ZWC_MAP[bit] for bit in binary)


def _decode_from_zwc(zwc_text: str) -> str:
    """영폭 문자열을 원래 텍스트로 디코딩합니다."""
    bits = []
    for char in zwc_text:
        if char == _ZWC_MAP['0']:
            bits.append('0')
        elif char == _ZWC_MAP['1']:
            bits.append('1')

    if not bits or len(bits) % 8 != 0:
        return ''

    byte_chunks = [bits[i:i+8] for i in range(0, len(bits), 8)]
    try:
        return bytes(int(''.join(chunk), 2) for chunk in byte_chunks).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return ''


def add_invisible_watermark(content: str, identifier: str = '') -> dict:
    """콘텐츠에 보이지 않는 워터마크를 삽입합니다.

    Args:
        content: 원본 콘텐츠
        identifier: 워터마크 식별자 (비우면 자동 생성)

    Returns:
        {
            'watermarked': str,
            'identifier': str,
            'watermark_length': int,
        }
    """
    if not content or not content.strip():
        return {'watermarked': '', 'identifier': '', 'watermark_length': 0}

    if not identifier:
        identifier = hashlib.md5(f'{time.time()}'.encode()).hexdigest()[:8]

    zwc_payload = _encode_to_zwc(identifier)

    # 첫 번째 문단 끝에 삽입
    lines = content.split('\n')
    inserted = False
    result_lines = []
    for line in lines:
        result_lines.append(line)
        if not inserted and line.strip() and not line.strip().startswith('#'):
            result_lines[-1] = line + zwc_payload
            inserted = True

    watermarked = '\n'.join(result_lines)

    return {
        'watermarked': watermarked,
        'identifier': identifier,
        'watermark_length': len(zwc_payload),
    }


def detect_watermark(content: str) -> dict:
    """콘텐츠에서 워터마크를 탐지합니다.

    Returns:
        {
            'has_watermark': bool,
            'identifier': str,
            'zwc_count': int,
        }
    """
    if not content:
        return {'has_watermark': False, 'identifier': '', 'zwc_count': 0}

    # 영폭 문자 추출
    zwc_chars = [c for c in content if c in _ZWC_CHARS]
    if not zwc_chars:
        return {'has_watermark': False, 'identifier': '', 'zwc_count': 0}

    zwc_text = ''.join(zwc_chars)
    identifier = _decode_from_zwc(zwc_text)

    return {
        'has_watermark': bool(identifier),
        'identifier': identifier,
        'zwc_count': len(zwc_chars),
    }


def add_attribution(content: str, author: str = '',
                    source_url: str = '', license_text: str = '') -> dict:
    """콘텐츠에 가시적 출처 표기를 추가합니다.

    Returns:
        {'attributed': str, 'attribution_text': str}
    """
    if not content or not content.strip():
        return {'attributed': '', 'attribution_text': ''}

    parts = []
    if author:
        parts.append(f'작성자: {author}')
    if source_url:
        parts.append(f'출처: {source_url}')
    if license_text:
        parts.append(license_text)

    if not parts:
        return {'attributed': content, 'attribution_text': ''}

    attribution = '\n\n---\n\n' + ' | '.join(parts)
    return {
        'attributed': content.rstrip() + attribution,
        'attribution_text': ' | '.join(parts),
    }
