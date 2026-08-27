import os
from unittest.mock import MagicMock, patch

from services.media.video_deepdive_service import MonitoredDownloadError
from services.transcript.whisper_service import download_audio


def test_download_audio_uses_canonical_youtube_url_and_monitored_download(tmp_path):
    tmp_dir = tmp_path / "ytdlp_audio_dir"
    tmp_dir.mkdir()
    audio_path = tmp_dir / "audio.m4a"
    video_url = "https://youtu.be/dQw4w9WgXcQ?feature=share"

    def write_audio(_args, **_kwargs):
        audio_path.write_bytes(b"audio")

    with patch(
        "services.transcript.whisper_service.tempfile.mkdtemp",
        return_value=str(tmp_dir),
    ) as mkdtemp_mock, patch(
        "services.media.video_deepdive_service.run_monitored_download",
        side_effect=write_audio,
    ) as monitored, patch(
        "services.transcript.whisper_service.shutil.rmtree"
    ) as rmtree_mock:
        result = download_audio(video_url)

    assert result == str(audio_path)
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    args = monitored.call_args.args[0]
    assert "--no-playlist" in args
    assert "--max-filesize" in args
    assert args[-1] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert oct(os.stat(audio_path).st_mode & 0o777) == "0o600"
    rmtree_mock.assert_not_called()


def test_download_audio_returns_none_and_cleans_empty_dir(tmp_path):
    tmp_dir = tmp_path / "empty_audio_dir"
    tmp_dir.mkdir()
    video_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    with patch(
        "services.transcript.whisper_service.tempfile.mkdtemp",
        return_value=str(tmp_dir),
    ) as mkdtemp_mock, patch(
        "services.media.video_deepdive_service.run_monitored_download"
    ), patch(
        "services.transcript.whisper_service.shutil.rmtree"
    ) as rmtree_mock:
        result = download_audio(video_url)

    assert result is None
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    rmtree_mock.assert_called_once_with(str(tmp_dir), ignore_errors=True)


def test_download_audio_cleans_temp_dir_when_ytdlp_raises(tmp_path):
    tmp_dir = tmp_path / "failed_audio_dir"
    tmp_dir.mkdir()
    video_url = "https://youtube.com/watch?v=dQw4w9WgXcQ"

    with patch(
        "services.transcript.whisper_service.tempfile.mkdtemp",
        return_value=str(tmp_dir),
    ) as mkdtemp_mock, patch(
        "services.media.video_deepdive_service.run_monitored_download",
        side_effect=MonitoredDownloadError("process"),
    ), patch(
        "services.transcript.whisper_service.shutil.rmtree"
    ) as rmtree_mock:
        result = download_audio(video_url)

    assert result is None
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    rmtree_mock.assert_called_once_with(str(tmp_dir), ignore_errors=True)


def test_private_direct_audio_url_is_rejected_before_network_connection():
    with patch("utils.url_safety._connect_to_public_ip") as connect:
        result = download_audio("http://127.0.0.1/private.mp3")

    assert result is None
    connect.assert_not_called()


def test_metadata_audio_url_is_rejected_before_network_connection():
    with patch("utils.url_safety._connect_to_public_ip") as connect:
        result = download_audio("http://169.254.169.254/latest/audio.mp3")

    assert result is None
    connect.assert_not_called()


def test_direct_audio_requires_audio_content_type():
    response = MagicMock(
        status_code=200,
        headers={"Content-Type": "text/html"},
        content=b"<html>not audio</html>",
    )
    with patch(
        "services.transcript.whisper_service.fetch_public_url",
        return_value=response,
    ), patch("services.transcript.whisper_service.tempfile.mkstemp") as mkstemp:
        result = download_audio("https://media.example.com/episode.mp3")

    assert result is None
    mkstemp.assert_not_called()
