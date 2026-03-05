"""
Notion 내보내기 서비스

Notion API v1으로 새 페이지를 생성합니다.
마크다운을 Notion 블록 형식으로 변환합니다.
"""
import re
import logging

import requests

logger = logging.getLogger(__name__)

NOTION_API_URL = 'https://api.notion.com/v1/pages'
NOTION_VERSION = '2022-06-28'


def export_to_notion(title: str, content: str, api_key: str, parent_page_id: str = '') -> dict:
    """Notion에 새 페이지를 생성합니다.

    Args:
        title: 페이지 제목
        content: 마크다운 본문
        api_key: Notion Integration API 키
        parent_page_id: 부모 페이지 ID (없으면 워크스페이스 루트)

    Returns:
        {"success": bool, "message": str, "url": str | None}
    """
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Notion-Version': NOTION_VERSION,
        'Content-Type': 'application/json',
    }

    # 부모 설정
    if parent_page_id:
        parent = {'page_id': parent_page_id}
    else:
        # parent_page_id 없으면 에러
        return {
            'success': False,
            'message': '부모 페이지 ID가 필요합니다.',
            'url': None,
        }

    blocks = _markdown_to_notion_blocks(content)

    payload = {
        'parent': parent,
        'properties': {
            'title': {
                'title': [{'text': {'content': title}}]
            }
        },
        'children': blocks[:100],  # Notion API 제한: 최대 100 블록
    }

    try:
        resp = requests.post(NOTION_API_URL, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'success': True,
                'message': f'Notion 페이지 생성 완료: {title}',
                'url': data.get('url'),
            }
        else:
            error_msg = resp.json().get('message', resp.text)
            logger.error(f"Notion API 오류: {resp.status_code} - {error_msg}")
            return {
                'success': False,
                'message': f'Notion API 오류: {error_msg}',
                'url': None,
            }
    except requests.RequestException as e:
        logger.error(f"Notion 연결 실패: {e}")
        return {
            'success': False,
            'message': f'Notion 연결 실패: {str(e)}',
            'url': None,
        }


def _markdown_to_notion_blocks(md: str) -> list[dict]:
    """마크다운 텍스트를 Notion 블록 배열로 변환합니다."""
    blocks = []
    lines = md.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # 코드 블록
        if stripped.startswith('```'):
            lang = stripped[3:].strip()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                code_lines.append(lines[i])
                i += 1
            blocks.append({
                'object': 'block',
                'type': 'code',
                'code': {
                    'rich_text': [{'type': 'text', 'text': {'content': '\n'.join(code_lines)}}],
                    'language': lang or 'plain text',
                },
            })
            i += 1
            continue

        # 헤딩
        if stripped.startswith('### '):
            blocks.append(_heading_block(stripped[4:], 3))
        elif stripped.startswith('## '):
            blocks.append(_heading_block(stripped[3:], 2))
        elif stripped.startswith('# '):
            blocks.append(_heading_block(stripped[2:], 1))

        # 인용문
        elif stripped.startswith('> '):
            blocks.append({
                'object': 'block',
                'type': 'quote',
                'quote': {'rich_text': _rich_text(stripped[2:])},
            })

        # 비순서 목록
        elif stripped.startswith(('- ', '* ', '+ ')):
            blocks.append({
                'object': 'block',
                'type': 'bulleted_list_item',
                'bulleted_list_item': {'rich_text': _rich_text(stripped[2:])},
            })

        # 순서 목록
        elif re.match(r'^\d+\.\s', stripped):
            text = re.sub(r'^\d+\.\s', '', stripped)
            blocks.append({
                'object': 'block',
                'type': 'numbered_list_item',
                'numbered_list_item': {'rich_text': _rich_text(text)},
            })

        # 일반 텍스트
        else:
            blocks.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {'rich_text': _rich_text(stripped)},
            })

        i += 1

    return blocks


def _heading_block(text: str, level: int) -> dict:
    """Notion 헤딩 블록 생성"""
    heading_type = f'heading_{level}'
    return {
        'object': 'block',
        'type': heading_type,
        heading_type: {'rich_text': _rich_text(text)},
    }


def _rich_text(text: str) -> list[dict]:
    """마크다운 인라인 서식을 Notion rich_text 배열로 변환합니다."""
    segments = []
    pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)')
    last_end = 0

    for m in pattern.finditer(text):
        if m.start() > last_end:
            segments.append({'type': 'text', 'text': {'content': text[last_end:m.start()]}})

        if m.group(2):  # 볼드
            segments.append({
                'type': 'text',
                'text': {'content': m.group(2)},
                'annotations': {'bold': True},
            })
        elif m.group(3):  # 이탤릭
            segments.append({
                'type': 'text',
                'text': {'content': m.group(3)},
                'annotations': {'italic': True},
            })
        elif m.group(4):  # 코드
            segments.append({
                'type': 'text',
                'text': {'content': m.group(4)},
                'annotations': {'code': True},
            })

        last_end = m.end()

    if last_end < len(text):
        segments.append({'type': 'text', 'text': {'content': text[last_end:]}})

    return segments or [{'type': 'text', 'text': {'content': text}}]
