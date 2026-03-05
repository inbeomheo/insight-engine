"""
SEO 자동 최적화 에이전트 단위 테스트 (F3-08)
"""
import unittest


class TestSeoOptimize(unittest.TestCase):
    """seo_optimize_agent.optimize_seo 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("")
        self.assertEqual(result['score'], 0)
        self.assertTrue(any('비어' in s for s in result['suggestions']))

    def test_short_content_penalty(self):
        """300자 미만 짧은 콘텐츠"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("짧은 글입니다.")
        self.assertTrue(any('짧' in s for s in result['suggestions']))

    def test_heading_structure_detection(self):
        """H2/H3 헤딩 구조 감지"""
        from services.agents.seo_optimize_agent import optimize_seo
        content = "## 소개\n\n내용입니다.\n\n## 본론\n\n### 세부사항\n\n더 많은 내용."
        result = optimize_seo(content)
        self.assertEqual(result['heading_structure']['h2'], 2)
        self.assertEqual(result['heading_structure']['h3'], 1)

    def test_keyword_density(self):
        """키워드 밀도 분석"""
        from services.agents.seo_optimize_agent import optimize_seo
        content = "인공지능은 미래 기술입니다. " * 20
        result = optimize_seo(content, keywords=["인공지능"])
        self.assertIn("인공지능", result['keyword_density'])
        self.assertGreater(result['keyword_density']['인공지능']['count'], 0)

    def test_missing_keyword_warning(self):
        """키워드가 본문에 없을 때 경고"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("이것은 테스트 글입니다.", keywords=["블록체인"])
        self.assertTrue(any('블록체인' in s for s in result['suggestions']))

    def test_no_h2_suggestion(self):
        """H2 없으면 추가 제안"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("헤딩 없는 긴 글입니다. " * 50)
        self.assertTrue(any('H2' in s for s in result['suggestions']))

    def test_score_range(self):
        """점수 0-100 범위"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("## 제목\n\n" + "좋은 콘텐츠입니다. " * 100)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_meta_length(self):
        """글자수/단어수 통계"""
        from services.agents.seo_optimize_agent import optimize_seo
        result = optimize_seo("테스트 콘텐츠")
        self.assertGreater(result['meta_length']['char_count'], 0)
        self.assertGreater(result['meta_length']['word_count'], 0)


if __name__ == '__main__':
    unittest.main()
