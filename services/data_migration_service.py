"""데이터 가져오기/내보내기 서비스 (F8-23)

JSON, CSV, Markdown 형식으로 콘텐츠를 가져오고 내보냅니다.
"""
import csv
import json
import io
import logging
from typing import Any
from services import content_library_service

logger = logging.getLogger(__name__)


# ─── 내보내기 ────────────────────────────────────────────────────

def export_json(
    workspace_id: str = '',
    user_id: str = '',
    include_content: bool = True,
) -> str:
    """콘텐츠를 JSON 문자열로 내보냅니다."""
    result = content_library_service.search_items(
        workspace_id=workspace_id,
        user_id=user_id,
        per_page=10000,
    )
    items = result['items']
    if not include_content:
        items = [{k: v for k, v in i.items() if k != 'content'} for i in items]
    return json.dumps(
        {'version': '1.0', 'count': len(items), 'items': items},
        ensure_ascii=False,
        indent=2,
    )


def export_csv(workspace_id: str = '', user_id: str = '') -> str:
    """콘텐츠 목록을 CSV 문자열로 내보냅니다 (본문 제외)."""
    result = content_library_service.search_items(
        workspace_id=workspace_id,
        user_id=user_id,
        per_page=10000,
    )
    items = result['items']

    buf = io.StringIO()
    fields = ['id', 'title', 'style', 'status', 'is_pinned', 'tags', 'url', 'created_at', 'updated_at']
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()
    for item in items:
        row = {**item, 'tags': ','.join(item.get('tags', []))}
        writer.writerow(row)
    return buf.getvalue()


def export_markdown(workspace_id: str = '', user_id: str = '') -> str:
    """콘텐츠를 마크다운 파일로 내보냅니다 (단일 파일, 섹션 분리)."""
    result = content_library_service.search_items(
        workspace_id=workspace_id,
        user_id=user_id,
        per_page=10000,
    )
    parts = []
    for item in result['items']:
        header = f"# {item.get('title', '제목 없음')}\n"
        meta = (
            f"- **스타일**: {item.get('style', '-')}\n"
            f"- **상태**: {item.get('status', '-')}\n"
            f"- **생성일**: {item.get('created_at', '-')}\n"
            f"- **태그**: {', '.join(item.get('tags', []))}\n"
        )
        content = item.get('content', '')
        parts.append(f"{header}\n{meta}\n{content}\n\n---\n")
    return '\n'.join(parts)


# ─── 가져오기 ────────────────────────────────────────────────────

def import_json(
    json_str: str,
    workspace_id: str = '',
    user_id: str = '',
    overwrite: bool = False,
) -> dict:
    """JSON 문자열에서 콘텐츠를 가져옵니다.

    Returns:
        {'imported': N, 'skipped': N, 'errors': []}
    """
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        return {'imported': 0, 'skipped': 0, 'errors': [f'JSON 파싱 오류: {e}']}

    items = data.get('items', [])
    if isinstance(data, list):
        items = data  # 배열 형식도 허용

    imported = skipped = 0
    errors = []

    for item in items:
        title = item.get('title', '').strip()
        if not title:
            skipped += 1
            continue
        try:
            existing_id = item.get('id', '')
            if existing_id and not overwrite:
                existing = content_library_service.get_item(existing_id)
                if existing:
                    skipped += 1
                    continue

            content_library_service.create_item(
                title=title,
                content=item.get('content', ''),
                style=item.get('style', ''),
                tags=item.get('tags', []),
                url=item.get('url', ''),
                user_id=user_id,
                workspace_id=workspace_id,
                folder_id=item.get('folder_id', ''),
                meta=item.get('meta', {}),
            )
            imported += 1
        except Exception as e:
            errors.append(f'{title}: {e}')

    logger.info('JSON 가져오기 완료: %d 성공, %d 건너뜀, %d 오류', imported, skipped, len(errors))
    return {'imported': imported, 'skipped': skipped, 'errors': errors}


def import_csv(
    csv_str: str,
    workspace_id: str = '',
    user_id: str = '',
) -> dict:
    """CSV 문자열에서 콘텐츠 메타데이터를 가져옵니다."""
    buf = io.StringIO(csv_str)
    reader = csv.DictReader(buf)
    imported = skipped = 0
    errors = []

    for row in reader:
        title = (row.get('title') or '').strip()
        if not title:
            skipped += 1
            continue
        try:
            tags_raw = row.get('tags', '')
            tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
            content_library_service.create_item(
                title=title,
                content=row.get('content', ''),
                style=row.get('style', ''),
                tags=tags,
                url=row.get('url', ''),
                user_id=user_id,
                workspace_id=workspace_id,
            )
            imported += 1
        except Exception as e:
            errors.append(f'{title}: {e}')

    return {'imported': imported, 'skipped': skipped, 'errors': errors}
