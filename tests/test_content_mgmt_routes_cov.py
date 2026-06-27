"""content_mgmt_routes.py 커버리지 보강 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_H = {'Origin': 'http://localhost:3000'}
_SB_PATCH = 'services.data.supabase_service.is_supabase_enabled'


class _Base(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()


class TestContentCRUD(_Base):
    """F8-01 콘텐츠 라이브러리 CRUD."""

    @patch(_SB_PATCH, return_value=False)
    def test_create_content_success(self, _):
        resp = self.client.post('/api/content', json={'title': '테스트'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    def test_create_content_no_title(self, _):
        resp = self.client.post('/api/content', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    def test_list_contents(self, _):
        resp = self.client.get('/api/content', headers=_H)
        self.assertIn(resp.status_code, [200, 400, 500])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value={'id': 'x', 'title': 't', 'content': ''})
    @patch('services.data.content_library_service.increment_view')
    def test_get_content_found(self, _m1, _m2, _):
        resp = self.client.get('/api/content/x', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value=None)
    def test_get_content_not_found(self, _m1, _):
        resp = self.client.get('/api/content/missing', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.update_item', return_value={'id': 'x', 'title': 'updated'})
    def test_update_content_success(self, _m1, _):
        resp = self.client.patch('/api/content/x', json={'title': 'updated'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.update_item', return_value=None)
    def test_update_content_not_found(self, _m1, _):
        resp = self.client.patch('/api/content/missing', json={'title': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.trash_service.move_to_trash', return_value=True)
    def test_delete_content_success(self, _m1, _):
        resp = self.client.delete('/api/content/x', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.trash_service.move_to_trash', return_value=False)
    def test_delete_content_not_found(self, _m1, _):
        resp = self.client.delete('/api/content/missing', headers=_H)
        self.assertEqual(resp.status_code, 404)


class TestBulkAction(_Base):
    """F8-05 일괄 작업."""

    @patch(_SB_PATCH, return_value=False)
    def test_bulk_no_ids(self, _):
        resp = self.client.post('/api/content/bulk', json={'action': 'delete', 'item_ids': []}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.trash_service.move_to_trash', return_value=True)
    def test_bulk_delete(self, _m1, _):
        resp = self.client.post('/api/content/bulk', json={'action': 'delete', 'item_ids': ['a', 'b']}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['success_count'], 2)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.archive_item', return_value={'id': 'a'})
    def test_bulk_archive(self, _m1, _):
        resp = self.client.post('/api/content/bulk', json={'action': 'archive', 'item_ids': ['a']}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.restore_item', return_value={'id': 'a'})
    def test_bulk_restore(self, _m1, _):
        resp = self.client.post('/api/content/bulk', json={'action': 'restore', 'item_ids': ['a']}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value={'id': 'a', 'tags': ['old']})
    @patch('services.data.content_library_service.update_item', return_value={'id': 'a'})
    def test_bulk_tag(self, _m1, _m2, _):
        resp = self.client.post('/api/content/bulk',
                                json={'action': 'tag', 'item_ids': ['a'], 'tags': ['new']}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.update_item', return_value={'id': 'a'})
    def test_bulk_status_change(self, _m1, _):
        resp = self.client.post('/api/content/bulk',
                                json={'action': 'status_change', 'item_ids': ['a'], 'status': 'published'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    def test_bulk_unknown_action(self, _):
        resp = self.client.post('/api/content/bulk',
                                json={'action': 'unknown', 'item_ids': ['a']}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['failed_count'], 1)


class TestClone(_Base):
    """F8-06 콘텐츠 복제."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value={
        'id': 'a', 'title': '원본', 'content': 'body', 'style': 'blog', 'tags': ['t1'],
        'url': '', 'user_id': 'u1', 'workspace_id': 'w1', 'folder_id': '', 'meta': {}
    })
    @patch('services.data.content_library_service.create_item', return_value={'id': 'b', 'title': '[복사] 원본'})
    def test_clone_success(self, _m1, _m2, _):
        resp = self.client.post('/api/content/a/clone', json={}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value=None)
    def test_clone_not_found(self, _m1, _):
        resp = self.client.post('/api/content/missing/clone', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)


class TestArchive(_Base):
    """F8-07 아카이브."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.archive_item', return_value={'id': 'a'})
    def test_archive_content(self, _m1, _):
        resp = self.client.post('/api/content/a/archive', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.archive_item', return_value=None)
    def test_archive_not_found(self, _m1, _):
        resp = self.client.post('/api/content/missing/archive', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.restore_item', return_value={'id': 'a'})
    def test_unarchive(self, _m1, _):
        resp = self.client.post('/api/content/a/unarchive', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.restore_item', return_value=None)
    def test_unarchive_not_found(self, _m1, _):
        resp = self.client.post('/api/content/x/unarchive', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.archive_service.list_archived', return_value={'items': [], 'total': 0})
    def test_list_archived(self, _m1, _):
        resp = self.client.get('/api/content/archive', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestLock(_Base):
    """F8-08 콘텐츠 잠금."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.lock_service.acquire_lock', return_value={'success': True})
    def test_acquire_lock(self, _m1, _):
        resp = self.client.post('/api/content/a/lock', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.lock_service.acquire_lock', return_value={'success': False, 'locked_by': 'other'})
    def test_acquire_lock_conflict(self, _m1, _):
        resp = self.client.post('/api/content/a/lock', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 423)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.lock_service.release_lock', return_value=True)
    def test_release_lock(self, _m1, _):
        resp = self.client.delete('/api/content/a/lock', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.lock_service.heartbeat', return_value=True)
    def test_lock_heartbeat(self, _m1, _):
        resp = self.client.post('/api/content/a/lock/heartbeat', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.lock_service.get_lock', return_value=None)
    def test_get_lock_status(self, _m1, _):
        resp = self.client.get('/api/content/a/lock', headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertFalse(data['is_locked'])


class TestExpiry(_Base):
    """F8-09 만료 관리."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.expiry_service.set_expiry', return_value={'item_id': 'a', 'expires_at': 999999})
    def test_set_expiry(self, _m1, _):
        resp = self.client.post('/api/content/a/expiry', json={'expires_at': 999999}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    def test_set_expiry_no_timestamp(self, _):
        resp = self.client.post('/api/content/a/expiry', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.expiry_service.remove_expiry', return_value=True)
    def test_remove_expiry(self, _m1, _):
        resp = self.client.delete('/api/content/a/expiry', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.expiry_service.get_expiry', return_value=None)
    def test_get_expiry(self, _m1, _):
        resp = self.client.get('/api/content/a/expiry', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestMedia(_Base):
    """F8-10 미디어 라이브러리."""

    @patch(_SB_PATCH, return_value=False)
    def test_register_media_missing_fields(self, _):
        resp = self.client.post('/api/content/media', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.media_library_service.register_media', return_value={'id': 'm1'})
    def test_register_media_success(self, _m1, _):
        resp = self.client.post('/api/content/media',
                                json={'name': 'img.png', 'url': 'https://example.com/img.png'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.media_library_service.list_media', return_value={'items': [], 'total': 0})
    def test_list_media(self, _m1, _):
        resp = self.client.get('/api/content/media', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.media_library_service.delete_media', return_value=True)
    def test_delete_media_success(self, _m1, _):
        resp = self.client.delete('/api/content/media/m1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.media_library_service.delete_media', return_value=False)
    def test_delete_media_not_found(self, _m1, _):
        resp = self.client.delete('/api/content/media/missing', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.media.media_library_service.get_storage_stats', return_value={'total_bytes': 0})
    def test_media_stats(self, _m1, _):
        resp = self.client.get('/api/content/media/stats', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestCustomField(_Base):
    """F8-11 커스텀 필드."""

    @patch(_SB_PATCH, return_value=False)
    def test_create_field_missing(self, _):
        resp = self.client.post('/api/content/fields', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.custom_field_service.create_field_schema', return_value={'id': 'f1'})
    def test_create_field_success(self, _m1, _):
        resp = self.client.post('/api/content/fields',
                                json={'workspace_id': 'w1', 'name': 'priority'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    def test_list_fields_no_workspace(self, _):
        resp = self.client.get('/api/content/fields', headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.custom_field_service.list_schemas', return_value=[])
    def test_list_fields(self, _m1, _):
        resp = self.client.get('/api/content/fields?workspace_id=w1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.custom_field_service.get_field_values', return_value={})
    def test_get_item_fields(self, _m1, _):
        resp = self.client.get('/api/content/a/fields', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.custom_field_service.set_field_value', return_value={'ok': True})
    def test_set_item_field(self, _m1, _):
        resp = self.client.put('/api/content/a/fields/f1', json={'value': 'high'}, headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestLinks(_Base):
    """F8-12 링크 관리."""

    @patch(_SB_PATCH, return_value=False)
    def test_add_link_no_target(self, _):
        resp = self.client.post('/api/content/a/links', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.seo.link_manager_service.add_link', return_value={'id': 'l1'})
    def test_add_link_success(self, _m1, _):
        resp = self.client.post('/api/content/a/links', json={'target': 'b'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.seo.link_manager_service.get_links_from', return_value=[])
    @patch('services.seo.link_manager_service.get_backlinks', return_value=[])
    def test_get_links(self, _m1, _m2, _):
        resp = self.client.get('/api/content/a/links', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.seo.link_manager_service.remove_link', return_value=True)
    def test_remove_link(self, _m1, _):
        resp = self.client.delete('/api/content/links/l1', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestSeoCheck(_Base):
    """F8-13 SEO 체크리스트."""

    @patch(_SB_PATCH, return_value=False)
    def test_seo_check_no_input(self, _):
        resp = self.client.post('/api/content/seo-check', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.seo.seo_checklist_service.run_checklist', return_value={'score': 80})
    def test_seo_check_success(self, _m1, _):
        resp = self.client.post('/api/content/seo-check', json={'title': 'T', 'content': 'C'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value=None)
    def test_seo_check_item_not_found(self, _m1, _):
        resp = self.client.get('/api/content/missing/seo-check', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value={
        'title': 'T', 'content': 'C', 'meta': {}
    })
    @patch('services.seo.seo_checklist_service.run_checklist', return_value={'score': 90})
    def test_seo_check_item(self, _m1, _m2, _):
        resp = self.client.get('/api/content/a/seo-check', headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestEmbed(_Base):
    """F8-14 콘텐츠 임베드."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value=None)
    def test_embed_not_found(self, _m1, _):
        resp = self.client.get('/api/content/embed/missing', headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.content_library_service.get_item', return_value={
        'title': '임베드 테스트', 'content': '본문 텍스트'
    })
    def test_embed_success(self, _m1, _):
        resp = self.client.get('/api/content/embed/a', headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/html', resp.content_type)


class TestShare(_Base):
    """F8-15 공유 링크."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.share_service.create_share_link', return_value={
        'token': 'tok123', 'expires_at': '2030-01-01'
    })
    def test_create_share(self, _m1, _):
        resp = self.client.post('/api/content/a/share', json={}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.share_service.verify_and_access', return_value={
        'success': True, 'item_id': 'a', 'allow_download': False
    })
    @patch('services.data.content_library_service.get_item', return_value={'id': 'a', 'title': 'T'})
    def test_access_share_success(self, _m1, _m2, _):
        resp = self.client.get('/api/content/share/tok123', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.share_service.verify_and_access', return_value={
        'success': False, 'reason': '만료됨'
    })
    def test_access_share_expired(self, _m1, _):
        resp = self.client.get('/api/content/share/bad', headers=_H)
        self.assertEqual(resp.status_code, 403)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.platform.share_service.revoke_share', return_value=True)
    def test_revoke_share(self, _m1, _):
        resp = self.client.delete('/api/content/share/tok123', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestComments(_Base):
    """F8-16 댓글."""

    @patch(_SB_PATCH, return_value=False)
    def test_add_comment_missing_fields(self, _):
        resp = self.client.post('/api/content/a/comments', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.add_comment', return_value={'id': 'c1'})
    def test_add_comment_success(self, _m1, _):
        resp = self.client.post('/api/content/a/comments',
                                json={'user_id': 'u1', 'text': '코멘트'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.list_comments', return_value=[])
    def test_list_comments(self, _m1, _):
        resp = self.client.get('/api/content/a/comments', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.update_comment', return_value={'id': 'c1'})
    def test_update_comment(self, _m1, _):
        resp = self.client.patch('/api/content/comments/c1', json={'text': 'edited'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.update_comment', return_value=None)
    def test_update_comment_not_found(self, _m1, _):
        resp = self.client.patch('/api/content/comments/bad', json={'text': 'x'}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.delete_comment', return_value=True)
    def test_delete_comment(self, _m1, _):
        resp = self.client.delete('/api/content/comments/c1', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.resolve_comment', return_value={'id': 'c1'})
    def test_resolve_comment(self, _m1, _):
        resp = self.client.post('/api/content/comments/c1/resolve', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.resolve_comment', return_value=None)
    def test_resolve_comment_not_found(self, _m1, _):
        resp = self.client.post('/api/content/comments/bad/resolve', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.add_reaction', return_value={'id': 'c1'})
    def test_react_comment(self, _m1, _):
        resp = self.client.post('/api/content/comments/c1/react', json={'user_id': 'u1'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.content.comment_service.add_reaction', return_value=None)
    def test_react_comment_not_found(self, _m1, _):
        resp = self.client.post('/api/content/comments/bad/react', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)


class TestWorkflow(_Base):
    """F8-17 워크플로우."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.create_workflow', return_value={'id': 'wf1'})
    def test_create_workflow(self, _m1, _):
        resp = self.client.post('/api/content/workflows', json={'name': 'auto'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.create_workflow', side_effect=ValueError('잘못된 트리거'))
    def test_create_workflow_validation_error(self, _m1, _):
        resp = self.client.post('/api/content/workflows', json={'name': 'bad'}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.list_workflows', return_value=[])
    def test_list_workflows(self, _m1, _):
        resp = self.client.get('/api/content/workflows', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.update_workflow', return_value={'id': 'wf1'})
    def test_update_workflow(self, _m1, _):
        resp = self.client.patch('/api/content/workflows/wf1', json={'name': 'updated'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.update_workflow', return_value=None)
    def test_update_workflow_not_found(self, _m1, _):
        resp = self.client.patch('/api/content/workflows/bad', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.delete_workflow', return_value=True)
    def test_delete_workflow(self, _m1, _):
        resp = self.client.delete('/api/content/workflows/wf1', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.workflow_service.fire_trigger', return_value=[])
    def test_fire_trigger(self, _m1, _):
        resp = self.client.post('/api/content/workflows/fire', json={'trigger': 'on_create'}, headers=_H)
        self.assertEqual(resp.status_code, 200)


class TestRBAC(_Base):
    """F8-19 RBAC."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.rbac_service.create_custom_role', return_value={'name': 'reviewer'})
    def test_create_role(self, _m1, _):
        resp = self.client.post('/api/content/roles', json={'name': 'reviewer'}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.rbac_service.list_roles', return_value=[])
    def test_list_roles(self, _m1, _):
        resp = self.client.get('/api/content/roles', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.rbac_service.assign_role', return_value={'ok': True})
    def test_assign_role(self, _m1, _):
        resp = self.client.post('/api/content/roles/assign',
                                json={'workspace_id': 'w1', 'user_id': 'u1', 'role': 'editor'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.rbac_service.has_permission', return_value=True)
    def test_check_permission(self, _m1, _):
        resp = self.client.post('/api/content/roles/check',
                                json={'workspace_id': 'w1', 'user_id': 'u1', 'permission': 'edit'}, headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['has_permission'])


class TestBackup(_Base):
    """F8-22 자동 백업."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.create_backup', return_value={'filename': 'backup.zip'})
    def test_create_backup(self, _m1, _):
        resp = self.client.post('/api/content/backup', json={}, headers=_H)
        self.assertIn(resp.status_code, [200, 201])

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.create_backup', side_effect=Exception('disk full'))
    def test_create_backup_error(self, _m1, _):
        resp = self.client.post('/api/content/backup', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.list_backups', return_value=[])
    def test_list_backups(self, _m1, _):
        resp = self.client.get('/api/content/backup', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.list_backups', side_effect=Exception('err'))
    def test_list_backups_error(self, _m1, _):
        resp = self.client.get('/api/content/backup', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.restore_backup', return_value={'restored': True})
    def test_restore_backup(self, _m1, _):
        resp = self.client.post('/api/content/backup/backup.zip/restore', json={}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.restore_backup', side_effect=FileNotFoundError('not found'))
    def test_restore_backup_not_found(self, _m1, _):
        resp = self.client.post('/api/content/backup/missing.zip/restore', json={}, headers=_H)
        self.assertEqual(resp.status_code, 404)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.restore_backup', side_effect=ValueError('bad name'))
    def test_restore_backup_invalid_filename(self, _m1, _):
        resp = self.client.post('/api/content/backup/bad.zip/restore', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.backup_service.restore_backup', side_effect=Exception('corrupted'))
    def test_restore_backup_error(self, _m1, _):
        resp = self.client.post('/api/content/backup/bad.zip/restore', json={}, headers=_H)
        self.assertEqual(resp.status_code, 500)


class TestDataExportImport(_Base):
    """F8-23 데이터 가져오기/내보내기."""

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.export_json', return_value='[]')
    def test_export_json(self, _m1, _):
        resp = self.client.get('/api/content/export/json', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.export_csv', return_value='a,b\n1,2')
    def test_export_csv(self, _m1, _):
        resp = self.client.get('/api/content/export/csv', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.export_markdown', return_value='# test')
    def test_export_markdown(self, _m1, _):
        resp = self.client.get('/api/content/export/markdown', headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    def test_export_unsupported(self, _):
        resp = self.client.get('/api/content/export/xml', headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.export_json', side_effect=Exception('err'))
    def test_export_error(self, _m1, _):
        resp = self.client.get('/api/content/export/json', headers=_H)
        self.assertEqual(resp.status_code, 500)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.import_json', return_value={'imported': 5})
    def test_import_json(self, _m1, _):
        resp = self.client.post('/api/content/import/json', json={'content': '[]'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.import_csv', return_value={'imported': 3})
    def test_import_csv(self, _m1, _):
        resp = self.client.post('/api/content/import/csv', json={'content': 'a,b'}, headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch(_SB_PATCH, return_value=False)
    def test_import_unsupported(self, _):
        resp = self.client.post('/api/content/import/xml', json={'content': ''}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch(_SB_PATCH, return_value=False)
    @patch('services.data.data_migration_service.import_json', side_effect=Exception('parse err'))
    def test_import_error(self, _m1, _):
        resp = self.client.post('/api/content/import/json', json={'content': 'bad'}, headers=_H)
        self.assertEqual(resp.status_code, 500)


if __name__ == '__main__':
    unittest.main()
