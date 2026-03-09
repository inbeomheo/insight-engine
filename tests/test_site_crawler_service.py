"""site_crawler_service 단위 테스트."""

import unittest

from services.site_crawler_service import (
    CrawlResult,
    PageContent,
    crawl_site,
    extract_links,
    is_allowed_by_robots,
    is_same_domain,
    normalize_url,
)


class TestNormalizeUrl(unittest.TestCase):
    """URL 정규화 함수."""

    def test_removes_fragment(self):
        self.assertEqual(
            normalize_url('https://example.com/page#section'),
            'https://example.com/page',
        )

    def test_removes_trailing_slash(self):
        self.assertEqual(
            normalize_url('https://example.com/page/'),
            'https://example.com/page',
        )

    def test_preserves_root_slash(self):
        url = normalize_url('https://example.com/')
        parsed_path = url.split('example.com')[-1]
        self.assertIn('/', parsed_path)

    def test_adds_root_path(self):
        url = normalize_url('https://example.com')
        self.assertIn('/', url)


class TestIsSameDomain(unittest.TestCase):
    """동일 도메인 판별."""

    def test_same_domain(self):
        self.assertTrue(is_same_domain(
            'https://example.com/about',
            'https://example.com/',
        ))

    def test_different_domain(self):
        self.assertFalse(is_same_domain(
            'https://other.com/page',
            'https://example.com/',
        ))

    def test_subdomain_is_different(self):
        self.assertFalse(is_same_domain(
            'https://blog.example.com/',
            'https://example.com/',
        ))


class TestIsAllowedByRobots(unittest.TestCase):
    """robots.txt 시뮬레이션."""

    def test_default_blocked_admin(self):
        self.assertFalse(is_allowed_by_robots('https://example.com/admin'))

    def test_default_blocked_api(self):
        self.assertFalse(is_allowed_by_robots('https://example.com/api/v1/data'))

    def test_allowed_normal_page(self):
        self.assertTrue(is_allowed_by_robots('https://example.com/about'))

    def test_custom_disallowed(self):
        self.assertFalse(is_allowed_by_robots(
            'https://example.com/secret/data',
            disallowed_paths=['/secret'],
        ))

    def test_empty_disallowed_allows_all(self):
        self.assertTrue(is_allowed_by_robots(
            'https://example.com/admin',
            disallowed_paths=[],
        ))


class TestExtractLinks(unittest.TestCase):
    """HTML 링크 추출."""

    def test_absolute_links(self):
        html = '<a href="https://example.com/page1">Link</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertIn('https://example.com/page1', links)

    def test_relative_links(self):
        html = '<a href="/about">About</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertIn('https://example.com/about', links)

    def test_ignores_javascript(self):
        html = '<a href="javascript:void(0)">Click</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertEqual(links, [])

    def test_ignores_mailto(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertEqual(links, [])

    def test_deduplicates(self):
        html = '<a href="/page">A</a><a href="/page">B</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertEqual(len(links), 1)

    def test_empty_html(self):
        self.assertEqual(extract_links('', 'https://example.com/'), [])

    def test_removes_fragment_in_links(self):
        html = '<a href="/page#top">Page</a>'
        links = extract_links(html, 'https://example.com/')
        self.assertEqual(links, ['https://example.com/page'])


class TestCrawlSite(unittest.TestCase):
    """crawl_site BFS 크롤링."""

    def _make_fetcher(self, page_map: dict[str, str]):
        """URL → HTML 매핑 기반 fetch 함수 생성. 키도 정규화하여 매칭."""
        normalized_map = {normalize_url(k): v for k, v in page_map.items()}
        def fetch(url: str) -> str | None:
            return normalized_map.get(normalize_url(url))
        return fetch

    def test_empty_url(self):
        result = crawl_site('')
        self.assertEqual(result.total_pages, 0)
        self.assertTrue(len(result.errors) > 0)

    def test_single_page(self):
        pages = {
            'https://example.com': '<html><title>Home</title><body>Welcome</body></html>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(result.pages[0].title, 'Home')

    def test_follows_internal_links(self):
        pages = {
            'https://example.com': '<a href="/about">About</a>',
            'https://example.com/about': '<title>About</title><p>About us</p>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        self.assertEqual(result.total_pages, 2)
        urls = [p.url for p in result.pages]
        self.assertIn('https://example.com/about', urls)

    def test_respects_max_pages(self):
        # 3페이지가 연결되어 있지만 max_pages=2
        pages = {
            'https://example.com': '<a href="/a">A</a><a href="/b">B</a>',
            'https://example.com/a': '<a href="/b">B</a>',
            'https://example.com/b': '<p>Page B</p>',
        }
        result = crawl_site('https://example.com', max_pages=2, fetch_fn=self._make_fetcher(pages))
        self.assertLessEqual(result.total_pages, 2)

    def test_respects_max_depth(self):
        # 깊이 3: / → /a → /b → /c
        pages = {
            'https://example.com': '<a href="/a">A</a>',
            'https://example.com/a': '<a href="/b">B</a>',
            'https://example.com/b': '<a href="/c">C</a>',
            'https://example.com/c': '<p>Deep</p>',
        }
        result = crawl_site('https://example.com', max_depth=2, fetch_fn=self._make_fetcher(pages))
        urls = [p.url for p in result.pages]
        # depth 0, 1, 2 까지만 수집 (/ → /a → /b)
        self.assertIn('https://example.com/b', urls)
        self.assertNotIn('https://example.com/c', urls)

    def test_skips_external_links(self):
        pages = {
            'https://example.com': '<a href="https://other.com/page">External</a>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        self.assertEqual(result.total_pages, 1)

    def test_robots_blocked_page(self):
        pages = {
            'https://example.com': '<a href="/admin/secret">Admin</a>',
            'https://example.com/admin/secret': '<p>Secret</p>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        urls = [p.url for p in result.pages]
        self.assertNotIn('https://example.com/admin/secret', urls)
        # 에러 목록에 차단 기록
        self.assertTrue(any('robots.txt' in e for e in result.errors))

    def test_no_duplicate_visits(self):
        # 순환 참조: / ↔ /about
        pages = {
            'https://example.com': '<a href="/about">About</a>',
            'https://example.com/about': '<a href="/">Home</a>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        self.assertEqual(result.total_pages, 2)

    def test_fetch_error_handled(self):
        def failing_fetch(url: str):
            raise ConnectionError('네트워크 오류')

        result = crawl_site('https://example.com', fetch_fn=failing_fetch)
        self.assertEqual(result.total_pages, 0)
        self.assertTrue(len(result.errors) > 0)

    def test_simulation_mode_without_fetch_fn(self):
        """fetch_fn 없으면 빈 HTML로 동작 (시뮬레이션)."""
        result = crawl_site('https://example.com')
        self.assertEqual(result.total_pages, 1)
        self.assertEqual(result.pages[0].content, '')

    def test_depth_tracking(self):
        pages = {
            'https://example.com': '<a href="/a">A</a>',
            'https://example.com/a': '<a href="/b">B</a>',
            'https://example.com/b': '<p>End</p>',
        }
        result = crawl_site('https://example.com', fetch_fn=self._make_fetcher(pages))
        self.assertEqual(result.max_depth_reached, 2)

    def test_crawl_result_dataclass(self):
        result = CrawlResult()
        self.assertEqual(result.pages, [])
        self.assertEqual(result.total_pages, 0)
        self.assertEqual(result.max_depth_reached, 0)
        self.assertEqual(result.errors, [])

    def test_page_content_dataclass(self):
        page = PageContent(url='https://x.com', title='X', content='body')
        self.assertEqual(page.links, [])
        self.assertEqual(page.depth, 0)
        self.assertIsInstance(page.crawled_at, str)


if __name__ == '__main__':
    unittest.main()
