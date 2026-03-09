"""포트폴리오 바인더 서비스 테스트"""

import unittest
from services.portfolio_binder_service import (
    PortfolioItem, Portfolio,
    create_portfolio, add_item, curate_highlights,
    generate_summary, export_portfolio,
)


class TestPortfolioBinderService(unittest.TestCase):
    """포트폴리오 바인더 서비스 테스트"""

    def test_create_portfolio_basic(self):
        """기본 포트폴리오 생성"""
        p = create_portfolio("작성자A", bio="콘텐츠 크리에이터")
        self.assertEqual(p.owner, "작성자A")
        self.assertEqual(p.bio, "콘텐츠 크리에이터")
        self.assertEqual(len(p.items), 0)

    def test_create_portfolio_empty_owner(self):
        """빈 소유자 거부"""
        with self.assertRaises(ValueError):
            create_portfolio("")

    def test_add_item_basic(self):
        """항목 추가"""
        p = create_portfolio("작성자")
        p = add_item(p, {
            "title": "첫 글",
            "content_type": "blog",
            "metrics": {"views": 100, "likes": 10},
            "tags": ["python", "tutorial"],
        })
        self.assertEqual(len(p.items), 1)
        self.assertEqual(p.items[0].title, "첫 글")

    def test_add_item_invalid_type(self):
        """유효하지 않은 콘텐츠 타입"""
        p = create_portfolio("작성자")
        with self.assertRaises(ValueError):
            add_item(p, {"title": "글", "content_type": "webinar"})

    def test_add_item_all_types(self):
        """모든 콘텐츠 타입"""
        p = create_portfolio("작성자")
        for ct in ("blog", "video", "podcast", "social", "newsletter", "tutorial"):
            p = add_item(p, {"title": ct, "content_type": ct})
        self.assertEqual(len(p.items), 6)

    def test_add_item_featured(self):
        """하이라이트 항목"""
        p = create_portfolio("작성자")
        p = add_item(p, {"title": "대표작", "content_type": "blog", "featured": True})
        self.assertTrue(p.items[0].featured)

    def test_curate_highlights_featured_first(self):
        """하이라이트 선정 — featured 우선"""
        p = create_portfolio("작성자")
        p = add_item(p, {"title": "일반", "content_type": "blog", "metrics": {"views": 1000}})
        p = add_item(p, {"title": "대표", "content_type": "blog", "metrics": {"views": 10}, "featured": True})
        highlights = curate_highlights(p, 1)
        self.assertEqual(highlights[0].title, "대표")

    def test_curate_highlights_metric_based(self):
        """메트릭 기반 정렬"""
        p = create_portfolio("작성자")
        p = add_item(p, {"title": "저조", "content_type": "blog", "metrics": {"views": 10}})
        p = add_item(p, {"title": "인기", "content_type": "blog", "metrics": {"views": 1000, "shares": 50}})
        p = add_item(p, {"title": "보통", "content_type": "blog", "metrics": {"views": 100}})
        highlights = curate_highlights(p, 2)
        self.assertEqual(highlights[0].title, "인기")

    def test_curate_highlights_count(self):
        """요청 개수만큼 반환"""
        p = create_portfolio("작성자")
        for i in range(10):
            p = add_item(p, {"title": f"글{i}", "content_type": "blog"})
        highlights = curate_highlights(p, 3)
        self.assertEqual(len(highlights), 3)

    def test_curate_highlights_exceeds_total(self):
        """요청이 전체보다 크면 전체 반환"""
        p = create_portfolio("작성자")
        p = add_item(p, {"title": "유일한 글", "content_type": "blog"})
        highlights = curate_highlights(p, 10)
        self.assertEqual(len(highlights), 1)

    def test_generate_summary(self):
        """포트폴리오 요약"""
        p = create_portfolio("작성자")
        p = add_item(p, {"title": "블로그1", "content_type": "blog", "metrics": {"views": 100}, "featured": True})
        p = add_item(p, {"title": "영상1", "content_type": "video", "metrics": {"views": 200}})
        p = add_item(p, {"title": "블로그2", "content_type": "blog", "metrics": {"views": 50}})
        summary = generate_summary(p)
        self.assertEqual(summary["total_items"], 3)
        self.assertEqual(summary["type_distribution"]["blog"], 2)
        self.assertEqual(summary["type_distribution"]["video"], 1)
        self.assertEqual(summary["featured_count"], 1)
        self.assertEqual(summary["total_views"], 350)

    def test_generate_summary_empty(self):
        """빈 포트폴리오 요약"""
        p = create_portfolio("작성자")
        summary = generate_summary(p)
        self.assertEqual(summary["total_items"], 0)
        self.assertEqual(summary["total_views"], 0)

    def test_export_portfolio(self):
        """포트폴리오 내보내기"""
        p = create_portfolio("작성자", "바이오")
        p = add_item(p, {"title": "글1", "content_type": "blog", "tags": ["tag1"]})
        exported = export_portfolio(p)
        self.assertEqual(exported["owner"], "작성자")
        self.assertEqual(exported["bio"], "바이오")
        self.assertEqual(exported["total_items"], 1)
        self.assertEqual(len(exported["items"]), 1)
        self.assertIn("tags", exported["items"][0])

    def test_export_portfolio_empty(self):
        """빈 포트폴리오 내보내기"""
        p = create_portfolio("작성자")
        exported = export_portfolio(p)
        self.assertEqual(exported["total_items"], 0)
        self.assertEqual(exported["items"], [])


if __name__ == "__main__":
    unittest.main()
