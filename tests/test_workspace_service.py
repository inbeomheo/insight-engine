"""
WorkspaceService 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock


class TestWorkspaceServiceDisabled(unittest.TestCase):
    """Supabase 비활성화 시 동작 테스트"""

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_create_returns_error_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.create_workspace('팀A', 'user-1')
        self.assertIn('error', result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_list_returns_empty_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.list_workspaces('user-1')
        self.assertEqual(result, [])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_get_workspace_returns_none_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.get_workspace('ws-1')
        self.assertIsNone(result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_get_members_returns_empty_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.get_members('ws-1')
        self.assertEqual(result, [])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_invite_returns_error_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.invite_member('ws-1', 'user-2')
        self.assertIn('error', result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_remove_returns_false_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.remove_member('ws-1', 'user-2')
        self.assertFalse(result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_update_role_returns_false_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.update_role('ws-1', 'user-2', 'viewer')
        self.assertFalse(result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=False)
    def test_delete_returns_false_when_disabled(self, _):
        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.delete_workspace('ws-1', 'owner-1')
        self.assertFalse(result)


class TestWorkspaceServiceCRUD(unittest.TestCase):
    """Supabase 활성화 시 CRUD 테스트 (mock)"""

    def _mock_supabase(self):
        """공통 Supabase 클라이언트 mock"""
        mock_client = MagicMock()
        return mock_client

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_create_workspace(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # insert 체인 mock
        workspace_data = {'id': 'ws-123', 'name': '팀A', 'owner_id': 'user-1'}
        mock_client.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[workspace_data]
        )

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.create_workspace('팀A', 'user-1')
        self.assertEqual(result['id'], 'ws-123')
        self.assertEqual(result['name'], '팀A')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_list_workspaces(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # 멤버 조회 mock
        members_data = [
            {'workspace_id': 'ws-1', 'role': 'owner'},
            {'workspace_id': 'ws-2', 'role': 'editor'},
        ]
        workspaces_data = [
            {'id': 'ws-1', 'name': '팀A', 'owner_id': 'user-1', 'created_at': '2026-01-01'},
            {'id': 'ws-2', 'name': '팀B', 'owner_id': 'user-2', 'created_at': '2026-01-02'},
        ]

        # 첫 번째 table 호출: 멤버 조회
        member_chain = MagicMock()
        member_chain.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=members_data
        )

        # 두 번째 table 호출: 워크스페이스 조회
        ws_chain = MagicMock()
        ws_chain.select.return_value.in_.return_value.order.return_value.execute.return_value = MagicMock(
            data=workspaces_data
        )

        mock_client.table.side_effect = [member_chain, ws_chain]

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.list_workspaces('user-1')
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['my_role'], 'owner')
        self.assertEqual(result[1]['my_role'], 'editor')

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_invite_duplicate_member(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # 이미 멤버인 경우
        chain = MagicMock()
        chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'user_id': 'user-2'}]
        )
        mock_client.table.return_value = chain

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.invite_member('ws-1', 'user-2')
        self.assertIn('error', result)
        self.assertIn('이미', result['error'])

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_remove_owner_prevented(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # owner 역할 조회 mock
        chain = MagicMock()
        chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'role': 'owner'}]
        )
        mock_client.table.return_value = chain

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.remove_member('ws-1', 'owner-user')
        self.assertFalse(result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_update_role_owner_prevented(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # owner 역할 조회 mock
        chain = MagicMock()
        chain.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'role': 'owner'}]
        )
        mock_client.table.return_value = chain

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.update_role('ws-1', 'owner-user', 'viewer')
        self.assertFalse(result)

    def test_update_role_invalid_role(self):
        """유효하지 않은 역할은 Supabase 호출 없이 False 반환"""
        with patch('services.data.workspace_service.is_supabase_enabled', return_value=True):
            from services.data.workspace_service import WorkspaceService
            ws = WorkspaceService()
            result = ws.update_role('ws-1', 'user-2', 'owner')
            self.assertFalse(result)

    def test_invite_invalid_role(self):
        """owner 역할로 초대 시도 시 에러"""
        with patch('services.data.workspace_service.is_supabase_enabled', return_value=True):
            from services.data.workspace_service import WorkspaceService
            ws = WorkspaceService()
            result = ws.invite_member('ws-1', 'user-2', 'owner')
            self.assertIn('error', result)

    @patch('services.data.workspace_service.is_supabase_enabled', return_value=True)
    @patch('services.data.workspace_service.get_user_supabase')
    def test_delete_non_owner_prevented(self, mock_get_sb, _):
        mock_client = self._mock_supabase()
        mock_get_sb.return_value = mock_client

        # owner가 다른 사용자인 경우
        chain = MagicMock()
        chain.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{'owner_id': 'other-user'}]
        )
        mock_client.table.return_value = chain

        from services.data.workspace_service import WorkspaceService
        ws = WorkspaceService()
        result = ws.delete_workspace('ws-1', 'user-1')
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
