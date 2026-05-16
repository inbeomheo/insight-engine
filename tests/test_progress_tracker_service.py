"""progress_tracker_service 단위 테스트"""
import unittest

from services.content.progress_tracker_service import (
    track_progress,
)


class TestTrackProgress(unittest.TestCase):

    def test_empty_content(self):
        result = track_progress('')
        self.assertEqual(result['overall_progress'], 0.0)
        self.assertEqual(result['status'], 'just_started')

    def test_none_content(self):
        result = track_progress(None)
        self.assertEqual(result['overall_progress'], 0.0)

    def test_partial_progress(self):
        content = '# 제목\n\n첫 번째 문단입니다. ' * 10
        result = track_progress(content, goals={'word_count': 500, 'section_count': 5})
        self.assertGreater(result['overall_progress'], 0.0)
        self.assertLess(result['overall_progress'], 1.0)

    def test_complete_progress(self):
        content = '# 제목\n## A\n## B\n## C\n## D\n## E\n' + '단어 ' * 1000
        result = track_progress(content, goals={'word_count': 100, 'section_count': 3})
        self.assertGreaterEqual(result['overall_progress'], 0.9)

    def test_word_metrics(self):
        content = '단어 ' * 50
        result = track_progress(content, goals={'word_count': 100})
        self.assertEqual(result['metrics']['words']['current'], 50)
        self.assertEqual(result['metrics']['words']['goal'], 100)
        self.assertAlmostEqual(result['metrics']['words']['progress'], 0.5)

    def test_section_metrics(self):
        content = '# A\n## B\n## C\n내용'
        result = track_progress(content, goals={'section_count': 6})
        self.assertEqual(result['metrics']['sections']['current'], 3)

    def test_image_metrics(self):
        content = '![img1](a.png)\n![img2](b.png)\n텍스트'
        result = track_progress(content, goals={'image_count': 5})
        self.assertEqual(result['metrics']['images']['current'], 2)
        self.assertAlmostEqual(result['metrics']['images']['progress'], 0.4)

    def test_checklist_progress(self):
        content = '- [x] 완료1\n- [x] 완료2\n- [ ] 미완료1\n- [ ] 미완료2'
        result = track_progress(content)
        checklist = result['metrics']['checklist']
        self.assertEqual(checklist['done'], 2)
        self.assertEqual(checklist['total'], 4)
        self.assertAlmostEqual(checklist['progress'], 0.5)

    def test_status_values(self):
        valid = {'just_started', 'in_progress', 'almost_done', 'complete'}
        content = '일부 내용입니다.'
        result = track_progress(content)
        self.assertIn(result['status'], valid)

    def test_suggestions_generated(self):
        content = '짧은 글'
        result = track_progress(content, goals={'word_count': 1000, 'section_count': 10})
        self.assertGreater(len(result['suggestions']), 0)

    def test_default_goals(self):
        content = '단어 ' * 500
        result = track_progress(content)
        # 기본 목표: word_count=1000, section_count=5
        self.assertEqual(result['metrics']['words']['goal'], 1000)
        self.assertEqual(result['metrics']['sections']['goal'], 5)

    def test_zero_goal_is_full(self):
        content = '텍스트'
        result = track_progress(content, goals={'image_count': 0})
        # 목표 0이면 달성 완료
        self.assertEqual(result['metrics']['images']['progress'], 1.0)

    def test_progress_capped_at_one(self):
        content = '단어 ' * 2000
        result = track_progress(content, goals={'word_count': 100})
        self.assertLessEqual(result['metrics']['words']['progress'], 1.0)
        self.assertLessEqual(result['overall_progress'], 1.0)


if __name__ == '__main__':
    unittest.main()
