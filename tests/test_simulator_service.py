"""simulator_service 단위 테스트"""
import unittest

from services.simulator_service import SimulatorService, SimulationResult


class TestSimulatorService(unittest.TestCase):

    def setUp(self):
        self.svc = SimulatorService()
        self.sample_content = (
            '# 파이썬 프로그래밍\n'
            '파이썬은 배우기 쉬운 언어입니다.\n'
            '## 변수와 타입\n'
            '변수를 선언하고 타입을 지정할 수 있습니다.\n'
            '## 함수 정의\n'
            '함수를 정의하여 코드를 재사용할 수 있습니다.\n'
        ) * 10  # 충분한 길이

    def test_basic_simulation(self):
        """기본 시뮬레이션 실행"""
        result = self.svc.simulate(self.sample_content, seed=42)
        self.assertIsInstance(result, SimulationResult)
        self.assertGreater(result.predicted_views_30d, 0)
        self.assertGreater(result.predicted_ctr, 0)

    def test_seed_reproducibility(self):
        """동일 시드로 재현 가능"""
        r1 = self.svc.simulate(self.sample_content, seed=123)
        r2 = self.svc.simulate(self.sample_content, seed=123)
        self.assertEqual(r1.predicted_views_30d, r2.predicted_views_30d)
        self.assertEqual(r1.predicted_clicks_30d, r2.predicted_clicks_30d)

    def test_style_multiplier_effect(self):
        """스타일별 조회수 배율 차이"""
        r_sns = self.svc.simulate(self.sample_content, style_id='sns_post', seed=1)
        r_newsletter = self.svc.simulate(self.sample_content, style_id='newsletter', seed=1)
        # sns_post(3.0) > newsletter(0.8)
        self.assertGreater(r_sns.predicted_views_30d, r_newsletter.predicted_views_30d)

    def test_platform_base_views(self):
        """플랫폼별 기준 조회수 차이"""
        r_naver = self.svc.simulate(self.sample_content, platform='naver_blog', seed=10)
        r_substack = self.svc.simulate(self.sample_content, platform='substack', seed=10)
        # naver_blog(500) > substack(150)
        self.assertGreater(r_naver.predicted_views_30d, r_substack.predicted_views_30d)

    def test_seo_keywords_bottleneck(self):
        """SEO 키워드 없을 때 병목 포함"""
        result = self.svc.simulate(self.sample_content, has_seo_keywords=False, seed=1)
        self.assertTrue(any('SEO' in b for b in result.bottlenecks))

    def test_no_images_bottleneck(self):
        """이미지 없을 때 병목 포함"""
        result = self.svc.simulate(self.sample_content, has_images=False, seed=1)
        self.assertTrue(any('이미지' in b for b in result.bottlenecks))

    def test_short_content_bottleneck(self):
        """짧은 콘텐츠 병목"""
        result = self.svc.simulate('짧은 글입니다.', seed=1)
        self.assertTrue(any('짧음' in b for b in result.bottlenecks))

    def test_title_length_bottleneck(self):
        """제목 길이 비최적 병목"""
        result = self.svc.simulate(self.sample_content, title_length=10, seed=1)
        self.assertTrue(any('제목 길이' in b for b in result.bottlenecks))

    def test_to_dict(self):
        """to_dict 변환"""
        result = self.svc.simulate(self.sample_content, seed=42)
        d = result.to_dict()
        self.assertIn('predicted_views_30d', d)
        self.assertIn('predicted_ctr', d)
        self.assertIn('engagement_score', d)
        self.assertIn('seo_potential', d)
        self.assertIn('bottlenecks', d)
        self.assertIn('recommendations', d)

    def test_engagement_score_range(self):
        """참여도 점수 0~100 범위"""
        result = self.svc.simulate(self.sample_content, seed=42)
        self.assertGreaterEqual(result.engagement_score, 0)
        self.assertLessEqual(result.engagement_score, 100)

    def test_seo_potential_range(self):
        """SEO 잠재력 0~100 범위"""
        result = self.svc.simulate(self.sample_content, seed=42)
        self.assertGreaterEqual(result.seo_potential, 0)
        self.assertLessEqual(result.seo_potential, 100)


if __name__ == '__main__':
    unittest.main()
