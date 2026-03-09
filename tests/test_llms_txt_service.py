"""
llms.txt 생성 및 검증 서비스 테스트
"""
import unittest
from services.llms_txt_service import (
    PageMeta,
    ValidationIssue,
    generate_llms_txt,
    validate_llms_txt,
    parse_llms_txt,
    VALID_CONTENT_TYPES,
)


class TestPageMeta(unittest.TestCase):
    """PageMeta 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 변환이 올바른 딕셔너리를 반환한다"""
        page = PageMeta(
            url='https://example.com/guide',
            title='시작 가이드',
            description='입문자를 위한 가이드',
            content_type='guide',
        )
        result = page.to_dict()
        self.assertEqual(result['url'], 'https://example.com/guide')
        self.assertEqual(result['title'], '시작 가이드')
        self.assertEqual(result['content_type'], 'guide')


class TestValidationIssue(unittest.TestCase):
    """ValidationIssue 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 변환이 올바른 딕셔너리를 반환한다"""
        issue = ValidationIssue(line=5, severity='error', message='오류 메시지')
        result = issue.to_dict()
        self.assertEqual(result['line'], 5)
        self.assertEqual(result['severity'], 'error')
        self.assertEqual(result['message'], '오류 메시지')


class TestGenerateLlmsTxt(unittest.TestCase):
    """generate_llms_txt 함수 테스트"""

    def _make_pages(self, count=3):
        """테스트용 페이지 목록 생성"""
        types = ['guide', 'article', 'product', 'faq']
        return [
            {
                'url': f'https://example.com/page-{i}',
                'title': f'페이지 {i}',
                'description': f'설명 {i}',
                'content_type': types[i % len(types)],
            }
            for i in range(count)
        ]

    def test_basic_generation(self):
        """기본 페이지 목록에서 llms.txt를 생성한다"""
        pages = self._make_pages(4)
        result = generate_llms_txt(pages, site_title='테스트 사이트')
        self.assertIn('# 테스트 사이트', result)
        self.assertIn('## Guides', result)
        self.assertIn('## Articles', result)

    def test_contains_all_pages(self):
        """모든 페이지가 결과에 포함된다"""
        pages = self._make_pages(3)
        result = generate_llms_txt(pages)
        for page in pages:
            self.assertIn(page['title'], result)
            self.assertIn(page['url'], result)

    def test_with_site_description(self):
        """사이트 설명이 블록인용문으로 포함된다"""
        pages = self._make_pages(1)
        result = generate_llms_txt(pages, site_title='사이트', site_description='설명문')
        self.assertIn('> 설명문', result)

    def test_auto_site_title_from_domain(self):
        """site_title 생략 시 첫 페이지 도메인을 사용한다"""
        pages = [{'url': 'https://mysite.com/page', 'title': 'Page', 'description': '', 'content_type': 'article'}]
        result = generate_llms_txt(pages)
        self.assertIn('# mysite.com', result)

    def test_link_format(self):
        """링크가 올바른 마크다운 형식이다"""
        pages = [{'url': 'https://example.com/test', 'title': 'Test', 'description': 'Desc', 'content_type': 'article'}]
        result = generate_llms_txt(pages)
        self.assertIn('- [Test](https://example.com/test): Desc', result)

    def test_link_without_description(self):
        """설명이 없는 링크는 콜론 없이 출력된다"""
        pages = [{'url': 'https://example.com/test', 'title': 'Test', 'description': '', 'content_type': 'article'}]
        result = generate_llms_txt(pages)
        self.assertIn('- [Test](https://example.com/test)', result)
        self.assertNotIn('- [Test](https://example.com/test):', result)

    def test_section_order(self):
        """섹션이 guide → faq → article → product 순서로 출력된다"""
        pages = [
            {'url': 'https://e.com/1', 'title': 'A', 'description': '', 'content_type': 'product'},
            {'url': 'https://e.com/2', 'title': 'B', 'description': '', 'content_type': 'guide'},
            {'url': 'https://e.com/3', 'title': 'C', 'description': '', 'content_type': 'faq'},
            {'url': 'https://e.com/4', 'title': 'D', 'description': '', 'content_type': 'article'},
        ]
        result = generate_llms_txt(pages)
        guide_pos = result.index('## Guides')
        faq_pos = result.index('## FAQ')
        article_pos = result.index('## Articles')
        product_pos = result.index('## Products')
        self.assertLess(guide_pos, faq_pos)
        self.assertLess(faq_pos, article_pos)
        self.assertLess(article_pos, product_pos)

    def test_empty_pages_raises(self):
        """빈 pages 목록은 ValueError를 발생시킨다"""
        with self.assertRaises(ValueError):
            generate_llms_txt([])

    def test_missing_url_raises(self):
        """url 누락 시 ValueError를 발생시킨다"""
        pages = [{'url': '', 'title': 'Test', 'description': '', 'content_type': 'article'}]
        with self.assertRaises(ValueError):
            generate_llms_txt(pages)

    def test_missing_title_raises(self):
        """title 누락 시 ValueError를 발생시킨다"""
        pages = [{'url': 'https://e.com', 'title': '', 'description': '', 'content_type': 'article'}]
        with self.assertRaises(ValueError):
            generate_llms_txt(pages)

    def test_invalid_url_raises(self):
        """잘못된 URL 형식은 ValueError를 발생시킨다"""
        pages = [{'url': 'not-a-url', 'title': 'Test', 'description': '', 'content_type': 'article'}]
        with self.assertRaises(ValueError):
            generate_llms_txt(pages)

    def test_invalid_content_type_raises(self):
        """잘못된 content_type은 ValueError를 발생시킨다"""
        pages = [{'url': 'https://e.com', 'title': 'Test', 'description': '', 'content_type': 'blog'}]
        with self.assertRaises(ValueError):
            generate_llms_txt(pages)

    def test_default_content_type(self):
        """content_type 생략 시 기본값 article이 사용된다"""
        pages = [{'url': 'https://e.com/p', 'title': 'T', 'description': 'D'}]
        result = generate_llms_txt(pages)
        self.assertIn('## Articles', result)

    def test_ends_with_newline(self):
        """결과가 개행으로 끝난다"""
        pages = self._make_pages(1)
        result = generate_llms_txt(pages)
        self.assertTrue(result.endswith('\n'))


class TestValidateLlmsTxt(unittest.TestCase):
    """validate_llms_txt 함수 테스트"""

    def _valid_content(self):
        """유효한 llms.txt 내용"""
        return (
            '# My Site\n'
            '\n'
            '> Site description\n'
            '\n'
            '## Guides\n'
            '\n'
            '- [Getting Started](https://example.com/start): Beginner guide\n'
            '- [Advanced](https://example.com/advanced): Advanced topics\n'
            '\n'
            '## Articles\n'
            '\n'
            '- [Blog Post](https://example.com/blog): A blog post\n'
        )

    def test_valid_content_no_issues(self):
        """유효한 내용에 대해 이슈가 없다"""
        issues = validate_llms_txt(self._valid_content())
        self.assertEqual(len(issues), 0)

    def test_empty_content_error(self):
        """빈 내용은 에러를 반환한다"""
        issues = validate_llms_txt('')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, 'error')

    def test_whitespace_only_error(self):
        """공백만 있는 내용은 에러를 반환한다"""
        issues = validate_llms_txt('   \n  \n  ')
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, 'error')

    def test_missing_main_title(self):
        """메인 제목이 없으면 에러를 반환한다"""
        content = '## Section\n\n- [Link](https://e.com): desc\n'
        issues = validate_llms_txt(content)
        errors = [i for i in issues if i.severity == 'error']
        messages = [i.message for i in errors]
        self.assertTrue(any('메인 제목' in m for m in messages))

    def test_missing_links(self):
        """링크가 없으면 에러를 반환한다"""
        content = '# My Site\n\n## Section\n'
        issues = validate_llms_txt(content)
        errors = [i for i in issues if i.severity == 'error']
        messages = [i.message for i in errors]
        self.assertTrue(any('링크가 하나도 없습니다' in m for m in messages))

    def test_invalid_url_in_link(self):
        """링크의 URL이 잘못된 형식이면 에러를 반환한다"""
        content = '# Site\n\n## Sec\n\n- [Title](not-a-url): desc\n'
        issues = validate_llms_txt(content)
        errors = [i for i in issues if i.severity == 'error']
        self.assertTrue(any('잘못된 URL' in i.message for i in errors))

    def test_duplicate_url_warning(self):
        """중복 URL은 경고를 반환한다"""
        content = (
            '# Site\n\n## Sec\n\n'
            '- [A](https://e.com/same): desc1\n'
            '- [B](https://e.com/same): desc2\n'
        )
        issues = validate_llms_txt(content)
        warnings = [i for i in issues if i.severity == 'warning']
        self.assertTrue(any('중복 URL' in i.message for i in warnings))

    def test_empty_section_warning(self):
        """빈 섹션은 경고를 반환한다"""
        content = '# Site\n\n## Empty\n\n## Filled\n\n- [A](https://e.com): d\n'
        issues = validate_llms_txt(content)
        warnings = [i for i in issues if i.severity == 'warning']
        self.assertTrue(any('빈 섹션' in i.message for i in warnings))

    def test_malformed_link_warning(self):
        """잘못된 형식의 리스트 항목은 경고를 반환한다"""
        content = '# Site\n\n## Sec\n\n- 그냥 텍스트\n- [Good](https://e.com): ok\n'
        issues = validate_llms_txt(content)
        warnings = [i for i in issues if i.severity == 'warning']
        self.assertTrue(any('올바른 링크 형식' in i.message for i in warnings))

    def test_multiple_main_titles_warning(self):
        """메인 제목이 여러 개면 경고를 반환한다"""
        content = '# Site A\n\n# Site B\n\n## Sec\n\n- [A](https://e.com): d\n'
        issues = validate_llms_txt(content)
        warnings = [i for i in issues if i.severity == 'warning']
        self.assertTrue(any('여러 개' in i.message for i in warnings))

    def test_missing_section_headers_warning(self):
        """섹션 헤더가 없으면 경고를 반환한다"""
        content = '# Site\n\n- [A](https://e.com): d\n'
        issues = validate_llms_txt(content)
        warnings = [i for i in issues if i.severity == 'warning']
        self.assertTrue(any('섹션 헤더' in i.message for i in warnings))

    def test_issue_line_numbers(self):
        """이슈에 올바른 라인 번호가 포함된다"""
        content = '# Site\n\n## Sec\n\n- [A](bad-url): d\n'
        issues = validate_llms_txt(content)
        url_errors = [i for i in issues if '잘못된 URL' in i.message]
        self.assertTrue(len(url_errors) > 0)
        self.assertEqual(url_errors[0].line, 5)


class TestParseLlmsTxt(unittest.TestCase):
    """parse_llms_txt 함수 테스트"""

    def test_basic_parse(self):
        """기본 llms.txt를 올바르게 파싱한다"""
        content = (
            '# My Site\n'
            '\n'
            '> Site description\n'
            '\n'
            '## Guides\n'
            '\n'
            '- [Start](https://e.com/start): Getting started\n'
        )
        result = parse_llms_txt(content)
        self.assertEqual(result['title'], 'My Site')
        self.assertEqual(result['description'], 'Site description')
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(result['sections'][0]['name'], 'Guides')
        self.assertEqual(len(result['sections'][0]['links']), 1)
        self.assertEqual(result['sections'][0]['links'][0]['title'], 'Start')

    def test_empty_content(self):
        """빈 내용에 대해 빈 구조를 반환한다"""
        result = parse_llms_txt('')
        self.assertEqual(result['title'], '')
        self.assertEqual(result['description'], '')
        self.assertEqual(len(result['sections']), 0)

    def test_multiple_sections(self):
        """여러 섹션을 올바르게 파싱한다"""
        content = (
            '# Site\n'
            '\n'
            '## Guides\n'
            '- [A](https://e.com/a): desc a\n'
            '\n'
            '## FAQ\n'
            '- [B](https://e.com/b): desc b\n'
        )
        result = parse_llms_txt(content)
        self.assertEqual(len(result['sections']), 2)
        self.assertEqual(result['sections'][0]['name'], 'Guides')
        self.assertEqual(result['sections'][1]['name'], 'FAQ')

    def test_link_without_description(self):
        """설명 없는 링크를 올바르게 파싱한다"""
        content = '# Site\n\n## Sec\n\n- [Title](https://e.com/t)\n'
        result = parse_llms_txt(content)
        link = result['sections'][0]['links'][0]
        self.assertEqual(link['title'], 'Title')
        self.assertEqual(link['url'], 'https://e.com/t')
        self.assertEqual(link['description'], '')


class TestRoundTrip(unittest.TestCase):
    """생성 → 검증 → 파싱 왕복 테스트"""

    def test_generated_content_validates(self):
        """generate_llms_txt 결과가 validate_llms_txt를 통과한다"""
        pages = [
            {'url': 'https://example.com/guide', 'title': 'Guide', 'description': 'A guide', 'content_type': 'guide'},
            {'url': 'https://example.com/faq', 'title': 'FAQ', 'description': 'Questions', 'content_type': 'faq'},
            {'url': 'https://example.com/blog', 'title': 'Blog', 'description': 'Post', 'content_type': 'article'},
        ]
        content = generate_llms_txt(pages, site_title='Test Site', site_description='Description')
        issues = validate_llms_txt(content)
        errors = [i for i in issues if i.severity == 'error']
        self.assertEqual(len(errors), 0, f'검증 에러: {[i.message for i in errors]}')

    def test_generate_then_parse(self):
        """생성한 llms.txt를 파싱하면 원본 데이터가 복원된다"""
        pages = [
            {'url': 'https://example.com/guide', 'title': 'Guide', 'description': 'A guide', 'content_type': 'guide'},
            {'url': 'https://example.com/product', 'title': 'Product', 'description': 'Item', 'content_type': 'product'},
        ]
        content = generate_llms_txt(pages, site_title='My Site', site_description='My Desc')
        parsed = parse_llms_txt(content)
        self.assertEqual(parsed['title'], 'My Site')
        self.assertEqual(parsed['description'], 'My Desc')
        # 모든 URL이 파싱 결과에 존재
        all_urls = {link['url'] for sec in parsed['sections'] for link in sec['links']}
        for page in pages:
            self.assertIn(page['url'], all_urls)


if __name__ == '__main__':
    unittest.main()
