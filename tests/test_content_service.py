"""content_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

import requests

from services.core.content_service import (
    SUPADATA_API_URL,
    PREFERRED_LANGUAGES,
    MAX_RETRY_ATTEMPTS,
    TIMEOUT_CONNECT,
    TIMEOUT_READ_SHORT,
    TIMEOUT_READ_LONG,
    HTTP_TIMEOUT,
    VIDEO_ID_PATTERN,
    _sanitize_video_id,
    _get_cache_path,
    is_youtube_url,
    get_video_id,
    _parse_vtt,
    _parse_timedtext_xml,
    _extract_caption_tracks,
    _pick_caption_track,
    _extract_text_from_transcript,
    _extract_segments_from_transcript,
    _detect_language_from_text,
    truncate_text,
    is_playlist_url,
    is_channel_url,
    _get_playlist_id,
    _get_channel_identifier,
    get_transcript_via_supadata,
)


class TestConstants(unittest.TestCase):

    def test_supadata_url(self):
        """Supadata API URL"""
        self.assertIn('supadata', SUPADATA_API_URL)

    def test_preferred_languages(self):
        """선호 언어 목록"""
        self.assertIn('ko', PREFERRED_LANGUAGES)
        self.assertIn('en', PREFERRED_LANGUAGES)

    def test_max_retry(self):
        """최대 재시도 횟수"""
        self.assertEqual(MAX_RETRY_ATTEMPTS, 3)

    def test_timeouts(self):
        """타임아웃 상수"""
        self.assertEqual(TIMEOUT_CONNECT, 5)
        self.assertEqual(TIMEOUT_READ_SHORT, 10)
        self.assertEqual(TIMEOUT_READ_LONG, 30)
        self.assertEqual(HTTP_TIMEOUT, (5, 30))


class TestSanitizeVideoId(unittest.TestCase):

    def test_valid_id(self):
        """유효한 video_id"""
        self.assertEqual(_sanitize_video_id('dQw4w9WgXcQ'), 'dQw4w9WgXcQ')

    def test_valid_id_with_dash_underscore(self):
        """하이픈/언더스코어 포함 ID"""
        self.assertEqual(_sanitize_video_id('abc-def_123'), 'abc-def_123')

    def test_empty(self):
        """빈 문자열 → ValueError"""
        with self.assertRaises(ValueError):
            _sanitize_video_id('')

    def test_none(self):
        """None → ValueError"""
        with self.assertRaises(ValueError):
            _sanitize_video_id(None)

    def test_too_short(self):
        """짧은 ID → ValueError"""
        with self.assertRaises(ValueError):
            _sanitize_video_id('abc')

    def test_path_traversal(self):
        """경로 탐색 시도 → ValueError"""
        with self.assertRaises(ValueError):
            _sanitize_video_id('../etc/passwd')


class TestGetCachePath(unittest.TestCase):

    def test_transcript_type(self):
        """transcript 타입 캐시 경로"""
        path = _get_cache_path('dQw4w9WgXcQ', 'transcript')
        self.assertIn('dQw4w9WgXcQ_transcript.json', path)

    def test_comments_type(self):
        """comments 타입 캐시 경로"""
        path = _get_cache_path('dQw4w9WgXcQ', 'comments')
        self.assertIn('dQw4w9WgXcQ_comments.json', path)

    def test_unknown_type(self):
        """알 수 없는 타입 → unknown으로 치환"""
        path = _get_cache_path('dQw4w9WgXcQ', 'malicious')
        self.assertIn('unknown', path)

    def test_invalid_video_id(self):
        """유효하지 않은 video_id → ValueError"""
        with self.assertRaises(ValueError):
            _get_cache_path('../../bad', 'transcript')


class TestIsYoutubeUrl(unittest.TestCase):

    def test_standard_url(self):
        """표준 YouTube URL"""
        self.assertTrue(is_youtube_url('https://www.youtube.com/watch?v=dQw4w9WgXcQ'))

    def test_short_url(self):
        """단축 URL"""
        self.assertTrue(is_youtube_url('https://youtu.be/dQw4w9WgXcQ'))

    def test_embed_url(self):
        """임베드 URL"""
        self.assertTrue(is_youtube_url('https://www.youtube.com/embed/dQw4w9WgXcQ'))

    def test_invalid_url(self):
        """유효하지 않은 URL"""
        self.assertFalse(is_youtube_url('https://example.com/video'))

    def test_empty(self):
        """빈 문자열"""
        self.assertFalse(is_youtube_url(''))


class TestGetVideoId(unittest.TestCase):

    def test_standard_url(self):
        """표준 URL에서 ID 추출"""
        self.assertEqual(get_video_id('https://www.youtube.com/watch?v=dQw4w9WgXcQ'), 'dQw4w9WgXcQ')

    def test_short_url(self):
        """단축 URL에서 ID 추출"""
        self.assertEqual(get_video_id('https://youtu.be/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')

    def test_embed_url(self):
        """임베드 URL에서 ID 추출"""
        self.assertEqual(get_video_id('https://www.youtube.com/embed/dQw4w9WgXcQ'), 'dQw4w9WgXcQ')

    def test_empty(self):
        """빈 문자열 → None"""
        self.assertIsNone(get_video_id(''))

    def test_none(self):
        """None → None"""
        self.assertIsNone(get_video_id(None))

    def test_no_match(self):
        """매칭 안 되는 URL"""
        self.assertIsNone(get_video_id('https://example.com'))


class TestParseVtt(unittest.TestCase):

    def test_basic_vtt(self):
        """기본 VTT 파싱"""
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n안녕하세요\n\n00:00:04.000 --> 00:00:06.000\n반갑습니다"
        result = _parse_vtt(vtt)
        self.assertIn('안녕하세요', result)
        self.assertIn('반갑습니다', result)

    def test_empty(self):
        """빈 입력 → 빈 문자열"""
        self.assertEqual(_parse_vtt(''), '')

    def test_none(self):
        """None → 빈 문자열"""
        self.assertEqual(_parse_vtt(None), '')

    def test_strips_html_tags(self):
        """HTML 태그 제거"""
        vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n<b>굵은</b> 텍스트"
        result = _parse_vtt(vtt)
        self.assertIn('굵은', result)
        self.assertNotIn('<b>', result)

    def test_skips_timestamp_lines(self):
        """타임스탬프 라인 제외"""
        vtt = "WEBVTT\n\n1\n00:00:01.000 --> 00:00:03.000\n텍스트"
        result = _parse_vtt(vtt)
        self.assertNotIn('-->', result)


class TestParseTimedtextXml(unittest.TestCase):

    def test_basic_xml(self):
        """기본 XML 파싱"""
        xml = '<transcript><text start="0" dur="3">안녕</text><text start="3" dur="2">세계</text></transcript>'
        result = _parse_timedtext_xml(xml)
        self.assertIn('안녕', result)
        self.assertIn('세계', result)

    def test_empty(self):
        """빈 입력 → 빈 문자열"""
        self.assertEqual(_parse_timedtext_xml(''), '')

    def test_invalid_xml(self):
        """잘못된 XML → 빈 문자열"""
        self.assertEqual(_parse_timedtext_xml('<invalid'), '')

    def test_html_unescape(self):
        """HTML 엔티티 디코딩"""
        xml = '<transcript><text start="0" dur="1">A &amp; B</text></transcript>'
        result = _parse_timedtext_xml(xml)
        self.assertIn('A & B', result)


class TestExtractCaptionTracks(unittest.TestCase):

    def test_valid_response(self):
        """유효한 플레이어 응답"""
        player = {
            'captions': {
                'playerCaptionsTracklistRenderer': {
                    'captionTracks': [
                        {'languageCode': 'ko', 'baseUrl': 'http://example.com'}
                    ]
                }
            }
        }
        tracks = _extract_caption_tracks(player)
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]['languageCode'], 'ko')

    def test_none_response(self):
        """None → 빈 리스트"""
        self.assertEqual(_extract_caption_tracks(None), [])

    def test_no_captions(self):
        """captions 없음 → 빈 리스트"""
        self.assertEqual(_extract_caption_tracks({}), [])


class TestPickCaptionTrack(unittest.TestCase):

    def test_prefer_korean(self):
        """한국어 우선 선택"""
        tracks = [
            {'languageCode': 'en', 'kind': ''},
            {'languageCode': 'ko', 'kind': ''},
        ]
        result = _pick_caption_track(tracks)
        self.assertEqual(result['languageCode'], 'ko')

    def test_prefer_manual_over_asr(self):
        """수동 자막 우선"""
        tracks = [
            {'languageCode': 'ko', 'kind': 'asr'},
            {'languageCode': 'ko', 'kind': ''},
        ]
        result = _pick_caption_track(tracks)
        self.assertNotEqual(result.get('kind'), 'asr')

    def test_empty_list(self):
        """빈 리스트 → None"""
        self.assertIsNone(_pick_caption_track([]))

    def test_none(self):
        """None → None"""
        self.assertIsNone(_pick_caption_track(None))


class TestExtractTextFromTranscript(unittest.TestCase):

    def test_dict_list(self):
        """딕셔너리 리스트"""
        fetched = [{'text': '안녕'}, {'text': '세계'}]
        result = _extract_text_from_transcript(fetched)
        self.assertEqual(result, '안녕 세계')

    def test_empty_list(self):
        """빈 리스트 → None"""
        self.assertIsNone(_extract_text_from_transcript([]))

    def test_none_text(self):
        """text가 None인 항목 무시"""
        fetched = [{'text': '유효'}, {'text': None}, {'text': '텍스트'}]
        result = _extract_text_from_transcript(fetched)
        self.assertEqual(result, '유효 텍스트')


class TestExtractSegmentsFromTranscript(unittest.TestCase):

    def test_dict_list(self):
        """딕셔너리 리스트에서 세그먼트 추출"""
        fetched = [
            {'start': 0.0, 'text': '시작', 'duration': 3.0},
            {'start': 3.0, 'text': '중간', 'duration': 2.0},
        ]
        result = _extract_segments_from_transcript(fetched)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['text'], '시작')
        self.assertAlmostEqual(result[0]['start'], 0.0)

    def test_empty_list(self):
        """빈 리스트 → 빈 리스트"""
        self.assertEqual(_extract_segments_from_transcript([]), [])

    def test_missing_start(self):
        """start 없는 항목 무시"""
        fetched = [{'text': '텍스트'}]
        self.assertEqual(_extract_segments_from_transcript(fetched), [])


class TestDetectLanguageFromText(unittest.TestCase):

    def test_korean(self):
        """한국어 감지"""
        self.assertEqual(_detect_language_from_text('안녕하세요 반갑습니다 테스트입니다'), 'ko')

    def test_english(self):
        """영어 감지"""
        self.assertEqual(_detect_language_from_text('Hello world this is a test'), 'en')

    def test_empty(self):
        """빈 문자열 → unknown"""
        self.assertEqual(_detect_language_from_text(''), 'unknown')


class TestTruncateText(unittest.TestCase):

    def test_no_truncation(self):
        """자르지 않음"""
        self.assertEqual(truncate_text('hello world', 10), 'hello world')

    def test_truncation(self):
        """토큰 수 초과 시 자르기"""
        result = truncate_text('a b c d e f', 3)
        self.assertEqual(result, 'a b c...')

    def test_non_string(self):
        """문자열이 아닌 입력 → 빈 문자열"""
        self.assertEqual(truncate_text(123, 10), '')

    def test_exact_limit(self):
        """정확히 제한과 같을 때"""
        self.assertEqual(truncate_text('a b c', 3), 'a b c')


class TestPlaylistChannelUrl(unittest.TestCase):

    def test_playlist_url(self):
        """재생목록 URL 감지"""
        self.assertTrue(is_playlist_url('https://www.youtube.com/playlist?list=PLxxxxxx'))

    def test_playlist_url_in_watch(self):
        """watch URL 내 재생목록"""
        self.assertTrue(is_playlist_url('https://www.youtube.com/watch?v=abc&list=PLxxxxxx'))

    def test_not_playlist(self):
        """일반 URL"""
        self.assertFalse(is_playlist_url('https://www.youtube.com/watch?v=abc'))

    def test_playlist_empty(self):
        """빈 문자열"""
        self.assertFalse(is_playlist_url(''))

    def test_channel_handle(self):
        """채널 @handle URL"""
        self.assertTrue(is_channel_url('https://www.youtube.com/@testchannel'))

    def test_channel_id(self):
        """채널 ID URL"""
        self.assertTrue(is_channel_url('https://www.youtube.com/channel/UCxxxxxxxx'))

    def test_channel_custom(self):
        """커스텀 채널 URL"""
        self.assertTrue(is_channel_url('https://www.youtube.com/c/CustomName'))

    def test_not_channel(self):
        """채널이 아닌 URL"""
        self.assertFalse(is_channel_url('https://www.youtube.com/watch?v=abc'))

    def test_channel_empty(self):
        """빈 문자열"""
        self.assertFalse(is_channel_url(''))


class TestGetPlaylistId(unittest.TestCase):

    def test_extract(self):
        """재생목록 ID 추출"""
        result = _get_playlist_id('https://www.youtube.com/playlist?list=PLabc123')
        self.assertEqual(result, 'PLabc123')

    def test_no_match(self):
        """매칭 없음 → None"""
        self.assertIsNone(_get_playlist_id('https://example.com'))


class TestGetChannelIdentifier(unittest.TestCase):

    def test_handle(self):
        """@handle 추출"""
        result = _get_channel_identifier('https://www.youtube.com/@testuser')
        self.assertEqual(result['type'], 'handle')
        self.assertEqual(result['value'], 'testuser')

    def test_channel_id(self):
        """채널 ID 추출"""
        result = _get_channel_identifier('https://www.youtube.com/channel/UCabcdef123')
        self.assertEqual(result['type'], 'id')
        self.assertEqual(result['value'], 'UCabcdef123')

    def test_custom(self):
        """커스텀 이름 추출"""
        result = _get_channel_identifier('https://www.youtube.com/c/MyChannel')
        self.assertEqual(result['type'], 'custom')
        self.assertEqual(result['value'], 'MyChannel')

    def test_no_match(self):
        """매칭 없음 → None"""
        self.assertIsNone(_get_channel_identifier('https://example.com'))


class TestGetTranscriptViaSupadata(unittest.TestCase):

    def test_no_api_key(self):
        """API 키 없음 → None"""
        self.assertIsNone(get_transcript_via_supadata('vid1', ''))

    @patch('services.core.content_service.requests.get')
    def test_success_content(self, mock_get):
        """content 필드 성공"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'content': '자막 내용입니다'}
        mock_get.return_value = mock_resp

        result = get_transcript_via_supadata('vid1', 'test-key')
        self.assertEqual(result, '자막 내용입니다')

    @patch('services.core.content_service.requests.get')
    def test_success_transcript_list(self, mock_get):
        """transcript 리스트 성공"""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'content': '',
            'transcript': [{'text': '첫째'}, {'text': '둘째'}]
        }
        mock_get.return_value = mock_resp

        result = get_transcript_via_supadata('vid1', 'test-key')
        self.assertEqual(result, '첫째 둘째')

    @patch('services.core.content_service.requests.get')
    def test_401_error(self, mock_get):
        """401 → API 키 오류"""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        result = get_transcript_via_supadata('vid1', 'bad-key')
        self.assertIsInstance(result, dict)
        self.assertIn('유효하지 않', result['error'])

    @patch('services.core.content_service.requests.get')
    def test_timeout(self, mock_get):
        """타임아웃 → None"""
        mock_get.side_effect = requests.exceptions.Timeout('timeout')
        result = get_transcript_via_supadata('vid1', 'key')
        self.assertIsNone(result)

    @patch('services.core.content_service.requests.get')
    def test_request_error(self, mock_get):
        """네트워크 오류 → None"""
        mock_get.side_effect = requests.exceptions.RequestException('network')
        result = get_transcript_via_supadata('vid1', 'key')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
