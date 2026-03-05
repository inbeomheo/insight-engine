"""폴더/카테고리 서비스 (F5-11)

콘텐츠를 폴더로 정리하는 CRUD 기능을 제공합니다.
인메모리 저장소 기반.
"""
import uuid
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 인메모리 저장소
_folders: dict[str, dict] = {}  # {folder_id: folder}
_content_folders: dict[str, str] = {}  # {content_id: folder_id}


def create_folder(name: str, parent_id: Optional[str] = None,
                  user_id: str = '') -> dict:
    """폴더를 생성합니다."""
    folder_id = str(uuid.uuid4())
    folder = {
        'id': folder_id,
        'name': name,
        'parent_id': parent_id,
        'user_id': user_id,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'content_count': 0,
    }
    _folders[folder_id] = folder
    logger.info("폴더 생성: %s (%s)", name, folder_id)
    return folder


def list_folders(user_id: str = '', parent_id: Optional[str] = None) -> list[dict]:
    """폴더 목록을 반환합니다."""
    result = []
    for folder in _folders.values():
        if user_id and folder.get('user_id') != user_id:
            continue
        if folder.get('parent_id') != parent_id:
            continue
        # 콘텐츠 수 갱신
        count = sum(1 for fid in _content_folders.values() if fid == folder['id'])
        folder['content_count'] = count
        result.append(folder)
    return sorted(result, key=lambda f: f['name'])


def get_folder(folder_id: str) -> Optional[dict]:
    """폴더를 조회합니다."""
    return _folders.get(folder_id)


def update_folder(folder_id: str, name: Optional[str] = None,
                  parent_id: Optional[str] = '__no_change__') -> Optional[dict]:
    """폴더를 수정합니다."""
    folder = _folders.get(folder_id)
    if not folder:
        return None
    if name is not None:
        folder['name'] = name
    if parent_id != '__no_change__':
        folder['parent_id'] = parent_id
    return folder


def delete_folder(folder_id: str) -> bool:
    """폴더를 삭제합니다. 하위 콘텐츠는 미분류로 이동."""
    if folder_id not in _folders:
        return False
    del _folders[folder_id]
    # 해당 폴더의 콘텐츠를 미분류로 이동
    for cid, fid in list(_content_folders.items()):
        if fid == folder_id:
            del _content_folders[cid]
    logger.info("폴더 삭제: %s", folder_id)
    return True


def move_content(content_id: str, folder_id: Optional[str]) -> bool:
    """콘텐츠를 폴더로 이동합니다. folder_id=None이면 미분류."""
    if folder_id and folder_id not in _folders:
        return False
    if folder_id:
        _content_folders[content_id] = folder_id
    else:
        _content_folders.pop(content_id, None)
    return True


def get_content_folder(content_id: str) -> Optional[str]:
    """콘텐츠가 속한 폴더 ID를 반환합니다."""
    return _content_folders.get(content_id)


def list_folder_contents(folder_id: str) -> list[str]:
    """폴더에 속한 콘텐츠 ID 목록을 반환합니다."""
    return [cid for cid, fid in _content_folders.items() if fid == folder_id]
