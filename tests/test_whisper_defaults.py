from unittest.mock import MagicMock, patch

from services.transcript.whisper_service import (
    extract_transcript_whisper,
    transcribe_audio,
)


def test_transcribe_audio_uses_base_model_size_by_default():
    mock_segment = MagicMock()
    mock_segment.text = "hello"

    mock_info = MagicMock()
    mock_info.language = "en"
    mock_info.language_probability = 0.99

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    mock_whisper = MagicMock()
    mock_whisper.WhisperModel.return_value = mock_model

    with patch.dict("sys.modules", {"faster_whisper": mock_whisper}):
        result = transcribe_audio("/tmp/audio.wav")

    assert result == "hello"
    assert mock_whisper.WhisperModel.call_args.args[0] == "base"


@patch("services.transcript.whisper_service._cleanup_file")
@patch("services.transcript.whisper_service.transcribe_audio", return_value="transcript")
@patch("services.transcript.whisper_service.download_audio", return_value="/tmp/audio.wav")
def test_extract_transcript_whisper_uses_base_model_size_by_default(
    mock_download_audio,
    mock_transcribe_audio,
    mock_cleanup_file,
):
    result = extract_transcript_whisper("https://youtube.com/watch?v=test")

    assert result == "transcript"
    mock_download_audio.assert_called_once_with("https://youtube.com/watch?v=test")
    mock_transcribe_audio.assert_called_once_with("/tmp/audio.wav", "base")
    mock_cleanup_file.assert_called_once_with("/tmp/audio.wav")
