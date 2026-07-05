"""Audio transcription extraction API tests."""
from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from app import create_app

_H = {"Origin": "http://localhost:3000"}
MP3_MIME = "audio/mpeg"
AUDIO_ONLY_ERROR = "MP3, WAV, M4A, OGG, FLAC, AAC 파일만 업로드할 수 있습니다."
WHISPER_DISABLED_ERROR = "음성 전사를 위해 서버에 WHISPER_ENABLED=true 설정이 필요합니다."
EMPTY_TRANSCRIPT_ERROR = "음성 인식 결과가 비어 있습니다. 오디오 파일을 확인해주세요."


def _app_client():
    app = create_app({"TESTING": True, "RATELIMIT_ENABLED": False})
    return app, app.test_client()


def _no_auth_patch():
    return patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    )


def _minimal_mp3_bytes() -> bytes:
    return b"ID3\x04\x00\x00\x00\x00\x00\x10route validation fixture\n"


def _upload(client, content: bytes, filename: str = "sample.mp3", content_type: str = MP3_MIME):
    return client.post(
        "/api/extract-audio",
        data={"file": (BytesIO(content), filename, content_type)},
        content_type="multipart/form-data",
        headers=_H,
    )


def _remove_temp_file(path: str) -> None:
    Path(path).unlink(missing_ok=True)


def test_extract_audio_whisper_disabled_returns_400_korean_message():
    _, client = _app_client()

    with _no_auth_patch(), patch.dict(os.environ, {"WHISPER_ENABLED": "false"}):
        resp = _upload(client, _minimal_mp3_bytes())

    assert resp.status_code == 400
    assert resp.get_json()["error"] == WHISPER_DISABLED_ERROR


def test_extract_audio_happy_path_returns_text_and_truncation_false():
    _, client = _app_client()
    transcript = "This is a readable audio transcript for direct text reuse. " * 2

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true", "WHISPER_MODEL_SIZE": "small"}),
        patch("services.transcript.whisper_service.transcribe_audio", return_value=transcript) as mock_transcribe,
        patch("services.transcript.whisper_service._cleanup_file", side_effect=_remove_temp_file) as mock_cleanup,
    ):
        resp = _upload(client, _minimal_mp3_bytes())

    assert resp.status_code == 200
    data = resp.get_json()
    assert "readable audio transcript" in data["text"]
    assert data["truncated"] is False
    assert "pages" not in data
    assert mock_transcribe.call_args.args[1] == "small"
    mock_cleanup.assert_called_once()


def test_extract_audio_rejects_non_audio_extension_with_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("services.transcript.whisper_service.transcribe_audio") as mock_transcribe,
    ):
        resp = _upload(client, b"not audio", filename="note.txt", content_type="text/plain")

    assert resp.status_code == 400
    assert resp.get_json()["error"] == AUDIO_ONLY_ERROR
    mock_transcribe.assert_not_called()


def test_extract_audio_rejects_oversized_file_with_limit_message():
    _, client = _app_client()
    oversized = b"RIFF" + (b"A" * 32)

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("config.AUDIO_UPLOAD_MAX_BYTES", 20),
        patch("services.transcript.whisper_service.transcribe_audio") as mock_transcribe,
    ):
        resp = _upload(client, oversized, filename="sample.wav", content_type="audio/wav")

    assert resp.status_code == 400
    assert "최대 20바이트" in resp.get_json()["error"]
    mock_transcribe.assert_not_called()


def test_extract_audio_empty_transcript_returns_400_korean_message():
    _, client = _app_client()

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("services.transcript.whisper_service.transcribe_audio", return_value="   "),
    ):
        resp = _upload(client, _minimal_mp3_bytes())

    assert resp.status_code == 400
    assert resp.get_json()["error"] == EMPTY_TRANSCRIPT_ERROR


def test_extract_audio_truncates_at_direct_text_max_chars():
    _, client = _app_client()
    transcript = "Alpha beta gamma delta " * 20

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("config.DIRECT_TEXT_MAX_CHARS", 80),
        patch("services.transcript.whisper_service.transcribe_audio", return_value=transcript),
    ):
        resp = _upload(client, _minimal_mp3_bytes())

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["truncated"] is True
    assert len(data["text"]) == 80
