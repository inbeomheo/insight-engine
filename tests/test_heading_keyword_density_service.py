"""Heading Keyword Density 서비스 테스트."""
import unittest
from services.heading_keyword_density_service import analyze_heading_keyword_density


class TestHeadingKeywordDensity(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_heading_keyword_density('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_headings'], 0)

    def test_none_content(self):
        result = analyze_heading_keyword_density(None)
        self.assertEqual(result['score'], 0.0)

    def test_no_headings(self):
        content = '이 글에는 헤딩이 없습니다. 순수한 본문만 있습니다.'
        result = analyze_heading_keyword_density(content)
        self.assertEqual(result['summary']['total_headings'], 0)
        self.assertEqual(result['score'], 50.0)

    def test_headings_with_keywords(self):
        content = ('# 파이썬 프로그래밍 가이드\n'
                   '파이썬은 인기 있는 프로그래밍 언어입니다.\n'
                   '## 파이썬 설치 방법\n'
                   '파이썬을 설치하는 방법을 설명합니다.\n'
                   '## 파이썬 기본 문법\n'
                   '파이썬의 기본 문법을 알아봅시다.')
        result = analyze_heading_keyword_density(content)
        self.assertGreater(result['summary']['total_headings'], 0)
        self.assertGreater(result['summary']['body_keywords_in_headings'], 0)

    def test_headings_without_body_keywords(self):
        content = ('# 서론\n'
                   '마케팅 전략이 중요합니다. 마케팅 분석을 합니다. 마케팅 계획을 세웁니다.\n'
                   '## 본론\n'
                   '마케팅 실행이 필요합니다.\n'
                   '## 결론\n'
                   '마케팅 성과를 측정합니다.')
        result = analyze_heading_keyword_density(content)
        # 헤딩에 "마케팅"이 없으므로 커버리지 낮음
        self.assertLessEqual(result['summary']['coverage_ratio'], 50.0)

    def test_coverage_ratio(self):
        content = ('# 데이터 분석 개요\n'
                   '데이터 분석은 비즈니스에 필수입니다. '
                   '분석 도구를 활용합니다.\n'
                   '## 데이터 수집\n'
                   '데이터를 수집하는 방법입니다.')
        result = analyze_heading_keyword_density(content)
        self.assertGreaterEqual(result['summary']['coverage_ratio'], 0.0)
        self.assertLessEqual(result['summary']['coverage_ratio'], 100.0)

    def test_heading_data_structure(self):
        content = '# 테스트 제목\n본문 내용입니다.'
        result = analyze_heading_keyword_density(content)
        for h in result['headings']:
            self.assertIn('level', h)
            self.assertIn('text', h)
            self.assertIn('keywords', h)
            self.assertIn('keyword_count', h)

    def test_keyword_coverage_structure(self):
        content = ('# 개발 가이드\n'
                   '개발 프로세스를 설명합니다. 개발 환경을 구축합니다.')
        result = analyze_heading_keyword_density(content)
        for kc in result['keyword_coverage']:
            self.assertIn('keyword', kc)
            self.assertIn('in_heading', kc)

    def test_level_excellent(self):
        content = ('# 머신러닝 딥러닝 가이드\n'
                   '머신러닝과 딥러닝은 인공지능의 핵심입니다. '
                   '머신러닝 알고리즘을 학습합니다. '
                   '딥러닝 모델을 구축합니다.\n'
                   '## 머신러닝 기초\n'
                   '머신러닝의 기초를 배웁니다.\n'
                   '## 딥러닝 실전\n'
                   '딥러닝을 실전에 적용합니다.')
        result = analyze_heading_keyword_density(content)
        self.assertIn(result['summary']['level'], ('excellent', 'good', 'fair'))

    def test_score_range(self):
        content = '# 제목\n본문 내용입니다.'
        result = analyze_heading_keyword_density(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '# 테스트\n내용입니다.'
        result = analyze_heading_keyword_density(content)
        self.assertIn('headings', result)
        self.assertIn('keyword_coverage', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_headings', result['summary'])
        self.assertIn('coverage_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '# 제목\n본문에 키워드가 있습니다. 중요한 내용입니다.'
        result = analyze_heading_keyword_density(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_max_20_headings(self):
        headings = '\n'.join([f'## 섹션 {i}\n내용 {i}' for i in range(25)])
        content = f'# 메인 제목\n{headings}'
        result = analyze_heading_keyword_density(content)
        self.assertLessEqual(len(result['headings']), 20)


if __name__ == '__main__':
    unittest.main()
