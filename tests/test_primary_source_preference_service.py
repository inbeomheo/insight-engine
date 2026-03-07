"""Primary Source Preference Checker 서비스 테스트."""
import unittest
from services.primary_source_preference_service import check_primary_source_preference


class TestPrimarySourcePreference(unittest.TestCase):

    def test_empty_content(self):
        result = check_primary_source_preference('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_primary_source_preference(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_urls(self):
        content = '출처 없이 작성된 일반 텍스트입니다. 다양한 내용을 포함합니다.'
        result = check_primary_source_preference(content)
        self.assertEqual(result['summary']['total_urls'], 0)

    def test_primary_sources(self):
        content = ('공식 문서를 참조하세요: https://docs.python.org/3/library/re.html '
                   '학술 자료: https://arxiv.org/abs/2301.12345 '
                   '정부 자료: https://www.gov.kr/portal/policy')
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['primary_count'], 0)
        self.assertIn(result['summary']['level'], ('excellent', 'good'))

    def test_secondary_sources(self):
        content = ('참고: https://medium.com/some-article '
                   '블로그: https://blog.example.com/post '
                   '토론: https://stackoverflow.com/questions/123 '
                   '뉴스: https://techcrunch.com/2024/01/article')
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['secondary_count'], 0)

    def test_mixed_sources(self):
        content = ('1차: https://docs.python.org/3/tutorial '
                   '2차: https://medium.com/python-guide '
                   '1차: https://doi.org/10.1234/example')
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['primary_count'], 0)
        self.assertGreater(result['summary']['secondary_count'], 0)

    def test_academic_citations(self):
        content = ('Smith et al. (2024)에 따르면 결과가 유의미합니다. '
                   'Kim et al. (2023)의 연구도 동일한 결론입니다. '
                   'Journal of AI, Vol. 15, pp. 123-145.')
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['academic_citations'], 0)

    def test_citation_mentions(self):
        content = ('공식 문서에 따르면 이 기능은 안정적입니다. '
                   '연구에 의하면 효과가 입증되었습니다. '
                   'According to the official documentation, this works.')
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['citation_mentions'], 0)

    def test_all_secondary_poor(self):
        content = ('https://medium.com/article1 에서 확인하세요. '
                   'https://blog.example.com/post2 참고. '
                   'https://reddit.com/r/topic/thread 토론. '
                   'https://youtube.com/watch?v=abc123 영상.')
        result = check_primary_source_preference(content)
        self.assertIn(result['summary']['level'], ('poor', 'fair'))

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_primary_source_preference(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_primary_source_preference(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('source_tiers', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_urls', result['summary'])
        self.assertIn('primary_count', result['summary'])
        self.assertIn('secondary_count', result['summary'])
        self.assertIn('primary_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = 'https://medium.com/article 만 참고했습니다.'
        result = check_primary_source_preference(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_gov_kr_primary(self):
        content = '정부 사이트 참조: https://www.mois.go.kr/policy/overview'
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['primary_count'], 0)

    def test_edu_primary(self):
        content = '학교 연구: https://cs.stanford.edu/research/paper.pdf'
        result = check_primary_source_preference(content)
        self.assertGreater(result['summary']['primary_count'], 0)


if __name__ == '__main__':
    unittest.main()
