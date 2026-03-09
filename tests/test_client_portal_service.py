"""클라이언트 포털 서비스 테스트"""

import unittest
from services.client_portal_service import (
    PortalClient, Portal,
    create_portal, share_content, add_message, get_activity_log,
)


class TestClientPortalService(unittest.TestCase):
    """클라이언트 포털 서비스 테스트"""

    def test_create_portal_basic(self):
        """기본 포털 생성"""
        portal = create_portal("고객사A", "client@example.com")
        self.assertEqual(portal.client.name, "고객사A")
        self.assertEqual(portal.client.email, "client@example.com")
        self.assertEqual(portal.client.access_level, "viewer")
        self.assertEqual(portal.shared_content, [])

    def test_create_portal_with_access_level(self):
        """접근 레벨 지정"""
        portal = create_portal("고객", "c@e.com", "editor")
        self.assertEqual(portal.client.access_level, "editor")

    def test_create_portal_invalid_access_level(self):
        """유효하지 않은 접근 레벨"""
        with self.assertRaises(ValueError):
            create_portal("고객", "c@e.com", "admin")

    def test_create_portal_empty_name(self):
        """빈 이름 거부"""
        with self.assertRaises(ValueError):
            create_portal("", "c@e.com")

    def test_create_portal_empty_email(self):
        """빈 이메일 거부"""
        with self.assertRaises(ValueError):
            create_portal("고객", "  ")

    def test_share_content(self):
        """콘텐츠 공유"""
        portal = create_portal("고객", "c@e.com")
        portal = share_content(portal, "content_1", "첫 번째 글")
        self.assertEqual(len(portal.shared_content), 1)
        self.assertEqual(portal.shared_content[0]["title"], "첫 번째 글")

    def test_share_content_duplicate_ignored(self):
        """중복 공유 무시"""
        portal = create_portal("고객", "c@e.com")
        portal = share_content(portal, "c1", "글1")
        portal = share_content(portal, "c1", "글1")
        self.assertEqual(len(portal.shared_content), 1)

    def test_share_content_multiple(self):
        """여러 콘텐츠 공유"""
        portal = create_portal("고객", "c@e.com")
        portal = share_content(portal, "c1", "글1")
        portal = share_content(portal, "c2", "글2")
        self.assertEqual(len(portal.shared_content), 2)

    def test_add_message(self):
        """메시지 추가"""
        portal = create_portal("고객", "c@e.com")
        portal = add_message(portal, "담당자", "안녕하세요!")
        self.assertEqual(len(portal.messages), 1)
        self.assertEqual(portal.messages[0]["sender"], "담당자")

    def test_add_message_multiple(self):
        """여러 메시지"""
        portal = create_portal("고객", "c@e.com")
        portal = add_message(portal, "A", "메시지1")
        portal = add_message(portal, "B", "메시지2")
        self.assertEqual(len(portal.messages), 2)

    def test_get_activity_log_empty(self):
        """빈 활동 로그"""
        portal = create_portal("고객", "c@e.com")
        log = get_activity_log(portal)
        self.assertEqual(log, [])

    def test_get_activity_log_mixed(self):
        """공유 + 메시지 통합 로그"""
        portal = create_portal("고객", "c@e.com")
        portal = share_content(portal, "c1", "글1")
        portal = add_message(portal, "담당자", "확인해주세요")
        log = get_activity_log(portal)
        self.assertEqual(len(log), 2)
        types = {item["type"] for item in log}
        self.assertEqual(types, {"share", "message"})

    def test_get_activity_log_sorted(self):
        """활동 로그 시간순 정렬"""
        portal = create_portal("고객", "c@e.com")
        portal = share_content(portal, "c1", "글1")
        portal = add_message(portal, "A", "메시지")
        log = get_activity_log(portal)
        # 시간 순서대로 정렬되어야 함
        timestamps = [item["timestamp"] for item in log]
        self.assertEqual(timestamps, sorted(timestamps))

    def test_create_portal_all_access_levels(self):
        """모든 접근 레벨"""
        for level in ("viewer", "reviewer", "editor"):
            portal = create_portal("고객", "c@e.com", level)
            self.assertEqual(portal.client.access_level, level)


if __name__ == "__main__":
    unittest.main()
