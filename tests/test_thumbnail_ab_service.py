"""thumbnail_ab_service 단위 테스트"""
import unittest

from services.thumbnail_ab_service import (
    ThumbnailABService, ThumbnailVariant, ABTest
)


class TestThumbnailVariant(unittest.TestCase):

    def test_update_ctr(self):
        """CTR 계산"""
        v = ThumbnailVariant('v1', 'control', 'url', 'prompt')
        v.impressions = 100
        v.clicks = 5
        v.update_ctr()
        self.assertAlmostEqual(v.ctr, 0.05)

    def test_update_ctr_zero_impressions(self):
        """노출 0일 때 CTR → 0"""
        v = ThumbnailVariant('v1', 'control', 'url', 'prompt')
        v.update_ctr()
        self.assertEqual(v.ctr, 0.0)


class TestThumbnailABService(unittest.TestCase):

    def setUp(self):
        self.svc = ThumbnailABService(store_path='/dev/null')
        # 테스트용 A/B 테스트 수동 생성 (image_gen_service 의존 회피)
        v1 = ThumbnailVariant('t1_v0', 'control', 'url0', 'prompt0')
        v2 = ThumbnailVariant('t1_v1', 'variant_a', 'url1', 'prompt1')
        self.test = ABTest(
            test_id='t1', title='테스트', video_url='https://youtube.com/watch?v=abc',
            variants=[v1, v2], min_impressions=5,
        )
        self.svc._tests['t1'] = self.test

    def test_record_impression(self):
        """노출 기록"""
        self.assertTrue(self.svc.record_impression('t1', 't1_v0'))
        self.assertEqual(self.test.variants[0].impressions, 1)

    def test_record_impression_invalid_test(self):
        """없는 테스트 → False"""
        self.assertFalse(self.svc.record_impression('bad', 't1_v0'))

    def test_record_impression_invalid_variant(self):
        """없는 변형 → False"""
        self.assertFalse(self.svc.record_impression('t1', 'bad_variant'))

    def test_record_click(self):
        """클릭 기록"""
        self.assertTrue(self.svc.record_click('t1', 't1_v0'))
        self.assertEqual(self.test.variants[0].clicks, 1)

    def test_record_click_invalid(self):
        """없는 테스트에 클릭 → False"""
        self.assertFalse(self.svc.record_click('bad', 't1_v0'))

    def test_get_results(self):
        """결과 조회"""
        result = self.svc.get_results('t1')
        self.assertEqual(result['test_id'], 't1')
        self.assertEqual(len(result['variants']), 2)
        self.assertEqual(result['status'], 'running')

    def test_get_results_nonexistent(self):
        """없는 테스트 결과 → None"""
        self.assertIsNone(self.svc.get_results('bad'))

    def test_auto_winner_selection(self):
        """최소 노출 달성 시 승자 자동 선택"""
        # v0: 높은 CTR
        for _ in range(6):
            self.svc.record_impression('t1', 't1_v0')
            self.svc.record_click('t1', 't1_v0')
        # v1: 낮은 CTR
        for _ in range(6):
            self.svc.record_impression('t1', 't1_v1')

        self.assertEqual(self.test.status, 'completed')
        self.assertEqual(self.test.winner_id, 't1_v0')

    def test_no_winner_when_close(self):
        """CTR 차이 1% 미만이면 미결"""
        for _ in range(6):
            self.svc.record_impression('t1', 't1_v0')
            self.svc.record_impression('t1', 't1_v1')
        # 둘 다 클릭 0 → CTR 동일 → 미결
        self.assertEqual(self.test.status, 'running')

    def test_completed_test_no_impression(self):
        """완료된 테스트에는 노출 기록 불가"""
        self.test.status = 'completed'
        self.assertFalse(self.svc.record_impression('t1', 't1_v0'))

    def test_generate_variant_prompts(self):
        """변형 프롬프트 생성"""
        prompts = self.svc._generate_variant_prompts('제목', 3, 'youtube')
        self.assertEqual(len(prompts), 3)
        self.assertEqual(prompts[0][0], 'control')


if __name__ == '__main__':
    unittest.main()
