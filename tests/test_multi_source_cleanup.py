import shutil
from unittest.mock import patch

import pytest

from services.content.multi_source_collector import _collect_podcast


def test_collect_podcast_cleans_ytdlp_audio_dir_in_finally(tmp_path, monkeypatch):
    audio_dir = tmp_path / "ytdlp_audio_case"
    audio_dir.mkdir()

    audio_path = audio_dir / "episode.wav"
    audio_path.write_bytes(b"fake audio")

    url = "https://example.com/episode.mp3"
    monkeypatch.setenv("WHISPER_ENABLED", "true")
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "base")

    with patch(
        "services.platform.spotify_service.is_spotify_episode_url",
        return_value=False,
    ), patch(
        "services.transcript.whisper_service.download_audio",
        return_value=str(audio_path),
    ) as mock_download, patch(
        "services.transcript.whisper_service.transcribe_audio",
        side_effect=RuntimeError("transcribe failed"),
    ) as mock_transcribe, patch(
        "shutil.rmtree",
        wraps=shutil.rmtree,
    ) as mock_rmtree:
        with pytest.raises(RuntimeError, match="transcribe failed"):
            _collect_podcast(url)

    mock_download.assert_called_once_with(url)
    mock_transcribe.assert_called_once_with(str(audio_path), "base")
    mock_rmtree.assert_called_once_with(str(audio_dir), ignore_errors=True)
    assert not audio_dir.exists()
