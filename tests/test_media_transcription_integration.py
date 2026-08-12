"""AI-Video-Transcriber 흡수: 비동기 로컬 미디어 전사 계약 테스트."""
from __future__ import annotations

import json
import os
import subprocess
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from services.transcript.media_normalizer import MediaValidationError, normalize_media
from services.transcript.media_transcription_jobs import create_job, read_job, run_job

_H = {"Origin": "http://localhost:3000"}


def _client():
    app = create_app({"TESTING": True})
    return app.test_client()


def _no_auth_patch():
    return patch(
        "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
        return_value=False,
    )


def test_transcribe_audio_detailed_preserves_timestamps_and_language():
    from services.transcript.whisper_service import transcribe_audio_detailed

    first = MagicMock(start=1.25, end=3.5, text=" 첫 문장 ")
    second = MagicMock(start=4.0, end=7.75, text="둘째 문장")
    info = MagicMock(language="ko", language_probability=0.97)
    model = MagicMock()
    model.transcribe.return_value = ([first, second], info)
    whisper_module = MagicMock()
    whisper_module.WhisperModel.return_value = model

    with patch.dict("sys.modules", {"faster_whisper": whisper_module}):
        result = transcribe_audio_detailed("/tmp/input.wav", "small")

    assert result == {
        "text": "첫 문장 둘째 문장",
        "segments": [
            {"start": 1.25, "end": 3.5, "text": "첫 문장"},
            {"start": 4.0, "end": 7.75, "text": "둘째 문장"},
        ],
        "language": "ko",
        "language_probability": 0.97,
    }
    kwargs = model.transcribe.call_args.kwargs
    assert kwargs["vad_filter"] is True
    assert kwargs["condition_on_previous_text"] is False


def test_create_media_transcription_enqueues_valid_mp4(tmp_path):
    client = _client()
    mp4 = b"\x00\x00\x00\x18ftypisom" + (b"0" * 32)
    record = {
        "job_id": "ec16b9e0-bbb1-456a-bc4d-e4a8199e3982",
        "status": "queued",
    }
    target = tmp_path / "job.mp4"

    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("importlib.util.find_spec", return_value=object()),
        patch("services.transcript.media_transcription_jobs.create_job", return_value=(record, target)),
        patch("services.transcript.media_transcription_jobs.enqueue_job") as enqueue,
    ):
        response = client.post(
            "/api/media-transcriptions",
            data={"file": (BytesIO(mp4), "회의 영상.mp4", "video/mp4")},
            content_type="multipart/form-data",
            headers=_H,
        )

    assert response.status_code == 202
    assert target.read_bytes() == mp4
    enqueue.assert_called_once_with(record["job_id"], str(target))
    assert response.get_json()["poll_url"].endswith(record["job_id"])


def test_create_media_transcription_rejects_fake_video():
    client = _client()
    with (
        _no_auth_patch(),
        patch.dict(os.environ, {"WHISPER_ENABLED": "true"}),
        patch("importlib.util.find_spec", return_value=object()),
        patch("services.transcript.media_transcription_jobs.enqueue_job") as enqueue,
    ):
        response = client.post(
            "/api/media-transcriptions",
            data={"file": (BytesIO(b"not a video"), "fake.mp4", "video/mp4")},
            content_type="multipart/form-data",
            headers=_H,
        )

    assert response.status_code == 400
    assert "지원하지 않는 파일" in response.get_json()["error"]
    enqueue.assert_not_called()


def test_media_job_owner_is_enforced(tmp_path):
    with patch("services.transcript.media_transcription_jobs.MEDIA_TRANSCRIPTION_DIR", str(tmp_path)):
        record, _ = create_job(
            owner_id="owner-a", source_title="회의", source_type="video", suffix=".mp4",
        )
        assert read_job(record["job_id"], "owner-a") is not None
        assert read_job(record["job_id"], "owner-b") is None


def test_worker_normalizes_transcribes_and_cleans_files(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"source")
    normalized = tmp_path / "normalized.wav"
    normalized.write_bytes(b"wav")
    transcript = {
        "text": "충분히 긴 전사 결과입니다. " * 3,
        "segments": [{"start": 0.0, "end": 2.0, "text": "첫 구간"}],
        "language": "ko",
        "language_probability": 0.96,
    }
    probe = MagicMock(duration_seconds=12.5)

    with (
        patch("services.transcript.media_transcription_jobs.MEDIA_TRANSCRIPTION_DIR", str(tmp_path / "jobs")),
        patch("services.transcript.media_transcription_jobs.normalize_media", return_value=(str(normalized), probe)),
        patch("services.transcript.whisper_service.transcribe_audio_detailed", return_value=transcript),
    ):
        record, expected_input = create_job(
            owner_id="owner", source_title="회의", source_type="video", suffix=".mp4",
        )
        expected_input.write_bytes(source.read_bytes())
        run_job(record["job_id"], str(expected_input))
        completed = read_job(record["job_id"], "owner")

    assert completed["status"] == "succeeded"
    assert completed["result"]["transcript_segments"] == transcript["segments"]
    assert not expected_input.exists()
    assert not normalized.exists()


def test_normalize_media_uses_ffprobe_and_safe_ffmpeg(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"media")
    probe_json = json.dumps({
        "format": {"duration": "12.5", "format_name": "mov,mp4"},
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
    })
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        if "ffprobe" in Path(command[0]).name:
            return MagicMock(stdout=probe_json)
        Path(command[-1]).write_bytes(b"wav")
        return MagicMock(stdout="")

    with patch("services.transcript.media_normalizer.subprocess.run", side_effect=fake_run):
        output, probe = normalize_media(
            str(source), max_duration_seconds=60, timeout_seconds=30,
        )
    try:
        assert probe.duration_seconds == 12.5
        ffmpeg_command, ffmpeg_kwargs = calls[1]
        assert ffmpeg_command[ffmpeg_command.index("-ac") + 1] == "1"
        assert ffmpeg_command[ffmpeg_command.index("-ar") + 1] == "16000"
        assert "shell" not in ffmpeg_kwargs
    finally:
        Path(output).unlink(missing_ok=True)


def test_normalize_media_rejects_no_audio_track(tmp_path):
    source = tmp_path / "silent.mp4"
    source.write_bytes(b"media")
    payload = json.dumps({
        "format": {"duration": "10", "format_name": "mov,mp4"},
        "streams": [{"codec_type": "video", "codec_name": "h264"}],
    })
    with patch(
        "services.transcript.media_normalizer.subprocess.run",
        return_value=MagicMock(stdout=payload),
    ):
        with pytest.raises(MediaValidationError, match="오디오 트랙"):
            normalize_media(str(source), max_duration_seconds=60, timeout_seconds=30)


def test_normalize_media_removes_temporary_wav_when_ffmpeg_fails(tmp_path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"media")
    probe_json = json.dumps({
        "format": {"duration": "1", "format_name": "mov,mp4"},
        "streams": [{"codec_type": "audio", "codec_name": "aac"}],
    })
    created = tmp_path / "normalized.wav"

    def fake_mkstemp(*_args, **_kwargs):
        created.write_bytes(b"")
        return os.open(created, os.O_RDWR), str(created)

    def fake_run(command, **_kwargs):
        if "ffprobe" in Path(command[0]).name:
            return MagicMock(stdout=probe_json)
        raise subprocess.CalledProcessError(1, command)

    with (
        patch("services.transcript.media_normalizer.tempfile.mkstemp", side_effect=fake_mkstemp),
        patch("services.transcript.media_normalizer.subprocess.run", side_effect=fake_run),
    ):
        with pytest.raises(MediaValidationError):
            normalize_media(str(source), max_duration_seconds=60, timeout_seconds=30)
    assert not created.exists()


def test_generate_direct_media_preserves_source_and_valid_segments():
    client = _client()
    text = "로컬 영상에서 전사한 충분히 긴 내용입니다. " * 4
    segments = [
        {"start": -1, "end": "bad", "text": "폐기"},
        {"start": 1, "end": 2, "text": "유효"},
    ]
    ai_result = {
        "title": "회의 요약", "content": "핵심 요약", "html": "<p>핵심 요약</p>",
        "usage": {"total_tokens": 3},
    }
    with (
        _no_auth_patch(),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        response = client.post(
            "/generate",
            json={
                "content": text,
                "source_type": "video",
                "source_title": "회의 영상",
                "transcript_source": "whisper",
                "detected_language": "ko",
                "transcript_segments": segments,
            },
            headers=_H,
        )

    assert response.status_code == 200
    data = response.get_json()
    assert data["source_type"] == "video"
    assert data["transcript_source"] == "whisper"
    assert data["source_meta"]["detected_language"] == "ko"
    assert data["transcript_segments"] == [{"start": 1.0, "end": 2.0, "text": "유효"}]
