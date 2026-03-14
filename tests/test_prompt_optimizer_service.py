"""prompt_optimizer_service 단위 테스트"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from services.data import prompt_optimizer_service


class TestPromptOptimizerService(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self._orig = prompt_optimizer_service._FEEDBACK_DIR
        prompt_optimizer_service._FEEDBACK_DIR = type(self._orig)(self.tmpdir)

    def tearDown(self):
        prompt_optimizer_service._FEEDBACK_DIR = self._orig
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_feedback(self):
        """피드백 저장"""
        result = prompt_optimizer_service.save_feedback('blog_seo', 'c1', 'like')
        self.assertTrue(result['ok'])

    def test_invalid_rating_raises(self):
        """잘못된 rating"""
        with self.assertRaises(ValueError):
            prompt_optimizer_service.save_feedback('blog_seo', 'c1', 'bad')

    def test_get_stats_empty(self):
        """피드백 없을 때 통계"""
        stats = prompt_optimizer_service.get_feedback_stats('empty_style')
        self.assertEqual(stats['total'], 0)

    def test_get_stats_with_data(self):
        """피드백 있을 때 통계"""
        prompt_optimizer_service.save_feedback('blog_seo', 'c1', 'like')
        prompt_optimizer_service.save_feedback('blog_seo', 'c2', 'like')
        prompt_optimizer_service.save_feedback('blog_seo', 'c3', 'dislike')
        stats = prompt_optimizer_service.get_feedback_stats('blog_seo')
        self.assertEqual(stats['total'], 3)
        self.assertEqual(stats['likes'], 2)
        self.assertEqual(stats['dislikes'], 1)

    def test_optimize_insufficient(self):
        """피드백 부족 시 최적화"""
        prompt_optimizer_service.save_feedback('test', 'c1', 'like')
        result = prompt_optimizer_service.optimize_prompt('test')
        self.assertIsNone(result['adjusted_temperature'])
        self.assertTrue(any('최소' in s for s in result['suggestions']))

    def test_optimize_low_satisfaction(self):
        """낮은 만족도 시 temperature 조정"""
        for i in range(6):
            prompt_optimizer_service.save_feedback('low', f'c{i}', 'dislike')
        prompt_optimizer_service.save_feedback('low', 'c6', 'like')
        result = prompt_optimizer_service.optimize_prompt('low')
        self.assertEqual(result['adjusted_temperature'], -0.1)

    def test_optimize_high_satisfaction(self):
        """높은 만족도"""
        for i in range(6):
            prompt_optimizer_service.save_feedback('high', f'c{i}', 'like')
        result = prompt_optimizer_service.optimize_prompt('high')
        self.assertIsNone(result['adjusted_temperature'])


if __name__ == '__main__':
    unittest.main()
