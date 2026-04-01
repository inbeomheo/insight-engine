from unittest.mock import MagicMock, patch

from services.transcript.whisper_service import transcribe_audio


def test_transcribe_audio_retries_on_cpu_when_cuda_model_init_fails():
    mock_segment = MagicMock()
    mock_segment.text = "fallback transcript"

    mock_info = MagicMock()
    mock_info.language = "ko"
    mock_info.language_probability = 0.99

    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([mock_segment], mock_info)

    init_calls = []

    def whisper_model_side_effect(model_size, device, compute_type):
        init_calls.append((model_size, device, compute_type))
        if device == "cuda":
            raise RuntimeError("CUDA initialization failed")
        return mock_model

    mock_whisper = MagicMock()
    mock_whisper.WhisperModel.side_effect = whisper_model_side_effect

    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True

    with patch.dict("sys.modules", {"faster_whisper": mock_whisper, "torch": mock_torch}):
        result = transcribe_audio("/tmp/audio.wav", model_size="base", language="ko")

    assert result == "fallback transcript"
    assert init_calls == [
        ("base", "cuda", "float16"),
        ("base", "cpu", "int8"),
    ]
    mock_model.transcribe.assert_called_once_with(
        "/tmp/audio.wav",
        language="ko",
        beam_size=5,
    )
