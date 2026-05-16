"""link_extractor_service 단위 테스트"""
import unittest

from services.content.link_extractor_service import (
    extract_links,
    _make_link,
)


class TestExtractLinks(unittest.TestCase):

    def test_empty_content(self):
        result = extract_links('')
        self.assertEqual(result['total'], 0)

    def test_none_content(self):
        result = extract_links(None)
        self.assertEqual(result['total'], 0)

    def test_markdown_link(self):
        text = '[구글](https://google.com)을 방문하세요.'
        result = extract_links(text)
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['links'][0]['text'], '구글')
        self.assertEqual(result['links'][0]['type'], 'external')

    def test_markdown_image(self):
        text = '![대체텍스트](https://example.com/img.png)'
        result = extract_links(text)
        self.assertGreater(result['total'], 0)
        images = [l for l in result['links'] if l['type'] == 'image']
        self.assertEqual(len(images), 1)

    def test_bare_url(self):
        text = '여기에 https://example.com/page 가 있습니다.'
        result = extract_links(text)
        bare = [l for l in result['links'] if l['type'] == 'bare']
        self.assertGreater(len(bare), 0)

    def test_html_anchor(self):
        text = '<a href="https://test.com">테스트</a>'
        result = extract_links(text)
        self.assertGreater(result['total'], 0)

    def test_no_duplicates(self):
        text = '[A](https://a.com) [B](https://a.com)'
        result = extract_links(text)
        urls = [l['url'] for l in result['links']]
        self.assertEqual(len(urls), len(set(urls)))

    def test_by_type_counts(self):
        text = '[링크](https://a.com)\n![이미지](https://b.com/img.png)'
        result = extract_links(text)
        self.assertGreaterEqual(result['by_type']['external'], 1)
        self.assertGreaterEqual(result['by_type']['image'], 1)

    def test_domains_extracted(self):
        text = '[A](https://google.com/1)\n[B](https://google.com/2)\n[C](https://github.com)'
        result = extract_links(text)
        self.assertIn('google.com', result['domains'])
        self.assertEqual(result['domains']['google.com'], 2)

    def test_anchor_links_skipped(self):
        text = '[섹션](#section-1)'
        result = extract_links(text)
        # #으로 시작하는 앵커는 외부 링크로 추출하지 않음
        external = [l for l in result['links'] if l['type'] == 'external']
        self.assertEqual(len(external), 0)

    def test_mixed_content(self):
        text = """# 제목

[링크1](https://a.com) 텍스트
![이미지](https://b.com/img.png)
방문: https://c.com/page
<a href="https://d.com">HTML링크</a>"""
        result = extract_links(text)
        self.assertGreaterEqual(result['total'], 4)


class TestMakeLink(unittest.TestCase):

    def test_basic(self):
        link = _make_link('https://example.com/page', '링크', 'external')
        self.assertEqual(link['url'], 'https://example.com/page')
        self.assertEqual(link['domain'], 'example.com')
        self.assertEqual(link['type'], 'external')

    def test_no_domain(self):
        link = _make_link('/relative/path', '상대', 'external')
        self.assertEqual(link['domain'], '')


if __name__ == '__main__':
    unittest.main()
