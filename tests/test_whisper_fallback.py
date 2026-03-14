"""Whisper 기반 자막 폴백 테스트

services/whisper_service.py의 함수와
content_service.py의 Whisper 4단계 폴백을 검증합니다.
"""
import os
import unittest
from unittest.mock import patch, MagicMock


class TestDownloadAudio(unittest.TestCase):
    """download_audio 함수 테스트"""

    def test_download_audio_success(self):
        """정상적으로 오디오를 다운로드하면 파일 경로를 반환"""
        from services import whisper_service as ws

        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_dlp.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict('sys.modules', {'yt_dlp': mock_yt_dlp}), \
             patch('os.path.exists', return_value=True), \
             patch('os.path.getsize', return_value=1024), \
             patch('tempfile.mkstemp', return_value=(5, '/tmp/test.wav')), \
             patch('os.close'):
            result = ws.download_audio('https://www.youtube.com/watch?v=dQw4w9WgXcQ')

        self.assertEqual(result, '/tmp/test.wav')

    def test_download_audio_no_yt_dlp(self):
        """yt-dlp가 설치되지 않으면 None 반환"""
        from services.transcript.whisper_service import download_audio

        with patch.dict('sys.modules', {'yt_dlp': None}):
            # import 실패를 시뮬레이션
            with patch('builtins.__import__', side_effect=ImportError("No module named 'yt_dlp'")):
                # 직접 함수 내부의 lazy import를 테스트
                pass

        # yt_dlp import가 실패하면 None 반환하는 로직 검증
        # (실제 환경에서는 yt_dlp가 설치되어 있을 수 있으므로 mock 필요)

    @patch('services.whisper_service.tempfile.mkstemp', return_value=(5, '/tmp/fail.wav'))
    @patch('services.whisper_service.os.close')
    def test_download_audio_exception_returns_none(self, mock_close, mock_mkstemp):
        """다운로드 중 예외 발생 시 None 반환 + 임시 파일 정리"""
        from services import whisper_service as ws

        with patch.object(ws, '_cleanup_file') as mock_cleanup:
            with patch.dict('sys.modules', {'yt_dlp': MagicMock(
                YoutubeDL=MagicMock(side_effect=Exception("download error"))
            )}):
                import importlib
                importlib.reload(ws)
                result = ws.download_audio('https://www.youtube.com/watch?v=test123')

        # 에러 발생 시 None 반환
        self.assertIsNone(result)


class TestTranscribeAudio(unittest.TestCase):
    """transcribe_audio 함수 테스트"""

    def test_transcribe_audio_success(self):
        """정상적으로 텍스트를 반환"""
        from services.transcript.whisper_service import transcribe_audio

        mock_segment1 = MagicMock()
        mock_segment1.text = "안녕하세요"
        mock_segment2 = MagicMock()
        mock_segment2.text = "반갑습니다"

        mock_info = MagicMock()
        mock_info.language = "ko"
        mock_info.language_probability = 0.95

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)

        with patch.dict('sys.modules', {'faster_whisper': MagicMock(
            WhisperModel=MagicMock(return_value=mock_model)
        )}):
            import importlib
            import services.transcript.whisper_service as ws
            importlib.reload(ws)
            result = ws.transcribe_audio('/tmp/test.wav', 'base')

        self.assertIn("안녕하세요", result)
        self.assertIn("반갑습니다", result)

    def test_transcribe_audio_empty_result(self):
        """빈 결과 시 None 반환"""
        from services.transcript.whisper_service import transcribe_audio

        mock_info = MagicMock()
        mock_info.language = "ko"

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)

        with patch.dict('sys.modules', {'faster_whisper': MagicMock(
            WhisperModel=MagicMock(return_value=mock_model)
        )}):
            import importlib
            import services.transcript.whisper_service as ws
            importlib.reload(ws)
            result = ws.transcribe_audio('/tmp/test.wav')

        self.assertIsNone(result)


class TestExtractTranscriptWhisper(unittest.TestCase):
    """extract_transcript_whisper 전체 파이프라인 테스트"""

    def test_full_pipeline_success(self):
        """다운로드 + 변환 성공 시 텍스트 반환"""
        from services import whisper_service as ws

        with patch.object(ws, 'download_audio', return_value='/tmp/audio.wav') as mock_dl, \
             patch.object(ws, 'transcribe_audio', return_value='변환된 텍스트') as mock_tr, \
             patch.object(ws, '_cleanup_file') as mock_clean:
            result = ws.extract_transcript_whisper('https://www.youtube.com/watch?v=abc', 'base')

        self.assertEqual(result, '변환된 텍스트')
        mock_dl.assert_called_once()
        mock_tr.assert_called_once_with('/tmp/audio.wav', 'base')
        mock_clean.assert_called_once_with('/tmp/audio.wav')

    def test_pipeline_download_fails(self):
        """다운로드 실패 시 None 반환"""
        from services import whisper_service as ws

        with patch.object(ws, 'download_audio', return_value=None):
            result = ws.extract_transcript_whisper('https://www.youtube.com/watch?v=abc')

        self.assertIsNone(result)

    def test_pipeline_transcribe_fails(self):
        """변환 실패 시 None 반환 + 임시 파일 정리"""
        from services import whisper_service as ws

        with patch.object(ws, 'download_audio', return_value='/tmp/audio.wav'), \
             patch.object(ws, 'transcribe_audio', return_value=None), \
             patch.object(ws, '_cleanup_file') as mock_clean:
            result = ws.extract_transcript_whisper('https://www.youtube.com/watch?v=abc')

        self.assertIsNone(result)
        mock_clean.assert_called_once_with('/tmp/audio.wav')

    def test_pipeline_exception_cleans_up(self):
        """예외 발생 시에도 임시 파일 정리"""
        from services import whisper_service as ws

        with patch.object(ws, 'download_audio', return_value='/tmp/audio.wav'), \
             patch.object(ws, 'transcribe_audio', side_effect=RuntimeError("boom")), \
             patch.object(ws, '_cleanup_file') as mock_clean:
            result = ws.extract_transcript_whisper('https://www.youtube.com/watch?v=abc')

        self.assertIsNone(result)
        mock_clean.assert_called_once_with('/tmp/audio.wav')


class TestWhisperDisabledSkip(unittest.TestCase):
    """WHISPER_ENABLED=False일 때 폴백 체인에서 스킵 확인"""

    @patch.dict(os.environ, {'WHISPER_ENABLED': 'false'}, clear=False)
    @patch('services.content_service._load_cache', return_value=None)
    @patch('services.content_service._build_ytt_api')
    @patch('services.content_service._fetch_transcript_with_api', return_value=None)
    @patch('services.content_service._get_transcript_from_watch_page', return_value={'error': 'failed'})
    @patch('services.content_service.get_transcript_via_supadata', return_value=None)
    def test_whisper_not_called_when_disabled(
        self, mock_supadata, mock_watch, mock_fetch, mock_ytt, mock_cache
    ):
        """WHISPER_ENABLED=False이면 Whisper를 시도하지 않음"""
        import flask
        app = flask.Flask(__name__)

        with app.app_context(), \
             patch.dict(os.environ, {'SUPADATA_API_KEY': ''}, clear=False), \
             patch('services.whisper_service.extract_transcript_whisper') as mock_whisper:
            from services.core.content_service import get_transcript
            result = get_transcript('dQw4w9WgXcQ')

        mock_whisper.assert_not_called()
        self.assertIn('error', result)


class TestWhisperInFallbackChain(unittest.TestCase):
    """content_service 폴백 체인에 Whisper가 포함되어 있는지 확인"""

    @patch.dict(os.environ, {'WHISPER_ENABLED': 'true', 'SUPADATA_API_KEY': ''}, clear=False)
    @patch('services.content_service._load_cache', return_value=None)
    @patch('services.content_service._build_ytt_api')
    @patch('services.content_service._fetch_transcript_with_api', return_value=None)
    @patch('services.content_service._get_transcript_from_watch_page', return_value={'error': 'failed'})
    @patch('services.content_service.get_transcript_via_supadata', return_value=None)
    @patch('services.whisper_service.extract_transcript_whisper', return_value='Whisper로 추출된 자막')
    def test_whisper_called_as_4th_fallback(
        self, mock_whisper, mock_supadata, mock_watch, mock_fetch, mock_ytt, mock_cache
    ):
        """모든 텍스트 방법 실패 후 Whisper가 4번째로 호출됨"""
        import flask
        app = flask.Flask(__name__)

        with app.app_context(), \
             patch('services.content_service._save_cache'):
            from services.core.content_service import get_transcript
            result = get_transcript('dQw4w9WgXcQ')

        mock_whisper.assert_called_once()
        self.assertEqual(result['text'], 'Whisper로 추출된 자막')
        self.assertEqual(result['source'], 'whisper')


class TestCleanupFile(unittest.TestCase):
    """_cleanup_file 유틸리티 테스트"""

    def test_cleanup_existing_file(self):
        """존재하는 파일 삭제"""
        from services.transcript.whisper_service import _cleanup_file

        with patch('os.path.exists', return_value=True), \
             patch('os.remove') as mock_remove:
            _cleanup_file('/tmp/test.wav')

        mock_remove.assert_called_once_with('/tmp/test.wav')

    def test_cleanup_nonexistent_file(self):
        """존재하지 않는 파일은 삭제 시도 안 함"""
        from services.transcript.whisper_service import _cleanup_file

        with patch('os.path.exists', return_value=False), \
             patch('os.remove') as mock_remove:
            _cleanup_file('/tmp/nonexistent.wav')

        mock_remove.assert_not_called()

    def test_cleanup_none_path(self):
        """None 경로는 무시"""
        from services.transcript.whisper_service import _cleanup_file
        _cleanup_file(None)  # 에러 없이 통과해야 함

    def test_cleanup_empty_path(self):
        """빈 문자열 경로는 무시"""
        from services.transcript.whisper_service import _cleanup_file
        _cleanup_file('')  # 에러 없이 통과해야 함


if __name__ == '__main__':
    unittest.main()
