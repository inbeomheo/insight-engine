"""스폰서 워크스페이스 서비스 테스트"""

import unittest
from services.sponsor_workspace_service import (
    SponsorDeal, SponsorWorkspace,
    create_deal, update_deal_status, calculate_revenue,
    get_active_deals, check_deliverables,
)


class TestSponsorWorkspaceService(unittest.TestCase):
    """스폰서 워크스페이스 서비스 테스트"""

    def test_create_deal_basic(self):
        """기본 딜 생성"""
        deal = create_deal("BrandX", 1000.0, ["블로그 1편", "영상 1편"])
        self.assertEqual(deal.sponsor_name, "BrandX")
        self.assertEqual(deal.budget, 1000.0)
        self.assertEqual(deal.status, "draft")
        self.assertEqual(len(deal.deliverables), 2)

    def test_create_deal_negative_budget(self):
        """음수 예산 거부"""
        with self.assertRaises(ValueError):
            create_deal("X", -100, [])

    def test_create_deal_empty_name(self):
        """빈 이름 거부"""
        with self.assertRaises(ValueError):
            create_deal("", 100, [])

    def test_update_deal_status_draft_to_active(self):
        """draft → active 전이"""
        deal = create_deal("X", 100, [])
        updated = update_deal_status(deal, "active")
        self.assertEqual(updated.status, "active")

    def test_update_deal_status_active_to_completed(self):
        """active → completed 전이"""
        deal = create_deal("X", 100, [])
        update_deal_status(deal, "active")
        updated = update_deal_status(deal, "completed")
        self.assertEqual(updated.status, "completed")

    def test_update_deal_status_invalid_transition(self):
        """유효하지 않은 전이 거부"""
        deal = create_deal("X", 100, [])
        with self.assertRaises(ValueError):
            update_deal_status(deal, "completed")  # draft → completed 불가

    def test_update_deal_status_invalid_status(self):
        """유효하지 않은 상태 거부"""
        deal = create_deal("X", 100, [])
        with self.assertRaises(ValueError):
            update_deal_status(deal, "unknown")

    def test_calculate_revenue(self):
        """수익 계산 (active + completed만)"""
        d1 = create_deal("A", 500, [])
        update_deal_status(d1, "active")
        d2 = create_deal("B", 300, [])
        update_deal_status(d2, "active")
        update_deal_status(d2, "completed")
        d3 = create_deal("C", 200, [])  # draft
        d4 = create_deal("D", 400, [])
        update_deal_status(d4, "active")
        update_deal_status(d4, "cancelled")

        ws = SponsorWorkspace(workspace_id="ws1", deals=[d1, d2, d3, d4])
        revenue = calculate_revenue(ws)
        self.assertEqual(revenue, 800.0)  # 500 + 300
        self.assertEqual(ws.total_revenue, 800.0)

    def test_get_active_deals(self):
        """활성 딜 필터링"""
        d1 = create_deal("A", 100, [])
        update_deal_status(d1, "active")
        d2 = create_deal("B", 200, [])  # draft

        ws = SponsorWorkspace(workspace_id="ws1", deals=[d1, d2])
        active = get_active_deals(ws)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0].sponsor_name, "A")

    def test_check_deliverables(self):
        """산출물 체크리스트"""
        deal = create_deal("X", 100, ["블로그", "영상", "SNS"])
        result = check_deliverables(deal)
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["items"]), 3)
        # 초기 상태 모두 미완료
        for item in result["items"]:
            self.assertFalse(item["completed"])

    def test_check_deliverables_empty(self):
        """빈 산출물"""
        deal = create_deal("X", 100, [])
        result = check_deliverables(deal)
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["items"], [])

    def test_completed_deal_cannot_change(self):
        """완료된 딜은 상태 변경 불가"""
        deal = create_deal("X", 100, [])
        update_deal_status(deal, "active")
        update_deal_status(deal, "completed")
        with self.assertRaises(ValueError):
            update_deal_status(deal, "active")


if __name__ == "__main__":
    unittest.main()
