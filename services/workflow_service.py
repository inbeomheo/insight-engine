"""콘텐츠 워크플로우 자동화 서비스 (F8-17)

트리거-액션 기반 워크플로우 정의 및 실행 엔진.
트리거: status_change, created, scheduled
액션: notify, assign, move_folder, auto_publish, add_tag
"""
import uuid
import time
import logging
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger(__name__)

TRIGGERS = {'status_change', 'created', 'tag_added', 'scheduled', 'lock_released'}
ACTIONS = {'notify', 'assign', 'move_folder', 'auto_publish', 'add_tag', 'remove_tag', 'webhook'}

_workflows: dict[str, dict] = {}
_execution_log: list[dict] = []
_action_handlers: dict[str, Callable] = {}
_lock = Lock()


def _now() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


# ─── 워크플로우 정의 ─────────────────────────────────────────────

def create_workflow(
    name: str,
    workspace_id: str,
    trigger: str,
    trigger_conditions: dict,
    actions: list[dict],
    is_enabled: bool = True,
    user_id: str = '',
) -> dict:
    """워크플로우를 생성합니다.

    Args:
        trigger: TRIGGERS 중 하나
        trigger_conditions: 트리거 조건 (예: {'from_status': 'draft', 'to_status': 'review'})
        actions: 수행할 액션 목록 (예: [{'type': 'notify', 'target': 'assignee'}])
    """
    if trigger not in TRIGGERS:
        raise ValueError(f'지원하지 않는 트리거: {trigger}')

    wf_id = str(uuid.uuid4())
    workflow = {
        'id': wf_id,
        'name': name,
        'workspace_id': workspace_id,
        'trigger': trigger,
        'trigger_conditions': trigger_conditions,
        'actions': actions,
        'is_enabled': is_enabled,
        'user_id': user_id,
        'run_count': 0,
        'last_run': None,
        'created_at': _now(),
    }
    with _lock:
        _workflows[wf_id] = workflow
    logger.info('워크플로우 생성: %s (%s)', wf_id[:8], name)
    return workflow


def update_workflow(wf_id: str, **kwargs) -> dict | None:
    """워크플로우를 업데이트합니다."""
    allowed = {'name', 'trigger_conditions', 'actions', 'is_enabled'}
    with _lock:
        wf = _workflows.get(wf_id)
        if not wf:
            return None
        for k, v in kwargs.items():
            if k in allowed:
                wf[k] = v
    return wf


def delete_workflow(wf_id: str) -> bool:
    """워크플로우를 삭제합니다."""
    with _lock:
        if wf_id in _workflows:
            del _workflows[wf_id]
            return True
        return False


def list_workflows(workspace_id: str = '') -> list[dict]:
    """워크플로우 목록을 반환합니다."""
    with _lock:
        wfs = list(_workflows.values())
    if workspace_id:
        wfs = [w for w in wfs if w['workspace_id'] == workspace_id]
    return wfs


# ─── 액션 핸들러 등록 ─────────────────────────────────────────────

def register_handler(action_type: str, handler: Callable) -> None:
    """액션 핸들러를 등록합니다."""
    _action_handlers[action_type] = handler


# ─── 트리거 실행 ─────────────────────────────────────────────────

def fire_trigger(
    trigger: str,
    item_id: str,
    workspace_id: str,
    context: dict | None = None,
) -> list[dict]:
    """트리거를 발동하여 매칭되는 워크플로우를 실행합니다.

    Returns:
        실행된 워크플로우별 결과 목록
    """
    context = context or {}
    results = []

    with _lock:
        candidates = [
            w for w in _workflows.values()
            if w['trigger'] == trigger
            and w['workspace_id'] == workspace_id
            and w['is_enabled']
        ]

    for wf in candidates:
        if not _matches_conditions(wf['trigger_conditions'], context):
            continue

        run_result = _execute_workflow(wf, item_id, context)
        results.append(run_result)

        with _lock:
            _workflows[wf['id']]['run_count'] += 1
            _workflows[wf['id']]['last_run'] = _now()

        with _lock:
            _execution_log.append({
                'wf_id': wf['id'],
                'item_id': item_id,
                'trigger': trigger,
                'result': run_result,
                'at': _now(),
            })

    return results


def _matches_conditions(conditions: dict, context: dict) -> bool:
    """트리거 조건이 컨텍스트와 일치하는지 확인합니다."""
    for key, expected in conditions.items():
        if context.get(key) != expected:
            return False
    return True


def _execute_workflow(wf: dict, item_id: str, context: dict) -> dict:
    """워크플로우의 모든 액션을 순서대로 실행합니다."""
    action_results = []
    for action in wf.get('actions', []):
        action_type = action.get('type')
        handler = _action_handlers.get(action_type)
        if handler:
            try:
                result = handler(item_id=item_id, action=action, context=context)
                action_results.append({'type': action_type, 'status': 'ok', 'result': result})
            except Exception as e:
                logger.error('워크플로우 액션 실패: %s — %s', action_type, e)
                action_results.append({'type': action_type, 'status': 'error', 'error': str(e)})
        else:
            action_results.append({'type': action_type, 'status': 'no_handler'})

    return {'wf_id': wf['id'], 'wf_name': wf['name'], 'actions': action_results}


def get_execution_log(wf_id: str = '', limit: int = 50) -> list[dict]:
    """워크플로우 실행 로그를 반환합니다."""
    with _lock:
        log = list(reversed(_execution_log))
    if wf_id:
        log = [e for e in log if e['wf_id'] == wf_id]
    return log[:limit]
