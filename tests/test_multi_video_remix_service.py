"""multi_video_remix_service 단위 테스트"""
import unittest

from services.multi_video_remix_service import (
    remix_videos,
    RemixPlan,
    RemixClip,
    _parse_timestamp,
    _format_timestamp,
    _validate_source,
    _calculate_clip_duration,
    _assign_transitions,
)


class TestRemixVideos(unittest.TestCase):
    """remix_videos 함수 테스트"""

    def test_empty_sources(self):
        """빈 소스 — 빈 계획"""
        result = remix_videos([])
        self.assertEqual(result.clips, [])
        self.assertEqual(result.total_duration, 0.0)

    def test_empty_sources_with_theme(self):
        """빈 소스 + 테마"""
        result = remix_videos([], theme='해변')
        self.assertEqual(result.theme, '해변')
        self.assertEqual(result.clips, [])

    def test_single_source(self):
        """단일 소스"""
        sources = [{'source_id': 'v1', 'start': '0:00', 'end': '1:30'}]
        result = remix_videos(sources, theme='테스트')
        self.assertEqual(len(result.clips), 1)
        self.assertEqual(result.clips[0].source_id, 'v1')
        self.assertEqual(result.clips[0].order, 0)

    def test_multiple_sources(self):
        """여러 소스"""
        sources = [
            {'source_id': 'v1', 'start': '0:00', 'end': '0:30'},
            {'source_id': 'v2', 'start': '1:00', 'end': '2:00'},
            {'source_id': 'v3', 'start': '0:10', 'end': '0:40'},
        ]
        result = remix_videos(sources, theme='모음집')
        self.assertEqual(len(result.clips), 3)
        # 순서 확인
        for i, clip in enumerate(result.clips):
            self.assertEqual(clip.order, i)

    def test_total_duration_calculation(self):
        """총 시간 계산"""
        sources = [
            {'source_id': 'v1', 'start': '0:00', 'end': '0:30'},  # 30초
            {'source_id': 'v2', 'start': '0:00', 'end': '1:00'},  # 60초
        ]
        result = remix_videos(sources)
        self.assertEqual(result.total_duration, 90.0)

    def test_transitions_generated(self):
        """전환 효과 생성"""
        sources = [
            {'source_id': 'v1', 'start': '0:00', 'end': '0:30'},
            {'source_id': 'v2', 'start': '0:00', 'end': '0:30'},
            {'source_id': 'v3', 'start': '0:00', 'end': '0:30'},
        ]
        result = remix_videos(sources)
        self.assertEqual(len(result.transitions), 2)  # 클립 수 - 1

    def test_invalid_source_raises(self):
        """유효하지 않은 소스 → ValueError"""
        sources = [{'source_id': 'v1'}]  # start, end 없음
        with self.assertRaises(ValueError):
            remix_videos(sources)

    def test_start_after_end_raises(self):
        """시작 > 끝 → ValueError"""
        sources = [{'source_id': 'v1', 'start': '2:00', 'end': '1:00'}]
        with self.assertRaises(ValueError):
            remix_videos(sources)

    def test_default_theme(self):
        """테마 미지정 시 기본값"""
        result = remix_videos([{'source_id': 'v1', 'start': '0:00', 'end': '0:10'}])
        self.assertEqual(result.theme, '(테마 미지정)')

    def test_result_is_dataclass(self):
        """반환 타입 확인"""
        result = remix_videos([{'source_id': 'v1', 'start': '0:00', 'end': '0:10'}])
        self.assertIsInstance(result, RemixPlan)
        self.assertIsInstance(result.clips[0], RemixClip)

    def test_hhmmss_format(self):
        """HH:MM:SS 타임스탬프 지원"""
        sources = [{'source_id': 'v1', 'start': '1:00:00', 'end': '1:01:00'}]
        result = remix_videos(sources)
        self.assertEqual(result.total_duration, 60.0)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_parse_timestamp_mmss(self):
        """MM:SS 파싱"""
        self.assertEqual(_parse_timestamp('1:30'), 90.0)

    def test_parse_timestamp_hhmmss(self):
        """HH:MM:SS 파싱"""
        self.assertEqual(_parse_timestamp('1:00:00'), 3600.0)

    def test_format_timestamp(self):
        """초 → MM:SS"""
        self.assertEqual(_format_timestamp(90), '1:30')
        self.assertEqual(_format_timestamp(0), '0:00')

    def test_validate_source_valid(self):
        """유효한 소스"""
        self.assertTrue(_validate_source({'source_id': 'v1', 'start': '0:00', 'end': '0:30'}))

    def test_validate_source_missing_fields(self):
        """필드 누락"""
        self.assertFalse(_validate_source({'source_id': 'v1'}))
        self.assertFalse(_validate_source({}))

    def test_validate_source_not_dict(self):
        """dict가 아닌 입력"""
        self.assertFalse(_validate_source('invalid'))

    def test_calculate_clip_duration(self):
        """클립 길이 계산"""
        self.assertEqual(_calculate_clip_duration('0:00', '1:30'), 90.0)

    def test_assign_transitions(self):
        """전환 배정 — 클립 수 - 1"""
        result = _assign_transitions(4)
        self.assertEqual(len(result), 3)

    def test_assign_transitions_single(self):
        """단일 클립 — 전환 없음"""
        self.assertEqual(_assign_transitions(1), [])


if __name__ == '__main__':
    unittest.main()
