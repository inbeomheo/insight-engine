"""bgm_stem_service 단위 테스트"""
import unittest

from services.bgm_stem_service import (
    suggest_bgm,
    BGMSuggestion,
    SUPPORTED_MOODS,
    _detect_mood,
    _split_segments,
    _format_timestamp,
)


class TestSuggestBgm(unittest.TestCase):
    """suggest_bgm 함수 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 — 빈 리스트"""
        result = suggest_bgm('')
        self.assertEqual(result, [])

    def test_whitespace_only(self):
        """공백만 — 빈 리스트"""
        result = suggest_bgm('   ')
        self.assertEqual(result, [])

    def test_unsupported_mood(self):
        """지원하지 않는 분위기 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            suggest_bgm('content', mood='angry')
        self.assertIn('angry', str(ctx.exception))

    def test_basic_suggestion(self):
        """기본 콘텐츠 — BGM 추천 반환"""
        content = '오늘은 좋은 날입니다.\n\n재미있는 이야기를 해봅시다.'
        result = suggest_bgm(content)
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], BGMSuggestion)

    def test_upbeat_mood(self):
        """upbeat 분위기 명시"""
        result = suggest_bgm('내용입니다.', mood='upbeat')
        for item in result:
            self.assertEqual(item.mood, 'upbeat')

    def test_calm_mood(self):
        """calm 분위기 명시"""
        result = suggest_bgm('내용입니다.', mood='calm')
        for item in result:
            self.assertEqual(item.mood, 'calm')

    def test_dramatic_mood(self):
        """dramatic 분위기 명시"""
        result = suggest_bgm('내용입니다.', mood='dramatic')
        for item in result:
            self.assertEqual(item.mood, 'dramatic')

    def test_melancholic_mood(self):
        """melancholic 분위기 명시"""
        result = suggest_bgm('내용입니다.', mood='melancholic')
        for item in result:
            self.assertEqual(item.mood, 'melancholic')

    def test_neutral_auto_detect(self):
        """neutral 시 자동 감지"""
        content = '정말 신나고 재미있는 내용입니다!'
        result = suggest_bgm(content, mood='neutral')
        # 자동 감지로 upbeat이 선택될 수 있음
        self.assertGreater(len(result), 0)

    def test_suggestion_fields(self):
        """BGMSuggestion 필드 완전성"""
        result = suggest_bgm('콘텐츠입니다.', mood='calm')
        for item in result:
            self.assertTrue(item.track_name)
            self.assertTrue(item.genre)
            self.assertTrue(item.mood)
            self.assertGreater(item.bpm, 0)
            self.assertGreaterEqual(item.energy_level, 0.0)
            self.assertLessEqual(item.energy_level, 1.0)
            self.assertIn('-', item.timestamp_range)

    def test_multiple_segments(self):
        """여러 세그먼트 → 여러 추천"""
        content = '문단1.\n\n문단2.\n\n문단3.'
        result = suggest_bgm(content, mood='upbeat')
        self.assertGreaterEqual(len(result), 2)

    def test_timestamp_format(self):
        """타임스탬프 형식 확인"""
        result = suggest_bgm('내용.', mood='neutral')
        for item in result:
            parts = item.timestamp_range.split('-')
            self.assertEqual(len(parts), 2)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_detect_mood_upbeat(self):
        """upbeat 키워드 감지"""
        self.assertEqual(_detect_mood('신나는 재미있는 하루'), 'upbeat')

    def test_detect_mood_calm(self):
        """calm 키워드 감지"""
        self.assertEqual(_detect_mood('평화롭고 조용한 시간'), 'calm')

    def test_detect_mood_no_match(self):
        """매칭 없으면 neutral"""
        self.assertEqual(_detect_mood('일반적인 내용'), 'neutral')

    def test_split_segments(self):
        """문단 분리"""
        result = _split_segments('A\n\nB\n\nC')
        self.assertEqual(len(result), 3)

    def test_format_timestamp(self):
        """초 → MM:SS 변환"""
        self.assertEqual(_format_timestamp(0, 90), '0:00-1:30')
        self.assertEqual(_format_timestamp(60, 120), '1:00-2:00')


if __name__ == '__main__':
    unittest.main()
