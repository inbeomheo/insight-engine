"""backlink_service recommend_internal_links 단위 테스트"""
import unittest

from services.backlink_service import recommend_internal_links


class TestRecommendInternalLinks(unittest.TestCase):

    def test_empty_content(self):
        self.assertEqual(recommend_internal_links('', []), [])

    def test_empty_existing(self):
        self.assertEqual(recommend_internal_links('Python 개발', []), [])

    def test_related_content(self):
        existing = [
            {'id': '1', 'title': 'Python 프로그래밍 입문', 'url': 'https://example.com/1'},
            {'id': '2', 'title': '요리 레시피 모음', 'url': 'https://example.com/2'},
        ]
        result = recommend_internal_links(
            'Python 프로그래밍 학습 가이드 개발', existing,
        )
        # Python 관련 콘텐츠가 추천되어야 함
        urls = [r['url'] for r in result]
        self.assertIn('https://example.com/1', urls)

    def test_max_links_limit(self):
        existing = [
            {'id': str(i), 'title': f'Python 개발 튜토리얼 {i}', 'url': f'https://example.com/{i}'}
            for i in range(10)
        ]
        result = recommend_internal_links('Python 개발 튜토리얼 학습', existing)
        self.assertLessEqual(len(result), 2)  # MAX_INTERNAL_LINKS

    def test_has_anchor_text(self):
        existing = [
            {'id': '1', 'title': 'Python 프로그래밍', 'url': 'https://example.com/1'},
        ]
        result = recommend_internal_links('Python 프로그래밍 학습', existing)
        if result:
            self.assertIn('anchor_text', result[0])

    def test_no_match(self):
        existing = [
            {'id': '1', 'title': '요리 레시피', 'url': 'https://example.com/1'},
        ]
        result = recommend_internal_links('블록체인 기술 분석', existing)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
