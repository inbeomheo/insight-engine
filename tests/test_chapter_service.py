"""chapter_service 단위 테스트"""
import unittest
from unittest.mock import Mock, patch

from services.transcript.chapter_service import split_chapters, _format_time, get_total_duration
from services.usage.usage_lock import UsageLockUnavailable


class TestFormatTime(unittest.TestCase):
    """_format_time 내부 함수 테스트"""

    def test_seconds_only(self):
        self.assertEqual(_format_time(45), '0:45')

    def test_minutes_and_seconds(self):
        self.assertEqual(_format_time(125), '2:05')

    def test_hours(self):
        self.assertEqual(_format_time(3661), '1:01:01')

    def test_zero(self):
        self.assertEqual(_format_time(0), '0:00')

    def test_exact_hour(self):
        self.assertEqual(_format_time(3600), '1:00:00')


class TestSplitChapters(unittest.TestCase):
    """split_chapters 함수 테스트"""

    def test_short_text_returns_empty(self):
        """500자 미만이면 빈 리스트"""
        result = split_chapters('짧은 텍스트', 'model1')
        self.assertEqual(result, [])

    @patch('services.transcript.chapter_service.ai_service')
    def test_success_with_json(self, mock_ai):
        """정상적인 JSON 응답 파싱"""
        mock_ai.create_content.return_value = {
            'content': '{"chapters": [{"title": "서론", "start": 0, "end": 120, "summary": "시작"}]}'
        }
        text = 'A' * 600
        result = split_chapters(text, 'model1')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], '서론')

    @patch('services.transcript.chapter_service.ai_service')
    def test_filters_invalid_chapters(self, mock_ai):
        """title/start/end 없는 챕터 필터링"""
        mock_ai.create_content.return_value = {
            'content': '{"chapters": [{"title": "유효", "start": 0, "end": 60}, {"noTitle": true}]}'
        }
        result = split_chapters('A' * 600, 'model1')
        self.assertEqual(len(result), 1)

    @patch('services.transcript.chapter_service.ai_service')
    def test_ai_error_returns_empty(self, mock_ai):
        """AI 호출 실패 시 빈 리스트"""
        mock_ai.create_content.side_effect = Exception('API error')
        result = split_chapters('A' * 600, 'model1')
        self.assertEqual(result, [])

    @patch('services.transcript.chapter_service.ai_service')
    def test_non_json_response(self, mock_ai):
        """JSON 아닌 응답 시 빈 리스트"""
        mock_ai.create_content.return_value = {'content': '챕터를 나눌 수 없습니다.'}
        result = split_chapters('A' * 600, 'model1')
        self.assertEqual(result, [])

    @patch('services.transcript.chapter_service.ai_service')
    def test_with_segments(self, mock_ai):
        """세그먼트 포함 시 타임스탬프 텍스트 구성"""
        mock_ai.create_content.return_value = {
            'content': '{"chapters": [{"title": "Ch1", "start": 0, "end": 60}]}'
        }
        segments = [
            {'start': 0, 'text': '안녕하세요 ' * 50},
            {'start': 60, 'text': '다음 주제 ' * 50},
        ]
        result = split_chapters('', 'model1', segments=segments)
        self.assertEqual(len(result), 1)
        # 프롬프트에 타임스탬프 형식 포함 확인
        call_args = mock_ai.create_content.call_args[0][0]
        self.assertIn('[0:00]', call_args)

    @patch('services.transcript.chapter_service.ai_service')
    def test_float_start_end_accepted(self, mock_ai):
        """start/end가 float여도 유효"""
        mock_ai.create_content.return_value = {
            'content': '{"chapters": [{"title": "Ch1", "start": 0.5, "end": 60.3, "summary": "ok"}]}'
        }
        result = split_chapters('A' * 600, 'model1')
        self.assertEqual(len(result), 1)

    @patch('services.transcript.chapter_service.ai_service')
    def test_cost_callback_is_deferred_to_the_actual_ai_boundary(self, mock_ai):
        callback = Mock()
        mock_ai.create_content.return_value = {'content': '{"chapters": []}'}

        split_chapters('A' * 600, 'model1', on_cost_start=callback)

        callback.assert_not_called()
        self.assertIs(
            mock_ai.create_content.call_args.kwargs['on_cost_start'],
            callback,
        )

    @patch('services.transcript.chapter_service.ai_service')
    def test_usage_lock_failure_is_not_a_graceful_empty_chapter_result(self, mock_ai):
        mock_ai.create_content.side_effect = UsageLockUnavailable('lease lost')

        with self.assertRaises(UsageLockUnavailable):
            split_chapters('A' * 600, 'model1', on_cost_start=Mock())


class TestGetTotalDuration(unittest.TestCase):
    """get_total_duration 함수 테스트"""

    def test_empty_segments(self):
        self.assertEqual(get_total_duration([]), 0)

    def test_single_segment(self):
        result = get_total_duration([{'start': 5, 'text': 'hello'}])
        self.assertEqual(result, 15)  # 5 + 10 여유

    def test_multiple_segments(self):
        segments = [
            {'start': 0, 'text': 'a'},
            {'start': 30, 'text': 'b'},
            {'start': 60, 'text': 'c'},
        ]
        result = get_total_duration(segments)
        # avg_gap = 60 / 2 = 30, total = 60 + 30 = 90
        self.assertEqual(result, 90)

    def test_no_valid_starts(self):
        result = get_total_duration([{'text': 'no start field'}])
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
