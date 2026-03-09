"""signage_loop_service 단위 테스트"""
import unittest

from services.signage_loop_service import (
    create_signage_loop,
    SignageLoop,
    SignageSlide,
    _generate_loop_id,
    _split_into_slide_texts,
    _assign_slide_durations,
)


class TestCreateSignageLoop(unittest.TestCase):
    """create_signage_loop 함수 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 — 빈 루프"""
        result = create_signage_loop('')
        self.assertEqual(result.slides, [])
        self.assertEqual(result.total_duration, 0)
        self.assertEqual(result.loop_count, 0)

    def test_whitespace_only(self):
        """공백만 — 빈 루프"""
        result = create_signage_loop('   \n\n  ')
        self.assertEqual(result.slides, [])

    def test_invalid_duration(self):
        """0 이하 duration → ValueError"""
        with self.assertRaises(ValueError):
            create_signage_loop('content', duration_seconds=0)
        with self.assertRaises(ValueError):
            create_signage_loop('content', duration_seconds=-10)

    def test_basic_content(self):
        """기본 콘텐츠 → 슬라이드 생성"""
        content = '첫 번째 슬라이드 내용입니다.\n\n두 번째 슬라이드 내용입니다.'
        result = create_signage_loop(content, duration_seconds=30)
        self.assertGreater(len(result.slides), 0)
        self.assertIsInstance(result, SignageLoop)

    def test_slide_has_all_fields(self):
        """슬라이드 필드 완전성"""
        result = create_signage_loop('내용입니다.', duration_seconds=10)
        for slide in result.slides:
            self.assertIsInstance(slide, SignageSlide)
            self.assertTrue(slide.text)
            self.assertGreater(slide.duration_seconds, 0)
            self.assertTrue(slide.transition)
            self.assertTrue(slide.background_color.startswith('#'))

    def test_total_duration_matches_slides(self):
        """총 시간 = 슬라이드 시간 합"""
        result = create_signage_loop('A.\n\nB.\n\nC.', duration_seconds=30)
        expected = sum(s.duration_seconds for s in result.slides)
        self.assertEqual(result.total_duration, expected)

    def test_loop_id_generated(self):
        """루프 ID 생성"""
        result = create_signage_loop('내용', duration_seconds=30)
        self.assertTrue(result.loop_id)
        self.assertEqual(len(result.loop_id), 12)

    def test_loop_id_deterministic(self):
        """같은 입력 → 같은 ID"""
        r1 = create_signage_loop('동일 내용', duration_seconds=30)
        r2 = create_signage_loop('동일 내용', duration_seconds=30)
        self.assertEqual(r1.loop_id, r2.loop_id)

    def test_different_content_different_id(self):
        """다른 입력 → 다른 ID"""
        r1 = create_signage_loop('내용A', duration_seconds=30)
        r2 = create_signage_loop('내용B', duration_seconds=30)
        self.assertNotEqual(r1.loop_id, r2.loop_id)

    def test_loop_count_positive(self):
        """루프 횟수 ≥ 1"""
        result = create_signage_loop('내용', duration_seconds=60)
        self.assertGreaterEqual(result.loop_count, 1)

    def test_long_paragraph_split(self):
        """긴 문단 → 문장 단위 분할"""
        # 120자 초과하는 긴 문단
        long_text = '이것은 매우 긴 문장입니다. ' * 15
        result = create_signage_loop(long_text, duration_seconds=60)
        # 여러 슬라이드로 분할되어야 함
        self.assertGreater(len(result.slides), 1)

    def test_transitions_cycle(self):
        """전환 효과가 순환"""
        content = '\n\n'.join([f'슬라이드 {i}.' for i in range(10)])
        result = create_signage_loop(content, duration_seconds=60)
        transitions = [s.transition for s in result.slides]
        self.assertGreater(len(set(transitions)), 1)

    def test_background_colors_cycle(self):
        """배경색이 순환"""
        content = '\n\n'.join([f'슬라이드 {i}.' for i in range(10)])
        result = create_signage_loop(content, duration_seconds=60)
        colors = [s.background_color for s in result.slides]
        self.assertGreater(len(set(colors)), 1)

    def test_markdown_heading_removed(self):
        """마크다운 헤딩 제거"""
        content = '# 제목\n\n본문입니다.'
        result = create_signage_loop(content, duration_seconds=10)
        for slide in result.slides:
            self.assertFalse(slide.text.startswith('#'))


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_generate_loop_id_length(self):
        """ID 길이 12"""
        loop_id = _generate_loop_id('test', 30)
        self.assertEqual(len(loop_id), 12)

    def test_split_into_slide_texts(self):
        """문단 분리"""
        texts = _split_into_slide_texts('A.\n\nB.\n\nC.')
        self.assertEqual(len(texts), 3)

    def test_split_removes_empty(self):
        """빈 문단 제거"""
        texts = _split_into_slide_texts('A.\n\n\n\nB.')
        self.assertEqual(len(texts), 2)

    def test_assign_slide_durations_total(self):
        """배분 총합 ≈ 목표 시간"""
        durations = _assign_slide_durations(3, 30)
        self.assertEqual(len(durations), 3)
        self.assertEqual(sum(durations), 30)

    def test_assign_slide_durations_min(self):
        """최소 시간 보장"""
        durations = _assign_slide_durations(100, 10)
        for d in durations:
            self.assertGreaterEqual(d, 3)

    def test_assign_slide_durations_empty(self):
        """0개 슬라이드"""
        self.assertEqual(_assign_slide_durations(0, 30), [])


if __name__ == '__main__':
    unittest.main()
