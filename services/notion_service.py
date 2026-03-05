"""
Notion 페이지 텍스트 추출 서비스

Notion API v1을 사용하여 페이지 블록을 조회하고 마크다운으로 변환.
"""
import logging
import re
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_NOTION_API_BASE = 'https://api.notion.com/v1'
_NOTION_VERSION = '2022-06-28'
_REQUEST_TIMEOUT = 15  # 초

# Notion 페이지 URL에서 page_id 추출 패턴
# 형식: notion.so/.../PageName-<32hex> 또는 notion.so/.../<uuid>
_PAGE_ID_RE = re.compile(
    r'(?:notion\.so|notion\.site)/(?:.+[-/])?([a-f0-9]{32})(?:\?|$|#)'
    r'|(?:notion\.so|notion\.site)/(?:.+[-/])?([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
    re.IGNORECASE,
)


def _extract_page_id(url: str) -> str:
    """Notion URL에서 page_id를 추출합니다."""
    m = _PAGE_ID_RE.search(url)
    if not m:
        raise ValueError('유효한 Notion 페이지 URL이 아닙니다.')
    # 그룹1: 32hex, 그룹2: uuid 형식
    raw = (m.group(1) or m.group(2)).replace('-', '')
    # UUID 형식으로 변환
    return f'{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}'


def _headers(api_key: str) -> Dict[str, str]:
    return {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': _NOTION_VERSION,
        'Content-Type': 'application/json',
    }


def _get_page_title(page_data: dict) -> str:
    """페이지 메타데이터에서 제목을 추출합니다."""
    props = page_data.get('properties', {})
    # title 속성 찾기
    for prop in props.values():
        if prop.get('type') == 'title':
            title_parts = prop.get('title', [])
            return ''.join(t.get('plain_text', '') for t in title_parts)
    return ''


def _rich_text_to_str(rich_texts: List[dict]) -> str:
    """rich_text 배열을 plain text로 변환합니다."""
    return ''.join(rt.get('plain_text', '') for rt in rich_texts)


def _block_to_markdown(block: dict) -> Optional[str]:
    """Notion 블록 하나를 마크다운 문자열로 변환합니다."""
    btype = block.get('type', '')
    data = block.get(btype, {})

    if btype == 'paragraph':
        text = _rich_text_to_str(data.get('rich_text', []))
        return text if text else ''

    if btype == 'heading_1':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'# {text}' if text else None

    if btype == 'heading_2':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'## {text}' if text else None

    if btype == 'heading_3':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'### {text}' if text else None

    if btype == 'bulleted_list_item':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'- {text}' if text else None

    if btype == 'numbered_list_item':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'1. {text}' if text else None

    if btype == 'code':
        text = _rich_text_to_str(data.get('rich_text', []))
        lang = data.get('language', '')
        return f'```{lang}\n{text}\n```' if text else None

    if btype == 'quote':
        text = _rich_text_to_str(data.get('rich_text', []))
        return f'> {text}' if text else None

    if btype == 'to_do':
        text = _rich_text_to_str(data.get('rich_text', []))
        checked = '☑' if data.get('checked') else '☐'
        return f'{checked} {text}' if text else None

    if btype == 'divider':
        return '---'

    # 지원하지 않는 블록은 무시
    return None


def extract_notion_page(page_url: str, api_key: str) -> Dict:
    """Notion 페이지에서 콘텐츠를 추출합니다.

    Args:
        page_url: Notion 페이지 URL
        api_key: Notion Integration API 키

    Returns:
        {"title": str, "content": str, "url": str, "source_type": "notion"}

    Raises:
        ValueError: URL 파싱 실패 또는 API 오류
    """
    if not api_key:
        raise ValueError('Notion API 키가 설정되지 않았습니다.')

    page_id = _extract_page_id(page_url)
    hdrs = _headers(api_key)

    # 1. 페이지 메타데이터 → 제목
    resp = requests.get(
        f'{_NOTION_API_BASE}/pages/{page_id}',
        headers=hdrs,
        timeout=_REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        raise ValueError(f'Notion 페이지 조회 실패: {resp.status_code} {resp.text[:200]}')

    title = _get_page_title(resp.json())

    # 2. 블록 조회 (페이지네이션)
    blocks: List[dict] = []
    cursor = None
    while True:
        params: Dict = {'page_size': 100}
        if cursor:
            params['start_cursor'] = cursor

        resp = requests.get(
            f'{_NOTION_API_BASE}/blocks/{page_id}/children',
            headers=hdrs,
            params=params,
            timeout=_REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            raise ValueError(f'Notion 블록 조회 실패: {resp.status_code}')

        data = resp.json()
        blocks.extend(data.get('results', []))

        if not data.get('has_more'):
            break
        cursor = data.get('next_cursor')

    # 3. 블록 → 마크다운 변환
    lines = []
    for block in blocks:
        md = _block_to_markdown(block)
        if md is not None:
            lines.append(md)

    content = '\n\n'.join(lines)
    if not content.strip():
        raise ValueError('Notion 페이지에서 텍스트를 추출할 수 없습니다.')

    return {
        'title': title or 'Notion 페이지',
        'content': content,
        'url': page_url,
        'source_type': 'notion',
    }
