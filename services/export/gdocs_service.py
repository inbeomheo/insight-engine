"""
Google Docs 텍스트 추출 서비스

공개 문서: export URL로 텍스트 다운로드
비공개: Google Docs API 사용 (API 키 필요)
"""
import logging
import re
from typing import Dict

import requests

logger = logging.getLogger(__name__)

_REQUEST_TIMEOUT = 15  # 초

# Google Docs URL에서 document ID 추출
_GDOC_ID_RE = re.compile(
    r'docs\.google\.com/document/d/([a-zA-Z0-9_-]+)',
    re.IGNORECASE,
)


def _extract_doc_id(url: str) -> str:
    """Google Docs URL에서 문서 ID를 추출합니다."""
    m = _GDOC_ID_RE.search(url)
    if not m:
        raise ValueError('유효한 Google Docs URL이 아닙니다.')
    return m.group(1)


def extract_google_doc(url: str, api_key: str = None) -> Dict:
    """Google Docs에서 텍스트를 추출합니다.

    공개 문서는 export URL로 직접 다운로드하고,
    실패 시 api_key가 있으면 Google Docs API를 사용합니다.

    Args:
        url: Google Docs URL
        api_key: Google API 키 (선택, 비공개 문서용)

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "gdocs"}

    Raises:
        ValueError: URL 파싱 실패 또는 문서 접근 불가
    """
    doc_id = _extract_doc_id(url)

    # 1차: 공개 export URL (텍스트 형식)
    export_url = f'https://docs.google.com/document/d/{doc_id}/export?format=txt'
    try:
        resp = requests.get(
            export_url,
            timeout=_REQUEST_TIMEOUT,
            allow_redirects=False,
        )
        if resp.status_code == 200 and len(resp.text.strip()) > 50:
            content = resp.text.strip()
            # 제목: 첫 줄
            lines = content.split('\n')
            title = lines[0].strip() if lines else 'Google 문서'
            return {
                'title': title,
                'content': content,
                'url': url,
                'source_type': 'gdocs',
            }
    except requests.RequestException:
        logger.debug('Google Docs export 실패, API 폴백 시도')

    # 2차: Google Docs API (api_key 필요)
    if api_key:
        return _extract_via_api(doc_id, api_key, url)

    raise ValueError(
        'Google Docs에 접근할 수 없습니다. '
        '문서가 공개 상태인지 확인하거나 Google API 키를 설정하세요.'
    )


def _extract_via_api(doc_id: str, api_key: str, original_url: str) -> Dict:
    """Google Docs API로 문서 텍스트를 추출합니다."""
    api_url = f'https://docs.googleapis.com/v1/documents/{doc_id}'
    resp = requests.get(
        api_url,
        params={'key': api_key},
        timeout=_REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if 300 <= resp.status_code < 400:
        raise ValueError(f'Google Docs API 리다이렉트 차단: {resp.status_code}')
    if resp.status_code != 200:
        raise ValueError(f'Google Docs API 오류: {resp.status_code}')

    doc = resp.json()
    title = doc.get('title', 'Google 문서')

    # body.content에서 텍스트 추출
    parts = []
    for element in doc.get('body', {}).get('content', []):
        paragraph = element.get('paragraph')
        if not paragraph:
            continue
        for el in paragraph.get('elements', []):
            text_run = el.get('textRun')
            if text_run:
                parts.append(text_run.get('content', ''))

    content = ''.join(parts).strip()
    if not content:
        raise ValueError('Google Docs에서 텍스트를 추출할 수 없습니다.')

    return {
        'title': title,
        'content': content,
        'url': original_url,
        'source_type': 'gdocs',
    }
