"""utils/timestamp_utils 단위 테스트 — YouTube 타임코드 변환 유틸 5개 함수"""
import unittest

from utils.timestamp_utils import (
    seconds_to_hhmmss,
    hhmmss_to_seconds,
    make_youtube_deeplink,
    format_segments_for_prompt,
    extract_timestamps_from_content,
)


class TestSecondsToHHMMSS(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(seconds_to_hhmmss(0), '00:00:00')

    def test_minute_boundary(self):
        self.assertEqual(seconds_to_hhmmss(59), '00:00:59')
        self.assertEqual(seconds_to_hhmmss(60), '00:01:00')
        self.assertEqual(seconds_to_hhmmss(125), '00:02:05')

    def test_hour_boundary(self):
        self.assertEqual(seconds_to_hhmmss(3599), '00:59:59')
        self.assertEqual(seconds_to_hhmmss(3600), '01:00:00')
        self.assertEqual(seconds_to_hhmmss(3725), '01:02:05')

    def test_negative_clamps_to_zero(self):
        self.assertEqual(seconds_to_hhmmss(-10), '00:00:00')

    def test_float_truncated(self):
        self.assertEqual(seconds_to_hhmmss(65.7), '00:01:05')


class TestHHMMSSToSeconds(unittest.TestCase):

    def test_full_format(self):
        self.assertEqual(hhmmss_to_seconds('00:02:05'), 125)
        self.assertEqual(hhmmss_to_seconds('01:00:00'), 3600)
        self.assertEqual(hhmmss_to_seconds('01:02:05'), 3725)

    def test_short_format(self):
        """MM:SS 형식도 지원"""
        self.assertEqual(hhmmss_to_seconds('2:05'), 125)
        self.assertEqual(hhmmss_to_seconds('0:30'), 30)

    def test_whitespace_trimmed(self):
        self.assertEqual(hhmmss_to_seconds('  01:00:00  '), 3600)

    def test_invalid_returns_zero(self):
        for bad in ('', 'abc', '1', '1:2:3:4', 'aa:bb:cc'):
            with self.subTest(bad=bad):
                self.assertEqual(hhmmss_to_seconds(bad), 0)

    def test_roundtrip(self):
        for sec in (0, 30, 60, 125, 3600, 7322):
            self.assertEqual(hhmmss_to_seconds(seconds_to_hhmmss(sec)), sec)


class TestMakeYoutubeDeeplink(unittest.TestCase):

    def test_basic_url_adds_t_param(self):
        url = 'https://youtu.be/abc'
        self.assertEqual(make_youtube_deeplink(url, 125), 'https://youtu.be/abc?t=125')

    def test_url_with_query_appends_with_ampersand(self):
        url = 'https://www.youtube.com/watch?v=abc'
        self.assertEqual(
            make_youtube_deeplink(url, 60),
            'https://www.youtube.com/watch?v=abc&t=60'
        )

    def test_existing_t_param_replaced(self):
        url = 'https://www.youtube.com/watch?v=abc&t=10'
        result = make_youtube_deeplink(url, 99)
        # 기존 t= 제거 후 새 t= 추가
        self.assertIn('t=99', result)
        self.assertNotIn('t=10', result)

    def test_empty_url_passes_through(self):
        self.assertEqual(make_youtube_deeplink('', 60), '')


class TestFormatSegmentsForPrompt(unittest.TestCase):

    def test_basic(self):
        segments = [
            {'start': 0, 'text': '안녕하세요'},
            {'start': 60, 'text': '둘째 줄'},
        ]
        result = format_segments_for_prompt(segments)
        self.assertIn('[00:00:00] 안녕하세요', result)
        self.assertIn('[00:01:00] 둘째 줄', result)

    def test_empty_list(self):
        self.assertEqual(format_segments_for_prompt([]), '')

    def test_filters_empty_text(self):
        segments = [
            {'start': 0, 'text': ''},
            {'start': 10, 'text': '   '},
            {'start': 20, 'text': '유효'},
        ]
        result = format_segments_for_prompt(segments)
        self.assertEqual(result.count('\n'), 0)
        self.assertIn('유효', result)

    def test_sampling_when_too_many(self):
        """max_segments 초과 시 균등 샘플링"""
        segments = [{'start': i, 'text': f't{i}'} for i in range(100)]
        result = format_segments_for_prompt(segments, max_segments=10)
        lines = [line for line in result.split('\n') if line]
        self.assertEqual(len(lines), 10)


class TestExtractTimestampsFromContent(unittest.TestCase):

    def test_extracts_multiple(self):
        content = '인트로 [00:00:30] 본문 [01:23:45] 마무리'
        results = extract_timestamps_from_content(content)
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['hhmmss'], '00:00:30')
        self.assertEqual(results[0]['seconds'], 30)
        self.assertEqual(results[1]['hhmmss'], '01:23:45')
        self.assertEqual(results[1]['seconds'], 1 * 3600 + 23 * 60 + 45)

    def test_no_timestamps(self):
        self.assertEqual(extract_timestamps_from_content('일반 텍스트'), [])

    def test_records_position(self):
        content = '[00:00:10] 시작'
        results = extract_timestamps_from_content(content)
        self.assertEqual(results[0]['pos'], 0)

    def test_ignores_invalid_format(self):
        """타임스탬프 형식이 아닌 [...]는 무시"""
        content = '[note] 텍스트 [10] 다른 [00:30] 단축 [00:01:00] 유효'
        results = extract_timestamps_from_content(content)
        # 정확히 1개만 매칭
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['hhmmss'], '00:01:00')


if __name__ == '__main__':
    unittest.main()
