"""
출처 서명(Provenance Stamp) 서비스

콘텐츠에 SHA256 해시 기반 출처 서명과 보이지 않는 유니코드(zero-width)
워터마크를 삽입하여, 이후 서명을 검증할 수 있게 합니다.
순수 파이썬, AI API 호출 없음.
"""
import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class ProvenanceRecord:
    """출처 서명 레코드."""
    stamp_id: str
    content_hash: str
    author: str
    model: str
    created_at: str
    watermark: str


# ── Zero-Width 유니코드 문자 ──
# 0 → ZWSP (U+200B), 1 → ZWNJ (U+200C)
_ZW_ZERO = '\u200b'  # Zero-Width Space
_ZW_ONE = '\u200c'   # Zero-Width Non-Joiner
_ZW_SEPARATOR = '\u200d'  # Zero-Width Joiner (비트열 구분자)
_ZW_PREFIX = '\u2060'  # Word Joiner (워터마크 시작 마커)
_ZW_SUFFIX = '\ufeff'  # Zero-Width No-Break Space (워터마크 끝 마커)


def _text_to_binary(text: str) -> str:
    """텍스트를 이진 문자열로 변환합니다."""
    return ''.join(format(b, '08b') for b in text.encode('utf-8'))


def _binary_to_text(binary: str) -> str:
    """이진 문자열을 텍스트로 복원합니다."""
    if len(binary) % 8 != 0:
        return ''
    byte_chunks = [binary[i:i + 8] for i in range(0, len(binary), 8)]
    try:
        return bytes(int(b, 2) for b in byte_chunks).decode('utf-8')
    except (ValueError, UnicodeDecodeError):
        return ''


def _encode_watermark(stamp_id: str) -> str:
    """stamp_id를 zero-width 유니코드 워터마크로 인코딩합니다."""
    binary = _text_to_binary(stamp_id)
    zw_chars = []
    for bit in binary:
        zw_chars.append(_ZW_ONE if bit == '1' else _ZW_ZERO)
    return _ZW_PREFIX + ''.join(zw_chars) + _ZW_SUFFIX


def _decode_watermark(watermark_str: str) -> str:
    """zero-width 유니코드 워터마크에서 stamp_id를 복원합니다."""
    # PREFIX와 SUFFIX 사이의 내용 추출
    start = watermark_str.find(_ZW_PREFIX)
    end = watermark_str.find(_ZW_SUFFIX, start + 1) if start >= 0 else -1

    if start < 0 or end < 0:
        return ''

    inner = watermark_str[start + 1:end]

    # zero-width 문자를 이진 문자열로 변환
    binary = []
    for ch in inner:
        if ch == _ZW_ZERO:
            binary.append('0')
        elif ch == _ZW_ONE:
            binary.append('1')
        # 다른 문자는 무시

    return _binary_to_text(''.join(binary))


def _compute_hash(content: str) -> str:
    """콘텐츠의 SHA256 해시를 계산합니다."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


def _strip_watermark(content: str) -> str:
    """콘텐츠에서 워터마크 문자를 제거합니다."""
    zw_chars = {_ZW_ZERO, _ZW_ONE, _ZW_SEPARATOR, _ZW_PREFIX, _ZW_SUFFIX}
    return ''.join(ch for ch in content if ch not in zw_chars)


def stamp_provenance(
    content: str,
    author: str = 'AI',
    model: str = '',
) -> ProvenanceRecord:
    """콘텐츠에 출처 서명을 생성합니다.

    Args:
        content: 서명할 콘텐츠
        author: 작성자 (기본: 'AI')
        model: 사용된 모델명

    Returns:
        ProvenanceRecord (watermark 필드에 삽입용 워터마크 문자열 포함)
    """
    # 워터마크 제거 후 해시 (이미 워터마크가 있을 수 있으므로)
    clean_content = _strip_watermark(content)
    content_hash = _compute_hash(clean_content)
    stamp_id = uuid.uuid4().hex[:16]
    created_at = datetime.now(timezone.utc).isoformat()
    watermark = _encode_watermark(stamp_id)

    return ProvenanceRecord(
        stamp_id=stamp_id,
        content_hash=content_hash,
        author=author,
        model=model,
        created_at=created_at,
        watermark=watermark,
    )


def verify_stamp(content: str) -> ProvenanceRecord | None:
    """콘텐츠에서 워터마크를 추출하여 서명을 검증합니다.

    Args:
        content: 워터마크가 포함된 콘텐츠

    Returns:
        ProvenanceRecord (검증 성공 시) 또는 None (워터마크 없음)
    """
    if not content:
        return None

    stamp_id = _decode_watermark(content)
    if not stamp_id:
        return None

    # 워터마크 제거 후 해시 계산
    clean_content = _strip_watermark(content)
    content_hash = _compute_hash(clean_content)

    return ProvenanceRecord(
        stamp_id=stamp_id,
        content_hash=content_hash,
        author='',  # 검증 시에는 작성자 정보 복원 불가
        model='',
        created_at='',
        watermark=_encode_watermark(stamp_id),
    )
