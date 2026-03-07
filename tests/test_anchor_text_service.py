"""anchor_text_service 단위 테스트"""
import unittest

from services.anchor_text_service import (
    audit_anchor_texts,
    _classify_anchor,
    _extract_links,
)


class TestAuditAnchorTexts(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠는 빈 결과를 반환한다."""
        result = audit_anchor_texts('')
        self.assertEqual(result['links'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['anchor_quality_score'], 100.0)

    def test_no_links(self):
        """링크가 없는 콘텐츠는 빈 결과를 반환한다."""
        result = audit_anchor_texts('이 문장에는 링크가 전혀 없습니다.')
        self.assertEqual(result['links'], [])
        self.assertEqual(result['summary']['total'], 0)

    def test_markdown_link_extraction(self):
        """마크다운 링크를 올바르게 추출한다."""
        content = '참고: [파이썬 공식 문서](https://python.org)를 확인하세요.'
        result = audit_anchor_texts(content)
        self.assertEqual(len(result['links']), 1)
        self.assertEqual(result['links'][0]['anchor'], '파이썬 공식 문서')
        self.assertEqual(result['links'][0]['url'], 'https://python.org')

    def test_html_link_extraction(self):
        """HTML 링크를 올바르게 추출한다."""
        content = '참고: <a href="https://python.org">파이썬 공식 문서</a>를 확인하세요.'
        result = audit_anchor_texts(content)
        self.assertEqual(len(result['links']), 1)
        self.assertEqual(result['links'][0]['anchor'], '파이썬 공식 문서')
        self.assertEqual(result['links'][0]['url'], 'https://python.org')

    def test_bad_anchor_detection(self):
        """모호한 앵커 텍스트를 'bad'로 판정한다."""
        content = '[여기](https://example.com)를 클릭하세요.'
        result = audit_anchor_texts(content)
        self.assertEqual(result['links'][0]['quality'], 'bad')

        content2 = '[click here](https://example.com)'
        result2 = audit_anchor_texts(content2)
        self.assertEqual(result2['links'][0]['quality'], 'bad')

    def test_generic_anchor_detection(self):
        """일반적 앵커 텍스트를 'generic'으로 판정한다."""
        content = '[자세히 보기](https://example.com/details)'
        result = audit_anchor_texts(content)
        self.assertEqual(result['links'][0]['quality'], 'generic')

        content2 = '[read more](https://example.com/article)'
        result2 = audit_anchor_texts(content2)
        self.assertEqual(result2['links'][0]['quality'], 'generic')

    def test_good_anchor_detection(self):
        """구체적 앵커 텍스트를 'good'으로 판정한다."""
        content = '[React 상태 관리 가이드](https://react.dev/learn/state)'
        result = audit_anchor_texts(content)
        self.assertEqual(result['links'][0]['quality'], 'good')

    def test_naked_url_detection(self):
        """앵커가 URL 자체인 경우 'naked_url'로 판정한다."""
        content = '[https://example.com](https://example.com)'
        result = audit_anchor_texts(content)
        self.assertEqual(result['links'][0]['quality'], 'naked_url')

    def test_quality_score_range(self):
        """품질 점수는 0-100 범위 내에 있어야 한다."""
        # 모두 good → 100점
        content_good = '[파이썬 튜토리얼](https://python.org/tutorial)'
        result_good = audit_anchor_texts(content_good)
        self.assertEqual(result_good['anchor_quality_score'], 100.0)

        # 모두 bad → 0점
        content_bad = '[여기](https://a.com) [클릭](https://b.com)'
        result_bad = audit_anchor_texts(content_bad)
        self.assertEqual(result_bad['anchor_quality_score'], 0.0)

        # 혼합 → 0~100 사이
        content_mixed = '[파이썬 가이드](https://a.com) [여기](https://b.com)'
        result_mixed = audit_anchor_texts(content_mixed)
        self.assertGreaterEqual(result_mixed['anchor_quality_score'], 0)
        self.assertLessEqual(result_mixed['anchor_quality_score'], 100)

    def test_mixed_links(self):
        """마크다운과 HTML 링크가 혼합된 콘텐츠를 처리한다."""
        content = (
            '[Git 브랜치 전략](https://git-scm.com/book) 참고. '
            '<a href="https://docs.github.com">여기</a>도 확인. '
            '[더보기](https://example.com/more)'
        )
        result = audit_anchor_texts(content)
        self.assertEqual(result['summary']['total'], 3)
        self.assertEqual(result['summary']['good'], 1)
        self.assertEqual(result['summary']['bad'], 1)
        self.assertEqual(result['summary']['generic'], 1)

    def test_suggestion_for_bad(self):
        """bad 품질 링크에는 개선 제안이 포함된다."""
        content = '[여기](https://example.com)'
        result = audit_anchor_texts(content)
        link = result['links'][0]
        self.assertEqual(link['quality'], 'bad')
        self.assertNotEqual(link['suggestion'], '')
        self.assertIn('구체적', link['suggestion'])

    def test_summary_counts(self):
        """summary의 각 카운트가 정확하다."""
        content = (
            '[Tailwind CSS 설치 방법](https://tailwindcss.com/docs/installation) '
            '[여기](https://a.com) '
            '[클릭](https://b.com) '
            '[자세히 보기](https://c.com) '
            '[https://d.com](https://d.com)'
        )
        result = audit_anchor_texts(content)
        s = result['summary']
        self.assertEqual(s['total'], 5)
        self.assertEqual(s['good'], 1)
        self.assertEqual(s['bad'], 2)
        self.assertEqual(s['generic'], 1)
        self.assertEqual(s['naked_url'], 1)

    def test_none_content(self):
        """None 입력도 안전하게 처리한다."""
        result = audit_anchor_texts(None)
        self.assertEqual(result['links'], [])
        self.assertEqual(result['summary']['total'], 0)

    def test_good_anchor_no_suggestion(self):
        """good 품질 링크에는 개선 제안이 없다."""
        content = '[TypeScript 핸드북](https://www.typescriptlang.org/docs/handbook/)'
        result = audit_anchor_texts(content)
        self.assertEqual(result['links'][0]['quality'], 'good')
        self.assertEqual(result['links'][0]['suggestion'], '')


if __name__ == '__main__':
    unittest.main()
