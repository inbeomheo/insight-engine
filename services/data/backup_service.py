"""자동 백업 서비스 (F8-22)

콘텐츠 라이브러리 전체 또는 개별 항목을 JSON으로 스냅샷 저장합니다.
APScheduler를 통해 일정 주기로 자동 실행합니다.
"""
import json
import os
import re
import uuid
import time
import logging
from pathlib import Path
from threading import Lock
from typing import Optional
from services.data import content_library_service

logger = logging.getLogger(__name__)

_BACKUP_FILENAME_RE = re.compile(r'^backup_[A-Za-z0-9_.-]+\.json$')


def _default_backup_dir() -> Path:
    explicit_dir = (os.getenv('CONTENT_BACKUP_DIR') or '').strip()
    if explicit_dir:
        return Path(explicit_dir)

    app_data_backup_dir = (os.getenv('APP_DATA_BACKUP_DIR') or '').strip()
    if app_data_backup_dir:
        return Path(app_data_backup_dir) / 'content-library'

    app_data_dir = (os.getenv('APP_DATA_DIR') or '').strip()
    if app_data_dir:
        return Path(app_data_dir) / 'backups'

    return Path('data/backups')


def _max_backups() -> int:
    raw = (
        (os.getenv('CONTENT_BACKUP_MAX_BACKUPS') or '').strip()
        or (os.getenv('MAX_BACKUPS') or '').strip()
        or '30'
    )
    return int(raw)


BACKUP_DIR = _default_backup_dir()
MAX_BACKUPS = _max_backups()  # 최대 보관 백업 수

_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _ts() -> str:
    return time.strftime('%Y%m%d_%H%M%S', time.gmtime())


def _backup_file_path(filename: str) -> Path:
    if not _BACKUP_FILENAME_RE.fullmatch(filename or ''):
        raise ValueError('invalid backup filename')

    root = BACKUP_DIR.resolve()
    path = (root / filename).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError('invalid backup filename') from exc
    return path


def create_backup(
    workspace_id: str = '',
    user_id: str = '',
    triggered_by: str = 'manual',
) -> dict:
    """콘텐츠 라이브러리 백업을 생성합니다.

    Returns:
        {'backup_id': ..., 'path': ..., 'item_count': ..., 'size_bytes': ...}
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    items = content_library_service.get_all_items_raw()
    if workspace_id:
        items = [i for i in items if i.get('workspace_id') == workspace_id]

    backup_id = str(uuid.uuid4())
    payload = {
        'backup_id': backup_id,
        'created_at': _now(),
        'workspace_id': workspace_id,
        'user_id': user_id,
        'triggered_by': triggered_by,
        'item_count': len(items),
        'items': items,
    }

    filename = f'backup_{_ts()}_{backup_id[:8]}.json'
    path = BACKUP_DIR / filename

    with _lock:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    size_bytes = path.stat().st_size
    logger.info('백업 완료: %s (%d items, %d bytes)', filename, len(items), size_bytes)

    # 오래된 백업 자동 삭제
    _prune_old_backups()

    return {
        'backup_id': backup_id,
        'filename': filename,
        'path': str(path),
        'item_count': len(items),
        'size_bytes': size_bytes,
        'created_at': _now(),
    }


def list_backups() -> list[dict]:
    """저장된 백업 목록을 반환합니다."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backups = []
    for p in sorted(BACKUP_DIR.glob('backup_*.json'), reverse=True):
        stat = p.stat()
        backups.append({
            'filename': p.name,
            'path': str(p),
            'size_bytes': stat.st_size,
            'modified_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(stat.st_mtime)),
        })
    return backups


def restore_backup(filename: str) -> dict:
    """백업 파일에서 항목을 복원합니다 (덮어쓰기).

    Returns:
        {'restored': N, 'skipped': N}
    """
    path = _backup_file_path(filename)
    if not path.exists():
        raise FileNotFoundError(f'백업 파일 없음: {filename}')

    payload = json.loads(path.read_text(encoding='utf-8'))
    items = payload.get('items', [])

    restored = skipped = 0
    for item in items:
        item_id = item.get('id')
        if not item_id:
            skipped += 1
            continue
        # 이미 존재하면 업데이트, 없으면 신규 생성
        existing = content_library_service.get_item(item_id)
        if existing:
            content_library_service.update_item(item_id, **{
                k: v for k, v in item.items()
                if k not in ('id', 'created_at', 'updated_at')
            })
        else:
            content_library_service.create_item(
                title=item.get('title', ''),
                content=item.get('content', ''),
                style=item.get('style', ''),
                tags=item.get('tags', []),
                url=item.get('url', ''),
                user_id=item.get('user_id', ''),
                workspace_id=item.get('workspace_id', ''),
                folder_id=item.get('folder_id', ''),
                meta=item.get('meta', {}),
            )
        restored += 1

    logger.info('백업 복원: %s → %d 항목 복원', filename, restored)
    return {'restored': restored, 'skipped': skipped}


def _prune_old_backups() -> None:
    """오래된 백업 파일을 삭제합니다."""
    files = sorted(BACKUP_DIR.glob('backup_*.json'), reverse=True)
    for old in files[MAX_BACKUPS:]:
        try:
            old.unlink()
            logger.info('오래된 백업 삭제: %s', old.name)
        except OSError as e:
            logger.warning('백업 삭제 실패: %s — %s', old.name, e)


def get_backup_info(filename: str) -> Optional[dict]:
    """백업 파일의 메타데이터를 반환합니다."""
    path = _backup_file_path(filename)
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding='utf-8'))
    return {
        'backup_id': payload.get('backup_id'),
        'created_at': payload.get('created_at'),
        'workspace_id': payload.get('workspace_id'),
        'item_count': payload.get('item_count'),
        'triggered_by': payload.get('triggered_by'),
    }
