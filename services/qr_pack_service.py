"""
QR 코드 팩 생성 서비스

여러 URL에 대한 QR 코드 데이터를 일괄 생성합니다.
외부 라이브러리 없이 QR 코드 텍스트 표현(데이터)을 생성하며,
실제 이미지 렌더링은 프론트엔드에서 처리합니다.
"""
import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class QRCode:
    """개별 QR 코드"""
    url: str
    qr_data: str      # QR 인코딩용 데이터 문자열
    label: str         # 표시 라벨
    style: str         # 스타일 ('standard', 'branded', 'minimal')


@dataclass
class QRPack:
    """QR 코드 팩"""
    codes: List[QRCode] = field(default_factory=list)
    total: int = 0
    format: str = 'png'  # 출력 포맷 힌트


# 지원 스타일
_SUPPORTED_STYLES = {'standard', 'branded', 'minimal', 'rounded', 'dotted'}

# URL 정규화 패턴
_URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$',
    re.IGNORECASE,
)


def _is_valid_url(url: str) -> bool:
    """URL 유효성을 검사합니다."""
    if not url or not isinstance(url, str):
        return False
    return bool(_URL_PATTERN.match(url.strip()))


def _normalize_url(url: str) -> str:
    """URL을 정규화합니다."""
    url = url.strip()
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    return url


def _generate_label(url: str) -> str:
    """URL에서 사람이 읽을 수 있는 라벨을 생성합니다."""
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ''
        # www. 제거
        if domain.startswith('www.'):
            domain = domain[4:]
        path = parsed.path.strip('/')
        if path:
            # 경로의 마지막 부분을 라벨로
            last_segment = path.split('/')[-1]
            # 파일 확장자 제거
            last_segment = re.sub(r'\.\w+$', '', last_segment)
            # 하이픈/언더스코어 → 공백
            last_segment = re.sub(r'[-_]', ' ', last_segment)
            if last_segment:
                return f"{domain}/{last_segment}"
        return domain
    except Exception:
        return url[:50]


def _generate_qr_data(url: str, style: str) -> str:
    """QR 코드 인코딩 데이터를 생성합니다.

    실제 QR 이미지 생성은 프론트엔드에서 처리하므로
    여기서는 URL + 메타데이터를 JSON 형식으로 반환합니다.
    """
    # 고유 ID 생성 (URL 해시)
    url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]

    # QR 데이터: 프론트엔드 QR 라이브러리가 사용할 형식
    qr_data = (
        f'{{"url":"{url}",'
        f'"id":"{url_hash}",'
        f'"style":"{style}",'
        f'"version":"1"}}'
    )
    return qr_data


def generate_qr_pack(urls: list, style: str = 'standard') -> QRPack:
    """여러 URL의 QR 코드 팩을 생성합니다.

    Args:
        urls: URL 문자열 리스트
        style: QR 스타일 ('standard', 'branded', 'minimal', 'rounded', 'dotted')

    Returns:
        QRPack (QR 코드 리스트, 총 수, 포맷)
    """
    if not urls:
        return QRPack(codes=[], total=0, format='png')

    # 스타일 검증
    if style not in _SUPPORTED_STYLES:
        logger.warning(f"미지원 스타일 '{style}', 'standard'로 대체합니다")
        style = 'standard'

    codes = []
    seen_urls = set()  # 중복 제거

    for url in urls:
        if not isinstance(url, str):
            continue

        normalized = _normalize_url(url)

        # 중복 스킵
        if normalized in seen_urls:
            continue
        seen_urls.add(normalized)

        # URL 유효성 검사
        if not _is_valid_url(normalized):
            logger.warning(f"유효하지 않은 URL 건너뜀: {url}")
            continue

        label = _generate_label(normalized)
        qr_data = _generate_qr_data(normalized, style)

        codes.append(QRCode(
            url=normalized,
            qr_data=qr_data,
            label=label,
            style=style,
        ))

    return QRPack(
        codes=codes,
        total=len(codes),
        format='png',
    )
