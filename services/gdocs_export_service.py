"""
Google Docs 내보내기 서비스

Google Docs API로 새 문서를 생성합니다.
마크다운을 Google Docs 요청(insertText, updateParagraphStyle)으로 변환합니다.
"""
import re
import logging

import requests

logger = logging.getLogger(__name__)

DOCS_API_URL = 'https://docs.googleapis.com/v1/documents'


def export_to_gdocs(title: str, content: str, access_token: str) -> dict:
    """Google Docs에 새 문서를 생성합니다.

    Args:
        title: 문서 제목
        content: 마크다운 본문
        access_token: Google OAuth2 액세스 토큰

    Returns:
        {"success": bool, "message": str, "url": str | None}
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
    }

    # 1단계: 빈 문서 생성
    try:
        create_resp = requests.post(
            DOCS_API_URL,
            json={'title': title},
            headers=headers,
            timeout=30,
        )
        if create_resp.status_code != 200:
            error_msg = create_resp.json().get('error', {}).get('message', create_resp.text)
            return {'success': False, 'message': f'문서 생성 실패: {error_msg}', 'url': None}

        doc_data = create_resp.json()
        doc_id = doc_data['documentId']
    except requests.RequestException as e:
        logger.error(f"Google Docs 연결 실패: {e}")
        return {'success': False, 'message': f'Google Docs 연결 실패: {str(e)}', 'url': None}

    # 2단계: 콘텐츠 삽입
    requests_list = _markdown_to_docs_requests(content)
    if requests_list:
        try:
            update_resp = requests.post(
                f'{DOCS_API_URL}/{doc_id}:batchUpdate',
                json={'requests': requests_list},
                headers=headers,
                timeout=30,
            )
            if update_resp.status_code != 200:
                logger.warning(f"콘텐츠 삽입 부분 실패: {update_resp.text}")
        except requests.RequestException as e:
            logger.warning(f"콘텐츠 삽입 중 오류: {e}")

    doc_url = f'https://docs.google.com/document/d/{doc_id}/edit'
    return {
        'success': True,
        'message': f'Google Docs 문서 생성 완료: {title}',
        'url': doc_url,
    }


def _markdown_to_docs_requests(md: str) -> list[dict]:
    """마크다운을 Google Docs batchUpdate 요청으로 변환합니다.

    Google Docs API는 인덱스 기반으로 동작하므로,
    콘텐츠를 역순으로 삽입해야 인덱스가 밀리지 않습니다.
    여기서는 단순화를 위해 순차 삽입 + 인덱스 추적 방식을 사용합니다.
    """
    # 마크다운 인라인 서식 제거 후 순수 텍스트로 삽입
    lines = md.split('\n')
    requests_list = []
    index = 1  # Google Docs는 1부터 시작

    for line in lines:
        stripped = line.strip()

        if stripped.startswith('```'):
            # 코드 블록 시작/끝은 건너뜀 (내용은 일반 텍스트로)
            continue

        # 헤딩 레벨 감지
        heading_level = 0
        text = stripped
        if stripped.startswith('### '):
            heading_level = 3
            text = stripped[4:]
        elif stripped.startswith('## '):
            heading_level = 2
            text = stripped[3:]
        elif stripped.startswith('# '):
            heading_level = 1
            text = stripped[2:]
        elif stripped.startswith('> '):
            text = stripped[2:]
        elif stripped.startswith(('- ', '* ', '+ ')):
            text = '• ' + stripped[2:]
        elif re.match(r'^\d+\.\s', stripped):
            text = stripped  # 번호 목록 유지

        # 인라인 서식 제거
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'`(.+?)`', r'\1', text)

        insert_text = text + '\n'

        # 텍스트 삽입
        requests_list.append({
            'insertText': {
                'location': {'index': index},
                'text': insert_text,
            }
        })

        # 헤딩 스타일 적용
        if heading_level > 0:
            heading_map = {1: 'HEADING_1', 2: 'HEADING_2', 3: 'HEADING_3'}
            requests_list.append({
                'updateParagraphStyle': {
                    'range': {
                        'startIndex': index,
                        'endIndex': index + len(insert_text),
                    },
                    'paragraphStyle': {
                        'namedStyleType': heading_map[heading_level],
                    },
                    'fields': 'namedStyleType',
                }
            })

        index += len(insert_text)

    return requests_list
