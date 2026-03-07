"""rbac_service 단위 테스트"""
import unittest

from services import rbac_service


class TestRbacService(unittest.TestCase):
    """RBAC 역할 기반 접근제어 테스트"""

    def setUp(self):
        with rbac_service._lock:
            rbac_service._custom_roles.clear()
            rbac_service._user_roles.clear()

    def test_builtin_role_permissions(self):
        """내장 역할 권한 조회"""
        perms = rbac_service.get_role_permissions('ws1', 'owner')
        self.assertIn('content:write', perms)
        self.assertIn('rbac:manage', perms)

    def test_viewer_limited(self):
        """뷰어는 read만"""
        perms = rbac_service.get_role_permissions('ws1', 'viewer')
        self.assertEqual(perms, ['content:read'])

    def test_create_custom_role(self):
        """사용자 정의 역할 생성"""
        role = rbac_service.create_custom_role('ws1', 'reviewer', ['content:read', 'comment:write'])
        self.assertIn('id', role)
        self.assertFalse(role['is_builtin'])
        self.assertIn('content:read', role['permissions'])

    def test_list_roles(self):
        """역할 목록 (내장 + 커스텀)"""
        rbac_service.create_custom_role('ws1', 'custom1', ['content:read'])
        roles = rbac_service.list_roles('ws1')
        names = [r['name'] for r in roles]
        self.assertIn('owner', names)
        self.assertIn('custom1', names)

    def test_assign_and_get_role(self):
        """역할 할당 및 조회"""
        rbac_service.assign_role('ws1', 'u1', 'editor')
        self.assertEqual(rbac_service.get_user_role('ws1', 'u1'), 'editor')

    def test_get_unassigned_role(self):
        """미할당 사용자 역할 조회"""
        self.assertIsNone(rbac_service.get_user_role('ws1', 'u999'))

    def test_remove_user_role(self):
        """역할 제거"""
        rbac_service.assign_role('ws1', 'u1', 'editor')
        self.assertTrue(rbac_service.remove_user_role('ws1', 'u1'))
        self.assertIsNone(rbac_service.get_user_role('ws1', 'u1'))

    def test_remove_nonexistent(self):
        """없는 역할 제거 시 False"""
        self.assertFalse(rbac_service.remove_user_role('ws1', 'u999'))

    def test_has_permission(self):
        """권한 확인"""
        rbac_service.assign_role('ws1', 'u1', 'editor')
        self.assertTrue(rbac_service.has_permission('ws1', 'u1', 'content:write'))
        self.assertFalse(rbac_service.has_permission('ws1', 'u1', 'rbac:manage'))

    def test_check_permission_raises(self):
        """권한 없으면 PermissionError"""
        rbac_service.assign_role('ws1', 'u1', 'viewer')
        with self.assertRaises(PermissionError):
            rbac_service.check_permission('ws1', 'u1', 'content:write')

    def test_get_all_user_permissions(self):
        """사용자 전체 권한 목록"""
        rbac_service.assign_role('ws1', 'u1', 'owner')
        perms = rbac_service.get_all_user_permissions('ws1', 'u1')
        self.assertIn('rbac:manage', perms)

    def test_custom_role_lookup_by_id(self):
        """커스텀 역할 ID로 권한 조회"""
        role = rbac_service.create_custom_role('ws1', 'tester', ['content:read'])
        rbac_service.assign_role('ws1', 'u1', role['id'])
        self.assertTrue(rbac_service.has_permission('ws1', 'u1', 'content:read'))


if __name__ == '__main__':
    unittest.main()
