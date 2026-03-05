"""
적응형 프롬프트 최적화 서비스 단위 테스트 (F3-06)
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch


class TestPromptOptimizer(unittest.TestCase):
    """prompt_optimizer_service 테스트"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch(
            'services.prompt_optimizer_service._FEEDBACK_DIR',
            new=__import__('pathlib').Path(self.test_dir),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_feedback_like(self):
        """좋아요 피드백 저장"""
        from services.prompt_optimizer_service import save_feedback
        result = save_feedback('blog_seo', 'content_001', 'like')
        self.assertTrue(result['ok'])
        self.assertIn('feedback_id', result)

    def test_save_feedback_dislike_with_comment(self):
        """싫어요 피드백 + 코멘트 저장"""
        from services.prompt_optimizer_service import save_feedback
        result = save_feedback('blog_seo', 'content_002', 'dislike', comment='구성이 아쉬움')
        self.assertTrue(result['ok'])

    def test_save_feedback_invalid_rating(self):
        """유효하지 않은 rating 시 ValueError"""
        from services.prompt_optimizer_service import save_feedback
        with self.assertRaises(ValueError):
            save_feedback('blog_seo', 'content_003', 'meh')

    def test_get_feedback_stats_empty(self):
        """피드백 없을 때 빈 통계"""
        from services.prompt_optimizer_service import get_feedback_stats
        stats = get_feedback_stats('nonexistent_style')
        self.assertEqual(stats['total'], 0)
        self.assertEqual(stats['like_ratio'], 0.0)

    def test_get_feedback_stats_counts(self):
        """피드백 저장 후 통계 확인"""
        from services.prompt_optimizer_service import save_feedback, get_feedback_stats

        save_feedback('summary', 'c1', 'like')
        save_feedback('summary', 'c2', 'like')
        save_feedback('summary', 'c3', 'dislike')

        stats = get_feedback_stats('summary')
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['likes'], 2)
        self.assertEqual(stats['dislikes'], 1)
        self.assertAlmostEqual(stats['like_ratio'], 0.667, places=2)

    def test_optimize_not_enough_feedback(self):
        """피드백 부족 시 최적화 불가 메시지"""
        from services.prompt_optimizer_service import optimize_prompt
        result = optimize_prompt('tutorial')
        self.assertIsNone(result['adjusted_temperature'])
        self.assertTrue(any('최소' in s for s in result['suggestions']))

    def test_optimize_with_low_satisfaction(self):
        """만족도 낮을 때 temperature 조정 제안"""
        from services.prompt_optimizer_service import save_feedback, optimize_prompt

        # 6개 피드백 (1 like, 5 dislike → 만족도 16.7%)
        save_feedback('qna', 'c1', 'like')
        for i in range(5):
            save_feedback('qna', f'c{i+2}', 'dislike')

        result = optimize_prompt('qna')
        self.assertEqual(result['adjusted_temperature'], -0.1)
        self.assertTrue(any('낮' in s for s in result['suggestions']))


class TestFeedbackStatsIsolation(unittest.TestCase):
    """스타일별 피드백 파일 격리 확인"""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch(
            'services.prompt_optimizer_service._FEEDBACK_DIR',
            new=__import__('pathlib').Path(self.test_dir),
        )
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_styles_isolated(self):
        """서로 다른 스타일의 피드백이 혼합되지 않음"""
        from services.prompt_optimizer_service import save_feedback, get_feedback_stats

        save_feedback('blog_seo', 'c1', 'like')
        save_feedback('summary', 'c2', 'dislike')

        blog_stats = get_feedback_stats('blog_seo')
        summary_stats = get_feedback_stats('summary')

        self.assertEqual(blog_stats['likes'], 1)
        self.assertEqual(blog_stats['dislikes'], 0)
        self.assertEqual(summary_stats['likes'], 0)
        self.assertEqual(summary_stats['dislikes'], 1)


if __name__ == '__main__':
    unittest.main()
