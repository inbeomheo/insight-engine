"""RBAC (역할 기반 접근 제어) 강화 서비스 (F8-19)

워크스페이스별 역할(Role)과 권한(Permission)을 세밀하게 관리합니다.
기존 workspace_service.py의 단순 Owner/Editor/Viewer 역할을 확장합니다.
"""
import uuid
import time
import logging
from threading import Lock
from typing import Optional

logger = logging.getLogger(__name__)

# 내장 역할과 기본 권한
BUILTIN_ROLES = {
    'owner': {
        'label': '소유자',
        'permissions': [
            'content:read', 'content:write', 'content:delete', 'content:publish',
            'member:invite', 'member:remove', 'workspace:settings',
            'workflow:manage', 'rbac:manage',
        ],
    },
    'editor': {
        'label': '편집자',
        'permissions': [
            'content:read', 'content:write', 'content:publish',
            'member:invite',
        ],
    },
    'viewer': {
        'label': '뷰어',
        'permissions': ['content:read'],
    },
    'commenter': {
        'label': '댓글 작성자',
        'permissions': ['content:read', 'comment:write'],
    },
}

# 사용자 정의 역할
_custom_roles: dict[str, dict] = {}  # role_id → RoleDef
# 사용자-역할 매핑: (workspace_id, user_id) → role_id
_user_roles: dict[str, str] = {}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def _role_key(workspace_id: str, user_id: str) -> str:
    return f'{workspace_id}:{user_id}'


# ─── 역할 정의 ─────────────────────────────────────────────────

def create_custom_role(
    workspace_id: str,
    name: str,
    permissions: list[str],
    label: str = '',
    description: str = '',
) -> dict:
    """사용자 정의 역할을 생성합니다."""
    role_id = str(uuid.uuid4())
    role = {
        'id': role_id,
        'workspace_id': workspace_id,
        'name': name,
        'label': label or name,
        'description': description,
        'permissions': list(set(permissions)),
        'is_builtin': False,
        'created_at': _now(),
    }
    with _lock:
        _custom_roles[role_id] = role
    return role


def get_role_permissions(workspace_id: str, role_name_or_id: str) -> list[str]:
    """역할의 권한 목록을 반환합니다."""
    # 내장 역할 먼저 확인
    if role_name_or_id in BUILTIN_ROLES:
        return list(BUILTIN_ROLES[role_name_or_id]['permissions'])

    with _lock:
        # ID 또는 이름으로 사용자 정의 역할 검색
        for role in _custom_roles.values():
            if role['workspace_id'] == workspace_id:
                if role['id'] == role_name_or_id or role['name'] == role_name_or_id:
                    return list(role['permissions'])
    return []


def list_roles(workspace_id: str) -> list[dict]:
    """워크스페이스에서 사용 가능한 모든 역할 목록 (내장 + 사용자 정의)."""
    builtin = [
        {'id': k, 'name': k, 'label': v['label'], 'permissions': v['permissions'], 'is_builtin': True}
        for k, v in BUILTIN_ROLES.items()
    ]
    with _lock:
        custom = [r for r in _custom_roles.values() if r['workspace_id'] == workspace_id]
    return builtin + custom


# ─── 사용자-역할 할당 ─────────────────────────────────────────────

def assign_role(workspace_id: str, user_id: str, role: str) -> dict:
    """사용자에게 역할을 할당합니다."""
    key = _role_key(workspace_id, user_id)
    with _lock:
        _user_roles[key] = role
    logger.info('역할 할당: %s → %s (ws: %s)', user_id, role, workspace_id)
    return {'workspace_id': workspace_id, 'user_id': user_id, 'role': role, 'updated_at': _now()}


def get_user_role(workspace_id: str, user_id: str) -> Optional[str]:
    """사용자의 역할을 반환합니다."""
    with _lock:
        return _user_roles.get(_role_key(workspace_id, user_id))


def remove_user_role(workspace_id: str, user_id: str) -> bool:
    """사용자의 역할 할당을 제거합니다."""
    key = _role_key(workspace_id, user_id)
    with _lock:
        if key in _user_roles:
            del _user_roles[key]
            return True
        return False


# ─── 권한 검증 ─────────────────────────────────────────────────

def has_permission(workspace_id: str, user_id: str, permission: str) -> bool:
    """사용자가 특정 권한을 가지고 있는지 확인합니다."""
    role = get_user_role(workspace_id, user_id)
    if not role:
        return False
    permissions = get_role_permissions(workspace_id, role)
    return permission in permissions


def check_permission(workspace_id: str, user_id: str, permission: str) -> None:
    """권한이 없으면 PermissionError를 발생시킵니다."""
    if not has_permission(workspace_id, user_id, permission):
        raise PermissionError(f'권한 없음: {permission} (user: {user_id})')


def get_all_user_permissions(workspace_id: str, user_id: str) -> list[str]:
    """사용자의 모든 권한 목록을 반환합니다."""
    role = get_user_role(workspace_id, user_id)
    if not role:
        return []
    return get_role_permissions(workspace_id, role)
