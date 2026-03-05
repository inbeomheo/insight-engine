"""커스텀 필드 서비스 (F8-11)

워크스페이스별로 콘텐츠에 추가할 커스텀 필드 스키마를 정의하고,
콘텐츠 항목에 커스텀 필드 값을 저장·조회합니다.
"""
import uuid
import time
import logging
from threading import Lock
from typing import Any, Optional

logger = logging.getLogger(__name__)

FIELD_TYPES = {'text', 'number', 'boolean', 'date', 'select', 'multi_select', 'url', 'email'}

_schemas: dict[str, dict] = {}   # schema_id → FieldSchema
_values: dict[str, dict] = {}    # item_id → {field_id: value}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


# ─── 스키마 관리 ─────────────────────────────────────────────────

def create_field_schema(
    workspace_id: str,
    name: str,
    field_type: str = 'text',
    required: bool = False,
    options: list[str] | None = None,
    default_value: Any = None,
    description: str = '',
) -> dict:
    """커스텀 필드 스키마를 생성합니다."""
    if field_type not in FIELD_TYPES:
        field_type = 'text'

    schema_id = str(uuid.uuid4())
    schema = {
        'id': schema_id,
        'workspace_id': workspace_id,
        'name': name,
        'field_type': field_type,
        'required': required,
        'options': options or [],
        'default_value': default_value,
        'description': description,
        'created_at': _now(),
    }
    with _lock:
        _schemas[schema_id] = schema
    return schema


def list_schemas(workspace_id: str) -> list[dict]:
    """워크스페이스의 커스텀 필드 스키마 목록을 반환합니다."""
    with _lock:
        return [s for s in _schemas.values() if s['workspace_id'] == workspace_id]


def delete_schema(schema_id: str) -> bool:
    """스키마를 삭제합니다."""
    with _lock:
        if schema_id in _schemas:
            del _schemas[schema_id]
            return True
        return False


# ─── 값 관리 ──────────────────────────────────────────────────────

def set_field_value(item_id: str, field_id: str, value: Any) -> dict:
    """콘텐츠 항목의 커스텀 필드 값을 설정합니다."""
    with _lock:
        if item_id not in _values:
            _values[item_id] = {}
        _values[item_id][field_id] = value
    return {item_id: _values[item_id]}


def get_field_values(item_id: str) -> dict:
    """콘텐츠 항목의 모든 커스텀 필드 값을 반환합니다."""
    with _lock:
        return dict(_values.get(item_id, {}))


def delete_field_values(item_id: str) -> None:
    """콘텐츠 항목의 모든 커스텀 필드 값을 삭제합니다."""
    with _lock:
        _values.pop(item_id, None)


def get_schema(schema_id: str) -> Optional[dict]:
    """스키마를 조회합니다."""
    with _lock:
        return _schemas.get(schema_id)
