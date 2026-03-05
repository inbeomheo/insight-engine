"""
콘텐츠 지문 서비스 (F10-25)
생성된 콘텐츠에 고유 지문(fingerprint)을 삽입하여 출처 추적
기법: LSB 스테가노그래피(텍스트), 워터마크 패턴 삽입
"""
import hashlib
import json
import logging
import re
import time
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 제로폭 문자 (Zero-Width Characters) — 스테가노그래피 인코딩
ZERO_WIDTH_JOINER = '\u200d'       # 비트 1
ZERO_WIDTH_NON_JOINER = '\u200c'   # 비트 0
ZERO_WIDTH_SPACE = '\u200b'        # 구분자


def _encode_bits(data: str) -> str:
    """
    텍스트를 제로폭 문자 시퀀스로 인코딩 (LSB 스테가노그래피)

    Args:
        data: 인코딩할 데이터 (짧은 문자열)

    Returns:
        제로폭 문자 시퀀스
    """
    bits = ''.join(format(ord(c), '08b') for c in data[:32])  # 최대 32자
    encoded = ZERO_WIDTH_SPACE  # 시작 마커
    for bit in bits:
        encoded += ZERO_WIDTH_JOINER if bit == '1' else ZERO_WIDTH_NON_JOINER
    encoded += ZERO_WIDTH_SPACE  # 종료 마커
    return encoded


def _decode_bits(text: str) -> Optional[str]:
    """제로폭 문자 시퀀스에서 데이터 복원"""
    # 시작/종료 마커 사이 추출
    start = text.find(ZERO_WIDTH_SPACE)
    if start == -1:
        return None
    end = text.find(ZERO_WIDTH_SPACE, start + 1)
    if end == -1:
        return None

    encoded = text[start + 1:end]
    bits = ''
    for char in encoded:
        if char == ZERO_WIDTH_JOINER:
            bits += '1'
        elif char == ZERO_WIDTH_NON_JOINER:
            bits += '0'

    if len(bits) < 8:
        return None

    try:
        chars = [chr(int(bits[i:i+8], 2)) for i in range(0, len(bits) - 7, 8)]
        return ''.join(chars).rstrip('\x00')
    except Exception:
        return None


class FingerprintService:
    """
    콘텐츠 지문 서비스

    기능:
    1. 콘텐츠에 보이지 않는 지문 삽입
    2. 지문 추출 및 출처 확인
    3. 콘텐츠 해시 기반 중복 감지
    """

    def embed(
        self,
        content: str,
        user_id: str,
        content_id: str = '',
        timestamp: Optional[float] = None,
    ) -> Tuple[str, str]:
        """
        콘텐츠에 지문 삽입

        Args:
            content: 원본 콘텐츠
            user_id: 사용자 ID
            content_id: 콘텐츠 고유 ID
            timestamp: 생성 시각 (없으면 현재 시각)

        Returns:
            (지문이 삽입된 콘텐츠, fingerprint_id)
        """
        ts = timestamp or time.time()
        fingerprint_id = self._make_fingerprint_id(user_id, content_id, ts)

        # 지문 데이터 (12자 이내로 압축)
        fp_data = fingerprint_id[:12]
        encoded = _encode_bits(fp_data)

        # 첫 번째 단락 끝에 삽입
        paragraphs = content.split('\n\n')
        if paragraphs:
            paragraphs[0] = paragraphs[0] + encoded
            watermarked = '\n\n'.join(paragraphs)
        else:
            watermarked = content + encoded

        logger.debug("지문 삽입 완료: fingerprint_id=%s", fingerprint_id)
        return watermarked, fingerprint_id

    def extract(self, content: str) -> Optional[str]:
        """
        콘텐츠에서 지문 추출

        Returns:
            fingerprint_id (없으면 None)
        """
        decoded = _decode_bits(content)
        if decoded:
            logger.debug("지문 추출 성공: %s", decoded)
        return decoded

    def verify(self, content: str, expected_fingerprint_id: str) -> bool:
        """지문 검증"""
        extracted = self.extract(content)
        if not extracted:
            return False
        return extracted == expected_fingerprint_id[:12]

    def hash_content(self, content: str) -> str:
        """콘텐츠 해시 (중복 감지용)"""
        # 제로폭 문자 제거 후 해시
        clean = re.sub(r'[\u200b-\u200d\ufeff]', '', content)
        return hashlib.sha256(clean.encode('utf-8')).hexdigest()

    def _make_fingerprint_id(self, user_id: str, content_id: str, timestamp: float) -> str:
        """지문 ID 생성 (SHA256 기반)"""
        raw = f"{user_id}|{content_id}|{timestamp:.0f}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def strip_fingerprint(self, content: str) -> str:
        """콘텐츠에서 지문 제거 (원본 복원)"""
        return re.sub(r'[\u200b-\u200d\ufeff]+', '', content)
