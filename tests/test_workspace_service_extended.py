"""workspace_service 확장 테스트 — is_member, find_user_by_email, ContentApprovalService"""
import unittest
from unittest.mock import patch, MagicMock


class TestIsMember(unittest.TestCase):
    """WorkspaceService.is_member 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        self.assertFalse(ws.is_member('ws-1', 'user-1'))

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_is_member_true(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'user_id': 'user-1'}]
        )
        ws = WorkspaceService()
        self.assertTrue(ws.is_member('ws-1', 'user-1'))

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_is_member_false(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]
        )
        ws = WorkspaceService()
        self.assertFalse(ws.is_member('ws-1', 'user-1'))

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase', return_value=None)
    def test_no_client(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        self.assertFalse(ws.is_member('ws-1', 'user-1'))


class TestFindUserByEmail(unittest.TestCase):
    """WorkspaceService.find_user_by_email 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        self.assertIsNone(ws.find_user_by_email('test@test.com'))

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_service_supabase')
    def test_found_with_explicit_service_role(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        user = MagicMock(email='test@test.com', id='user-123')
        mock_client.auth.admin.list_users.return_value = [user]
        ws = WorkspaceService()
        self.assertEqual(ws.find_user_by_email('test@test.com'), 'user-123')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_service_supabase')
    def test_not_found(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.auth.admin.list_users.return_value = []
        ws = WorkspaceService()
        self.assertIsNone(ws.find_user_by_email('nobody@test.com'))

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_service_supabase', return_value=None)
    def test_no_client(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        self.assertIsNone(ws.find_user_by_email('test@test.com'))


class TestWorkspaceServiceInviteSuccess(unittest.TestCase):
    """invite_member 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_invite_new_member(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        # 1. 기존 멤버 아님
        check_chain = MagicMock()
        check_chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        # 2. 초대 삽입 성공
        insert_chain = MagicMock()
        insert_chain.insert.return_value.execute.return_value = MagicMock(
            data=[{'workspace_id': 'ws-1', 'user_id': 'user-2', 'role': 'editor'}]
        )
        mock_client.table.side_effect = [check_chain, insert_chain]

        ws = WorkspaceService()
        result = ws.invite_member('ws-1', 'user-2')
        self.assertNotIn('error', result)
        self.assertEqual(result['role'], 'editor')


class TestWorkspaceServiceRemoveSuccess(unittest.TestCase):
    """remove_member 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_remove_non_owner(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        # editor 역할
        check_chain = MagicMock()
        check_chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'role': 'editor'}]
        )
        # 삭제 실행
        delete_chain = MagicMock()
        delete_chain.delete.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_client.table.side_effect = [check_chain, delete_chain]

        ws = WorkspaceService()
        self.assertTrue(ws.remove_member('ws-1', 'user-2'))


class TestWorkspaceServiceUpdateRoleSuccess(unittest.TestCase):
    """update_role 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_update_to_viewer(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        # editor 역할 (owner 아님)
        check_chain = MagicMock()
        check_chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'role': 'editor'}]
        )
        # 업데이트 실행
        update_chain = MagicMock()
        update_chain.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_client.table.side_effect = [check_chain, update_chain]

        ws = WorkspaceService()
        self.assertTrue(ws.update_role('ws-1', 'user-2', 'viewer'))


class TestWorkspaceServiceDeleteSuccess(unittest.TestCase):
    """delete_workspace 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_owner_deletes(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client

        # owner 확인 성공
        check_chain = MagicMock()
        check_chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'owner_id': 'owner-1'}]
        )
        # 삭제 실행
        delete_chain = MagicMock()
        delete_chain.delete.return_value.eq.return_value.execute.return_value = MagicMock()

        mock_client.table.side_effect = [check_chain, delete_chain]

        ws = WorkspaceService()
        self.assertTrue(ws.delete_workspace('ws-1', 'owner-1'))


class TestContentApprovalServiceDisabled(unittest.TestCase):
    """ContentApprovalService — Supabase 비활성 시"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_add_content_disabled(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        result = cas.add_content('ws-1', 'user-1', 'c-1', 'Title')
        self.assertIn('error', result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_get_workspace_contents_disabled(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        result = cas.get_workspace_contents('ws-1')
        self.assertEqual(result, [])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_transition_disabled(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        result = cas._transition('c-1', 'user-1', 'review', ['owner'])
        self.assertIn('error', result)


class TestContentApprovalServiceTransition(unittest.TestCase):
    """ContentApprovalService._transition 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_content_not_found(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        with patch.object(cas, '_get_content', return_value=None):
            result = cas._transition('c-1', 'user-1', 'review', ['owner'])
            self.assertIn('error', result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_invalid_transition(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        with patch.object(cas, '_get_content', return_value={'status': 'published', 'workspace_id': 'ws-1'}):
            result = cas._transition('c-1', 'user-1', 'review', ['owner'])
            self.assertIn('error', result)
            self.assertIn('전환할 수 없습니다', result['error'])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_no_permission(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        with patch.object(cas, '_get_content', return_value={'status': 'draft', 'workspace_id': 'ws-1'}), \
             patch.object(cas, '_get_member_role', return_value='viewer'):
            result = cas._transition('c-1', 'user-1', 'review', ['owner', 'editor'])
            self.assertIn('error', result)
            self.assertIn('권한', result['error'])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_valid_transition(self, mock_sb, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        transition_query = (
            mock_client.table.return_value.update.return_value
            .eq.return_value.eq.return_value
        )
        transition_query.execute.return_value = MagicMock(
            data=[{'status': 'review'}],
        )
        with patch.object(cas, '_get_content', return_value={'status': 'draft', 'workspace_id': 'ws-1'}), \
             patch.object(cas, '_get_member_role', return_value='editor'):
            result = cas._transition('c-1', 'user-1', 'review', ['owner', 'editor'])
            self.assertEqual(result['status'], 'review')
        first_eq = mock_client.table.return_value.update.return_value.eq
        first_eq.assert_called_once_with('id', 'c-1')
        first_eq.return_value.eq.assert_called_once_with('status', 'draft')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_stale_transition_is_rejected(self, mock_sb, _):
        from services.data.workspace_service import ContentApprovalService

        cas = ContentApprovalService()
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        (
            mock_client.table.return_value.update.return_value
            .eq.return_value.eq.return_value.execute.return_value
        ) = MagicMock(data=[])

        with patch.object(
            cas,
            '_get_content',
            return_value={'status': 'draft', 'workspace_id': 'ws-1'},
        ), patch.object(cas, '_get_member_role', return_value='editor'):
            result = cas._transition(
                'c-1', 'user-1', 'review', ['owner', 'editor'],
            )

        self.assertIn('이미 변경', result['error'])


class TestContentApprovalServiceActions(unittest.TestCase):
    """ContentApprovalService 각 액션 메서드 테스트"""

    def _make_cas(self):
        from services.data.workspace_service import ContentApprovalService
        return ContentApprovalService()

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_submit_for_review(self, _):
        cas = self._make_cas()
        with patch.object(cas, '_transition', return_value={'status': 'review'}) as mock_t:
            result = cas.submit_for_review('c-1', 'user-1')
            mock_t.assert_called_once()
            self.assertEqual(result['status'], 'review')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_approve_content(self, _):
        cas = self._make_cas()
        with patch.object(cas, '_transition', return_value={'status': 'approved'}) as mock_t:
            result = cas.approve_content('c-1', 'reviewer-1')
            self.assertEqual(result['status'], 'approved')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_reject_content(self, _):
        cas = self._make_cas()
        with patch.object(cas, '_transition', return_value={'status': 'rejected'}) as mock_t:
            result = cas.reject_content('c-1', 'reviewer-1', '품질 미달')
            self.assertEqual(result['status'], 'rejected')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_publish_content(self, _):
        cas = self._make_cas()
        with patch.object(cas, '_transition', return_value={'status': 'published'}) as mock_t:
            result = cas.publish_content('c-1', 'owner-1')
            self.assertEqual(result['status'], 'published')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_revert_to_draft(self, _):
        cas = self._make_cas()
        with patch.object(cas, '_transition', return_value={'status': 'draft'}) as mock_t:
            result = cas.revert_to_draft('c-1', 'editor-1')
            self.assertEqual(result['status'], 'draft')


class TestContentApprovalAddContent(unittest.TestCase):
    """ContentApprovalService.add_content 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_success(self, mock_sb, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{'id': 'wc-1', 'status': 'draft'}]
        )
        with patch.object(cas, '_get_member_role', return_value='editor'):
            result = cas.add_content('ws-1', 'user-1', 'c-1', 'Test Title')
            self.assertEqual(result['status'], 'draft')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    def test_no_permission(self, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        with patch.object(cas, '_get_member_role', return_value='viewer'):
            result = cas.add_content('ws-1', 'user-1', 'c-1', 'Title')
            self.assertIn('error', result)


class TestGetWorkspaceContents(unittest.TestCase):
    """ContentApprovalService.get_workspace_contents 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_all_contents(self, mock_sb, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{'id': 'wc-1', 'status': 'draft'}]
        )
        result = cas.get_workspace_contents('ws-1')
        self.assertEqual(len(result), 1)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_filter_by_status(self, mock_sb, _):
        from services.data.workspace_service import ContentApprovalService
        cas = ContentApprovalService()
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        query_chain = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        result = cas.get_workspace_contents('ws-1', status='review')
        self.assertEqual(result, [])


class TestContentStatesConstants(unittest.TestCase):
    """CONTENT_STATES, VALID_TRANSITIONS 상수 테스트"""

    def test_all_states_defined(self):
        from services.data.workspace_service import CONTENT_STATES, VALID_TRANSITIONS
        self.assertEqual(len(CONTENT_STATES), 5)
        for state in CONTENT_STATES:
            self.assertIn(state, VALID_TRANSITIONS)

    def test_published_is_terminal(self):
        from services.data.workspace_service import VALID_TRANSITIONS
        self.assertEqual(VALID_TRANSITIONS['published'], [])


class TestWorkspaceServiceGetWorkspace(unittest.TestCase):
    """WorkspaceService.get_workspace 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_found(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'id': 'ws-1', 'name': '팀A'}]
        )
        ws = WorkspaceService()
        result = ws.get_workspace('ws-1')
        self.assertEqual(result['name'], '팀A')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_not_found(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        ws = WorkspaceService()
        self.assertIsNone(ws.get_workspace('nonexistent'))


class TestWorkspaceServiceGetMembers(unittest.TestCase):
    """WorkspaceService.get_members 성공 케이스"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_members_found(self, mock_sb, _):
        from services.data.workspace_service import WorkspaceService
        mock_client = MagicMock()
        mock_sb.return_value = mock_client
        mock_client.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value = MagicMock(
            data=[{'user_id': 'u1', 'role': 'owner'}, {'user_id': 'u2', 'role': 'editor'}]
        )
        ws = WorkspaceService()
        result = ws.get_members('ws-1')
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
