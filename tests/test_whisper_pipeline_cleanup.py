from pathlib import Path
from unittest.mock import patch

from services.transcript.whisper_service import extract_transcript_whisper


@patch("services.transcript.whisper_service._cleanup_file")
@patch("services.transcript.whisper_service.shutil.rmtree")
@patch("services.transcript.whisper_service.transcribe_audio", return_value="transcript")
@patch("services.transcript.whisper_service.download_audio")
def test_extract_transcript_whisper_removes_ytdlp_audio_directory_in_finally(
    mock_download_audio,
    mock_transcribe_audio,
    mock_rmtree,
    mock_cleanup_file,
):
    audio_path = Path.cwd() / "ytdlp_audio_case" / "audio.wav"
    mock_download_audio.return_value = str(audio_path)

    result = extract_transcript_whisper("https://youtube.com/watch?v=test")

    assert result == "transcript"
    mock_download_audio.assert_called_once_with("https://youtube.com/watch?v=test")
    mock_transcribe_audio.assert_called_once_with(str(audio_path), "base")
    mock_rmtree.assert_called_once_with(str(audio_path.parent), ignore_errors=True)
    mock_cleanup_file.assert_not_called()


@patch("services.transcript.whisper_service._cleanup_file")
@patch("services.transcript.whisper_service.shutil.rmtree")
@patch("services.transcript.whisper_service.transcribe_audio", return_value="transcript")
@patch("services.transcript.whisper_service.download_audio")
def test_extract_transcript_whisper_calls_cleanup_file_for_regular_path(
    mock_download_audio,
    mock_transcribe_audio,
    mock_rmtree,
    mock_cleanup_file,
):
    audio_path = Path.cwd() / "regular_audio" / "audio.wav"
    mock_download_audio.return_value = str(audio_path)

    result = extract_transcript_whisper("https://youtube.com/watch?v=test")

    assert result == "transcript"
    mock_download_audio.assert_called_once_with("https://youtube.com/watch?v=test")
    mock_transcribe_audio.assert_called_once_with(str(audio_path), "base")
    mock_cleanup_file.assert_called_once_with(str(audio_path))
    mock_rmtree.assert_not_called()
