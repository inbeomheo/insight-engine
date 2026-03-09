"""권한 인지 편집 서비스 테스트."""

import unittest
from services.permission_aware_edit_service import (
    EditPermission,
    EditRequest,
    EditResult,
    define_permissions,
    check_permission,
    filter_visible_fields,
    audit_edit,
)


class TestPermissionAwareEditService(unittest.TestCase):
    """PermissionAwareEditService 단위 테스트."""

    def setUp(self):
        """테스트용 권한 목록."""
        self.admin_perm = define_permissions("admin", ["title", "content", "status", "metadata"], True, True)
        self.editor_perm = define_permissions("editor", ["title", "content"], False, True)
        self.viewer_perm = define_permissions("viewer", [], False, False)
        self.permissions = [self.admin_perm, self.editor_perm, self.viewer_perm]

    def test_define_permissions(self):
        """권한 정의가 올바르게 생성된다."""
        perm = define_permissions("editor", ["title", "content"], can_delete=False, can_publish=True)
        self.assertIsInstance(perm, EditPermission)
        self.assertEqual(perm.role, "editor")
        self.assertEqual(perm.allowed_fields, ["title", "content"])
        self.assertFalse(perm.can_delete)
        self.assertTrue(perm.can_publish)

    def test_check_permission_allowed(self):
        """허용된 필드 편집은 승인된다."""
        req = EditRequest(user_role="editor", field="title", old_value="이전", new_value="새 제목")
        result = check_permission(req, self.permissions)
        self.assertTrue(result.approved)
        self.assertEqual(result.field, "title")

    def test_check_permission_denied_field(self):
        """허용되지 않은 필드 편집은 거부된다."""
        req = EditRequest(user_role="editor", field="status", old_value="draft", new_value="published")
        result = check_permission(req, self.permissions)
        self.assertFalse(result.approved)
        self.assertIn("편집할 수 없음", result.reason)

    def test_check_permission_undefined_role(self):
        """정의되지 않은 역할은 거부된다."""
        req = EditRequest(user_role="guest", field="title", old_value="a", new_value="b")
        result = check_permission(req, self.permissions)
        self.assertFalse(result.approved)
        self.assertIn("정의되지 않음", result.reason)

    def test_check_permission_admin_all_fields(self):
        """관리자는 모든 정의된 필드를 편집할 수 있다."""
        for field_name in ["title", "content", "status", "metadata"]:
            req = EditRequest(user_role="admin", field=field_name, old_value="old", new_value="new")
            result = check_permission(req, self.permissions)
            self.assertTrue(result.approved, f"admin should edit {field_name}")

    def test_check_permission_viewer_no_fields(self):
        """뷰어는 어떤 필드도 편집할 수 없다."""
        req = EditRequest(user_role="viewer", field="title", old_value="old", new_value="new")
        result = check_permission(req, self.permissions)
        self.assertFalse(result.approved)

    def test_filter_visible_fields_admin(self):
        """관리자는 모든 필드를 볼 수 있다."""
        all_fields = ["title", "content", "status", "metadata", "internal_notes"]
        visible = filter_visible_fields(all_fields, "admin", self.permissions)
        self.assertIn("title", visible)
        self.assertIn("metadata", visible)
        # internal_notes는 admin 권한에 없으므로 안 보임
        self.assertNotIn("internal_notes", visible)

    def test_filter_visible_fields_editor(self):
        """에디터는 title, content만 볼 수 있다."""
        all_fields = ["title", "content", "status", "metadata"]
        visible = filter_visible_fields(all_fields, "editor", self.permissions)
        self.assertEqual(set(visible), {"title", "content"})

    def test_filter_visible_fields_unknown_role(self):
        """정의되지 않은 역할은 빈 리스트."""
        visible = filter_visible_fields(["title", "content"], "guest", self.permissions)
        self.assertEqual(visible, [])

    def test_filter_visible_fields_viewer(self):
        """뷰어는 빈 필드 목록."""
        visible = filter_visible_fields(["title", "content"], "viewer", self.permissions)
        self.assertEqual(visible, [])

    def test_audit_edit_approved(self):
        """승인된 편집의 감사 로그."""
        req = EditRequest(user_role="admin", field="title", old_value="이전", new_value="새 제목")
        result = EditResult(approved=True, field="title", new_value="새 제목", reason="승인됨")
        log = audit_edit(req, result)

        self.assertIn("timestamp", log)
        self.assertEqual(log["user_role"], "admin")
        self.assertEqual(log["field"], "title")
        self.assertTrue(log["approved"])
        self.assertEqual(log["old_value"], "이전")
        self.assertEqual(log["new_value"], "새 제목")

    def test_audit_edit_denied(self):
        """거부된 편집의 감사 로그."""
        req = EditRequest(user_role="viewer", field="content", old_value="a", new_value="b")
        result = EditResult(approved=False, field="content", new_value="b", reason="권한 없음")
        log = audit_edit(req, result)

        self.assertFalse(log["approved"])
        self.assertEqual(log["reason"], "권한 없음")

    def test_edit_result_contains_new_value(self):
        """편집 결과에 new_value가 포함된다."""
        req = EditRequest(user_role="editor", field="title", old_value="old", new_value="updated")
        result = check_permission(req, self.permissions)
        self.assertEqual(result.new_value, "updated")


if __name__ == "__main__":
    unittest.main()
