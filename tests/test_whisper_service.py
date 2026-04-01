"""whisper_service 단위 테스트"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from services.transcript.whisper_service import (
    _cleanup_file,
    download_audio,
    transcribe_audio,
    extract_transcript_whisper,
)


class TestCleanupFile(unittest.TestCase):

    def test_existing_file(self):
        """존재하는 파일 삭제"""
        fd, path = tempfile.mkstemp()
        os.close(fd)
        self.assertTrue(os.path.exists(path))
        _cleanup_file(path)
        self.assertFalse(os.path.exists(path))

    def test_nonexistent_file(self):
        """존재하지 않는 파일 → 에러 없음"""
        _cleanup_file('/nonexistent/file.wav')

    def test_none_path(self):
        """None → 에러 없음"""
        _cleanup_file(None)

    def test_empty_string(self):
        """빈 문자열 → 에러 없음"""
        _cleanup_file('')


class TestDownloadAudio(unittest.TestCase):

    @patch.dict('sys.modules', {'yt_dlp': None})
    def test_no_yt_dlp(self):
        """yt-dlp 미설치 → None"""
        # yt_dlp import 실패 시뮬레이션
        import importlib
        import services.transcript.whisper_service as ws
        with patch.object(ws, 'download_audio', wraps=ws.download_audio):
            # 직접 ImportError를 시뮬레이션
            with patch('builtins.__import__', side_effect=ImportError('no yt_dlp')):
                result = download_audio('https://youtube.com/watch?v=test')
        self.assertIsNone(result)

    def test_empty_audio_file(self):
        """오디오 파일 비어있음 → None"""
        mock_yt_dlp = MagicMock()
        mock_ydl = MagicMock()
        mock_yt_dlp.YoutubeDL.return_value.__enter__ = MagicMock(return_value=mock_ydl)
        mock_yt_dlp.YoutubeDL.return_value.__exit__ = MagicMock(return_value=False)

        with patch.dict('sys.modules', {'yt_dlp': mock_yt_dlp}):
            with patch('services.transcript.whisper_service.tempfile.mkdtemp', return_value='/tmp/ytdlp_audio_test'):
                with patch('services.transcript.whisper_service.os.listdir', return_value=['audio.wav']):
                    with patch('services.transcript.whisper_service.os.path.getsize', return_value=0):
                        with patch('services.transcript.whisper_service.shutil.rmtree'):
                            result = download_audio('https://youtube.com/watch?v=test')
        self.assertIsNone(result)


class TestTranscribeAudio(unittest.TestCase):

    def test_no_faster_whisper(self):
        """faster-whisper 미설치 → None"""
        with patch('builtins.__import__', side_effect=ImportError('no faster_whisper')):
            result = transcribe_audio('/tmp/audio.wav')
        self.assertIsNone(result)

    def test_success(self):
        """정상 변환"""
        mock_segment1 = MagicMock()
        mock_segment1.text = '안녕하세요'
        mock_segment2 = MagicMock()
        mock_segment2.text = '테스트입니다'

        mock_info = MagicMock()
        mock_info.language = 'ko'
        mock_info.language_probability = 0.95

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([mock_segment1, mock_segment2], mock_info)

        mock_whisper = MagicMock()
        mock_whisper.WhisperModel.return_value = mock_model

        with patch.dict('sys.modules', {'faster_whisper': mock_whisper}):
            result = transcribe_audio('/tmp/audio.wav')
        self.assertEqual(result, '안녕하세요 테스트입니다')

    def test_empty_segments(self):
        """빈 세그먼트 → None"""
        mock_info = MagicMock()
        mock_info.language = 'ko'

        mock_model = MagicMock()
        mock_model.transcribe.return_value = ([], mock_info)

        mock_whisper = MagicMock()
        mock_whisper.WhisperModel.return_value = mock_model

        with patch.dict('sys.modules', {'faster_whisper': mock_whisper}):
            result = transcribe_audio('/tmp/audio.wav')
        self.assertIsNone(result)

    def test_exception(self):
        """변환 예외 → None"""
        mock_whisper = MagicMock()
        mock_whisper.WhisperModel.side_effect = Exception('model error')

        with patch.dict('sys.modules', {'faster_whisper': mock_whisper}):
            result = transcribe_audio('/tmp/audio.wav')
        self.assertIsNone(result)


class TestExtractTranscriptWhisper(unittest.TestCase):

    # download_audio는 ytdlp_audio_ 접두사 디렉토리 내부 파일을 반환
    MOCK_AUDIO_DIR = '/tmp/ytdlp_audio_abc123'
    MOCK_AUDIO_PATH = '/tmp/ytdlp_audio_abc123/audio.wav'

    @patch('services.transcript.whisper_service.shutil.rmtree')
    @patch('services.transcript.whisper_service.transcribe_audio', return_value='변환된 텍스트')
    @patch('services.transcript.whisper_service.download_audio')
    def test_success(self, mock_dl, mock_transcribe, mock_rmtree):
        """전체 파이프라인 성공 — 디렉토리 정리"""
        mock_dl.return_value = self.MOCK_AUDIO_PATH
        result = extract_transcript_whisper('https://youtube.com/watch?v=test')
        self.assertEqual(result, '변환된 텍스트')
        mock_rmtree.assert_called_once_with(self.MOCK_AUDIO_DIR, ignore_errors=True)

    @patch('services.transcript.whisper_service.shutil.rmtree')
    @patch('services.transcript.whisper_service.download_audio', return_value=None)
    def test_download_fails(self, mock_dl, mock_rmtree):
        """다운로드 실패 → None"""
        result = extract_transcript_whisper('https://youtube.com/watch?v=fail')
        self.assertIsNone(result)

    @patch('services.transcript.whisper_service.shutil.rmtree')
    @patch('services.transcript.whisper_service.transcribe_audio', return_value=None)
    @patch('services.transcript.whisper_service.download_audio')
    def test_transcribe_fails(self, mock_dl, mock_transcribe, mock_rmtree):
        """변환 실패 → None, 디렉토리 정리"""
        mock_dl.return_value = self.MOCK_AUDIO_PATH
        result = extract_transcript_whisper('https://youtube.com/watch?v=test')
        self.assertIsNone(result)
        mock_rmtree.assert_called_once_with(self.MOCK_AUDIO_DIR, ignore_errors=True)

    @patch('services.transcript.whisper_service.shutil.rmtree')
    @patch('services.transcript.whisper_service.download_audio', side_effect=Exception('unexpected'))
    def test_pipeline_exception(self, mock_dl, mock_rmtree):
        """파이프라인 예외 → None"""
        result = extract_transcript_whisper('https://youtube.com/watch?v=err')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
