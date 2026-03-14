"""
MarketplaceService 단위 테스트 (F4-14)
"""
import unittest
from services.platform.marketplace_service import MarketplaceService


class TestMarketplaceService(unittest.TestCase):

    def setUp(self):
        self.svc = MarketplaceService()

    def test_publish_template(self):
        result = self.svc.publish_template('author-1', 'SEO 블로그', '설명', 'prompt text')
        self.assertIn('id', result)
        self.assertEqual(result['status'], 'published')

    def test_publish_empty_title_rejected(self):
        result = self.svc.publish_template('author-1', '', '', '')
        self.assertIn('error', result)

    def test_list_and_search(self):
        self.svc.publish_template('a1', 'SEO 블로그', 'SEO 관련', 'p1', category='blog')
        self.svc.publish_template('a1', '마케팅', '마케팅 관련', 'p2', category='marketing')
        self.assertEqual(len(self.svc.list_templates()), 2)
        self.assertEqual(len(self.svc.list_templates(category='blog')), 1)
        self.assertEqual(len(self.svc.list_templates(query='마케팅')), 1)

    def test_download_increments_count(self):
        t = self.svc.publish_template('a1', 'T', 'D', 'P')
        self.svc.download_template(t['id'], 'u1')
        self.svc.download_template(t['id'], 'u2')
        self.assertEqual(self.svc.get_template(t['id'])['downloads'], 2)

    def test_download_not_found(self):
        result = self.svc.download_template('nope', 'u1')
        self.assertIn('error', result)

    def test_rate_template(self):
        t = self.svc.publish_template('a1', 'T', 'D', 'P')
        self.svc.rate_template(t['id'], 'u1', 5.0)
        self.svc.rate_template(t['id'], 'u2', 3.0)
        template = self.svc.get_template(t['id'])
        self.assertEqual(template['rating_count'], 2)
        self.assertAlmostEqual(template['rating'], 4.0, places=1)

    def test_rate_invalid_score(self):
        t = self.svc.publish_template('a1', 'T', 'D', 'P')
        result = self.svc.rate_template(t['id'], 'u1', 6.0)
        self.assertIn('error', result)

    def test_unpublish(self):
        t = self.svc.publish_template('a1', 'T', 'D', 'P')
        self.svc.unpublish_template(t['id'], 'a1')
        # 비공개 후 목록에 안 나옴
        self.assertEqual(len(self.svc.list_templates()), 0)

    def test_unpublish_wrong_author(self):
        t = self.svc.publish_template('a1', 'T', 'D', 'P')
        result = self.svc.unpublish_template(t['id'], 'a2')
        self.assertIn('error', result)


if __name__ == '__main__':
    unittest.main()
