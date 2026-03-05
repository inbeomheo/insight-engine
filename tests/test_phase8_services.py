"""Phase 8 서비스 통합 테스트 (F8-02 ~ F8-25)"""
import pytest
import time as _time
from services import content_library_service as lib_svc
from services import archive_service
from services import lock_service
from services import expiry_service
from services import media_library_service
from services import custom_field_service
from services import link_manager_service
from services import seo_checklist_service
from services import share_service
from services import comment_service
from services import workflow_service
from services import rbac_service
from services import trash_service


@pytest.fixture(autouse=True)
def clear_state():
    lib_svc.clear_all()
    # 각 서비스 내부 상태 리셋
    lock_service._locks.clear()
    expiry_service._expiry_rules.clear()
    media_library_service._media.clear()
    custom_field_service._schemas.clear()
    custom_field_service._values.clear()
    link_manager_service._links.clear()
    share_service._shares.clear()
    comment_service._comments.clear()
    workflow_service._workflows.clear()
    workflow_service._execution_log.clear()
    rbac_service._custom_roles.clear()
    rbac_service._user_roles.clear()
    yield
    lib_svc.clear_all()


# ─── F8-07 아카이브 ──────────────────────────────────────────

def test_archive_and_restore():
    item = lib_svc.create_item(title='아카이브 테스트', content='')
    archived = archive_service.archive_item(item['id'], user_id='u1')
    assert archived['is_archived'] is True
    assert archived['status'] == 'archived'

    restored = archive_service.restore_item(item['id'], user_id='u1')
    assert restored['is_archived'] is False
    assert restored['status'] == 'draft'


def test_archive_list():
    item = lib_svc.create_item(title='목록 아카이브', content='')
    archive_service.archive_item(item['id'])
    result = archive_service.list_archived()
    assert result['total'] >= 1


# ─── F8-08 잠금 ─────────────────────────────────────────────

def test_lock_acquire_release():
    result = lock_service.acquire_lock('item-1', 'user-a', 'Alice')
    assert result['success'] is True

    result2 = lock_service.acquire_lock('item-1', 'user-b', 'Bob')
    assert result2['success'] is False
    assert 'locked_by' in result2

    released = lock_service.release_lock('item-1', 'user-a')
    assert released is True
    assert lock_service.get_lock('item-1') is None


def test_lock_same_user_renew():
    lock_service.acquire_lock('item-2', 'user-a')
    result = lock_service.acquire_lock('item-2', 'user-a')
    assert result['success'] is True


def test_lock_heartbeat():
    lock_service.acquire_lock('item-3', 'user-a')
    ok = lock_service.heartbeat('item-3', 'user-a')
    assert ok is True


# ─── F8-09 만료 관리 ─────────────────────────────────────────

def test_expiry_set_and_get():
    item = lib_svc.create_item(title='만료 테스트', content='')
    ts = _time.time() + 3600
    rule = expiry_service.set_expiry(item['id'], expires_at=ts, action='archive')
    assert rule['item_id'] == item['id']
    assert rule['action'] == 'archive'

    fetched = expiry_service.get_expiry(item['id'])
    assert fetched is not None
    assert fetched['expires_at'] == ts


def test_expiry_process_expired():
    item = lib_svc.create_item(title='만료 처리', content='')
    # 과거 시간으로 설정
    expiry_service.set_expiry(item['id'], expires_at=_time.time() - 10, action='archive')
    result = expiry_service.process_expired()
    assert result['archived'] >= 1


# ─── F8-10 미디어 라이브러리 ──────────────────────────────────

def test_media_register_and_list():
    m = media_library_service.register_media(
        name='test.png', url='https://example.com/img.png', media_type='image',
        size_bytes=1024, workspace_id='ws1',
    )
    assert m['media_type'] == 'image'

    result = media_library_service.list_media(workspace_id='ws1')
    assert result['total'] == 1


def test_media_delete():
    m = media_library_service.register_media(name='del.jpg', url='http://x.com', workspace_id='ws2')
    success = media_library_service.delete_media(m['id'])
    assert success is True
    assert media_library_service.get_media(m['id']) is None


# ─── F8-11 커스텀 필드 ───────────────────────────────────────

def test_custom_field_schema_and_value():
    schema = custom_field_service.create_field_schema(
        workspace_id='ws1', name='priority', field_type='select',
        options=['low', 'mid', 'high'],
    )
    assert schema['field_type'] == 'select'

    custom_field_service.set_field_value('item-1', schema['id'], 'high')
    vals = custom_field_service.get_field_values('item-1')
    assert vals[schema['id']] == 'high'


# ─── F8-12 링크 관리 ──────────────────────────────────────────

def test_link_add_and_backlink():
    link_manager_service.add_link('src-1', 'dst-1', link_type='internal', label='관련 글')
    links = link_manager_service.get_links_from('src-1')
    assert len(links) == 1

    backlinks = link_manager_service.get_backlinks('dst-1')
    assert len(backlinks) == 1
    assert backlinks[0]['source_id'] == 'src-1'


def test_link_broken():
    link = link_manager_service.add_link('src-2', 'http://broken.example', link_type='external')
    updated = link_manager_service.mark_broken(link['id'], True)
    assert updated['is_broken'] is True

    broken = link_manager_service.get_broken_links('src-2')
    assert len(broken) == 1


# ─── F8-13 SEO 체크리스트 ─────────────────────────────────────

def test_seo_checklist_pass():
    title = '파이썬으로 배우는 머신러닝 입문'
    content = ('파이썬' * 5 + '\n## 소개\n\n' + '# 파이썬 기초\n' +
                '[링크1](https://a.com) [링크2](https://b.com)\n' + 'x' * 1000)
    result = seo_checklist_service.run_checklist(title, content)
    assert 'score' in result
    assert result['grade'] in ('A', 'B', 'C', 'D')
    assert len(result['checks']) >= 5


def test_seo_checklist_fail_short_content():
    result = seo_checklist_service.run_checklist('짧은 제목', 'short')
    content_check = next(c for c in result['checks'] if c['id'] == 'content_length')
    assert content_check['status'] == 'fail'


# ─── F8-15 공유 링크 ──────────────────────────────────────────

def test_share_link_create_and_access():
    link = share_service.create_share_link('item-1', user_id='u1', expires_in_hours=24)
    token = link['token']

    result = share_service.verify_and_access(token)
    assert result['success'] is True
    assert result['item_id'] == 'item-1'


def test_share_link_password():
    link = share_service.create_share_link('item-2', password='secret123')
    token = link['token']

    result = share_service.verify_and_access(token, password='wrong')
    assert result['success'] is False

    result2 = share_service.verify_and_access(token, password='secret123')
    assert result2['success'] is True


def test_share_link_revoke():
    link = share_service.create_share_link('item-3', user_id='u1')
    share_service.revoke_share(link['token'], 'u1')
    result = share_service.verify_and_access(link['token'])
    assert result['success'] is False


# ─── F8-16 댓글 ───────────────────────────────────────────────

def test_comment_add_and_list():
    c = comment_service.add_comment('item-1', 'u1', 'Alice', '좋은 글이에요!')
    assert c['text'] == '좋은 글이에요!'

    comments = comment_service.list_comments('item-1')
    assert len(comments) == 1


def test_comment_mention():
    c = comment_service.add_comment('item-2', 'u1', 'Alice', '안녕 @bob, @charlie 확인해봐')
    assert 'bob' in c['mentions']
    assert 'charlie' in c['mentions']


def test_comment_resolve():
    c = comment_service.add_comment('item-3', 'u1', 'Alice', '수정 필요')
    comment_service.resolve_comment(c['id'], 'u2')
    unresolved = comment_service.list_comments('item-3', include_resolved=False)
    assert len(unresolved) == 0


def test_comment_delete():
    c = comment_service.add_comment('item-4', 'u1', 'Alice', '삭제됩니다')
    comment_service.delete_comment(c['id'], 'u1')
    comments = comment_service.list_comments('item-4')
    assert len(comments) == 0


# ─── F8-17 워크플로우 ─────────────────────────────────────────

def test_workflow_create_and_fire():
    called_with = {}

    def handler(item_id, action, context):
        called_with['item_id'] = item_id
        return 'ok'

    workflow_service.register_handler('notify', handler)

    wf = workflow_service.create_workflow(
        name='초안→검토 알림',
        workspace_id='ws1',
        trigger='status_change',
        trigger_conditions={'from_status': 'draft', 'to_status': 'review'},
        actions=[{'type': 'notify', 'target': 'assignee'}],
    )

    results = workflow_service.fire_trigger(
        trigger='status_change',
        item_id='item-1',
        workspace_id='ws1',
        context={'from_status': 'draft', 'to_status': 'review'},
    )
    assert len(results) == 1
    assert called_with.get('item_id') == 'item-1'


def test_workflow_conditions_not_match():
    workflow_service.create_workflow(
        name='다른 조건',
        workspace_id='ws2',
        trigger='status_change',
        trigger_conditions={'from_status': 'review', 'to_status': 'approved'},
        actions=[],
    )
    results = workflow_service.fire_trigger(
        trigger='status_change',
        item_id='item-2',
        workspace_id='ws2',
        context={'from_status': 'draft', 'to_status': 'review'},  # 조건 불일치
    )
    assert len(results) == 0


# ─── F8-19 RBAC ───────────────────────────────────────────────

def test_rbac_builtin_roles():
    perms = rbac_service.get_role_permissions('ws1', 'owner')
    assert 'content:write' in perms
    assert 'rbac:manage' in perms


def test_rbac_assign_and_check():
    rbac_service.assign_role('ws1', 'u1', 'editor')
    assert rbac_service.has_permission('ws1', 'u1', 'content:write') is True
    assert rbac_service.has_permission('ws1', 'u1', 'rbac:manage') is False


def test_rbac_custom_role():
    role = rbac_service.create_custom_role(
        'ws1', 'reviewer', permissions=['content:read', 'comment:write'], label='검토자'
    )
    rbac_service.assign_role('ws1', 'u2', role['name'])
    assert rbac_service.has_permission('ws1', 'u2', 'content:read') is True
    assert rbac_service.has_permission('ws1', 'u2', 'content:write') is False


# ─── F8-24 휴지통 ─────────────────────────────────────────────

def test_trash_move_and_restore():
    item = lib_svc.create_item(title='휴지통 테스트', content='')
    trash_service.move_to_trash(item['id'], 'u1')
    assert lib_svc.get_item(item['id']) is None  # 조회 불가

    restored = trash_service.restore_from_trash(item['id'])
    assert restored is not None
    assert lib_svc.get_item(item['id']) is not None


def test_trash_list():
    item = lib_svc.create_item(title='목록 테스트', content='')
    trash_service.move_to_trash(item['id'])
    result = trash_service.list_trash()
    assert result['total'] >= 1


def test_trash_permanent_delete():
    item = lib_svc.create_item(title='영구삭제', content='')
    trash_service.move_to_trash(item['id'])
    trash_service.permanently_delete(item['id'])
    result = trash_service.list_trash()
    ids = [i['id'] for i in result['items']]
    assert item['id'] not in ids


def test_empty_trash():
    for i in range(3):
        it = lib_svc.create_item(title=f'비우기 {i}', content='')
        trash_service.move_to_trash(it['id'])
    count = trash_service.empty_trash()
    assert count == 3
    assert trash_service.list_trash()['total'] == 0
