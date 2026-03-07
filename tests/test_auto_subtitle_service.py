"""auto_subtitle_service 단위 테스트 (내부 함수 위주)"""
import unittest

from services.auto_subtitle_service import (
    _format_vtt, _format_srt,
    _seconds_to_vtt_time, _seconds_to_srt_time,
    AutoSubtitleService,
)


class TestSecondsToVttTime(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(_seconds_to_vtt_time(0), '00:00:00.000')

    def test_minutes(self):
        self.assertEqual(_seconds_to_vtt_time(65.5), '00:01:05.500')

    def test_hours(self):
        self.assertEqual(_seconds_to_vtt_time(3661.0), '01:01:01.000')


class TestSecondsToSrtTime(unittest.TestCase):

    def test_zero(self):
        self.assertEqual(_seconds_to_srt_time(0), '00:00:00,000')

    def test_milliseconds(self):
        result = _seconds_to_srt_time(1.234)
        self.assertEqual(result, '00:00:01,234')


class TestFormatVtt(unittest.TestCase):

    def test_basic(self):
        """VTT 포맷 변환"""
        entries = [{'start': 0, 'end': 5, 'text': '안녕하세요'}]
        result = _format_vtt(entries)
        self.assertIn('WEBVTT', result)
        self.assertIn('안녕하세요', result)
        self.assertIn('-->', result)

    def test_multiple_entries(self):
        """여러 항목 VTT"""
        entries = [
            {'start': 0, 'end': 3, 'text': '첫 번째'},
            {'start': 3, 'end': 6, 'text': '두 번째'},
        ]
        result = _format_vtt(entries)
        self.assertIn('첫 번째', result)
        self.assertIn('두 번째', result)


class TestFormatSrt(unittest.TestCase):

    def test_basic(self):
        """SRT 포맷 변환"""
        entries = [{'start': 0, 'end': 5, 'text': 'Hello'}]
        result = _format_srt(entries)
        self.assertIn('Hello', result)
        self.assertIn(',', result)  # SRT는 밀리초 구분자가 콤마


class TestAutoSubtitleServiceInternal(unittest.TestCase):

    def setUp(self):
        self.svc = AutoSubtitleService()

    def test_parse_to_segments_with_timestamps(self):
        """[MM:SS] 타임스탬프 자막 파싱"""
        transcript = '[00:00] 안녕하세요 [01:30] 두 번째 문장입니다'
        segments = self.svc._parse_to_segments(transcript)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]['start'], 0)
        self.assertEqual(segments[1]['start'], 90)

    def test_parse_to_segments_no_timestamps(self):
        """타임스탬프 없는 자막 → 균등 분할"""
        transcript = '첫 문장입니다. 두 번째 문장입니다. 세 번째입니다.'
        segments = self.svc._parse_to_segments(transcript)
        self.assertGreater(len(segments), 0)
        self.assertEqual(segments[0]['start'], 0)

    def test_parse_with_copy_timing(self):
        """타이밍 복사"""
        transcript = '번역된 첫 문장입니다. 번역된 두 번째입니다.'
        timing = [
            {'start': 10, 'end': 15},
            {'start': 15, 'end': 20},
        ]
        segments = self.svc._parse_to_segments(transcript, copy_timing=timing)
        self.assertEqual(segments[0]['start'], 10)

    def test_format_output_vtt(self):
        """VTT 출력 포맷"""
        segments = [{'start': 0, 'end': 5, 'text': '테스트'}]
        result = self.svc._format_output(segments, 'vtt')
        self.assertIn('WEBVTT', result)

    def test_format_output_srt(self):
        """SRT 출력 포맷"""
        segments = [{'start': 0, 'end': 5, 'text': '테스트'}]
        result = self.svc._format_output(segments, 'srt')
        self.assertIn(',', result)

    def test_format_output_text(self):
        """텍스트 출력 포맷"""
        segments = [
            {'start': 0, 'end': 3, 'text': '라인1'},
            {'start': 3, 'end': 6, 'text': '라인2'},
        ]
        result = self.svc._format_output(segments, 'text')
        self.assertEqual(result, '라인1\n라인2')


if __name__ == '__main__':
    unittest.main()
