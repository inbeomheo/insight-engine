import sys
from unittest.mock import MagicMock, patch

from services.transcript.whisper_service import download_audio


def _build_fake_yt_dlp(download_side_effect=None):
    ydl = MagicMock()
    if download_side_effect is not None:
        ydl.download.side_effect = download_side_effect

    fake_yt_dlp = MagicMock()
    fake_yt_dlp.YoutubeDL.return_value.__enter__.return_value = ydl
    fake_yt_dlp.YoutubeDL.return_value.__exit__.return_value = False
    return fake_yt_dlp, ydl


def test_download_audio_returns_wav_path_from_mkdtemp_dir(tmp_path):
    tmp_dir = tmp_path / "ytdlp_audio_dir"
    tmp_dir.mkdir()
    wav_path = tmp_dir / "audio.wav"
    video_url = "https://youtube.com/watch?v=test"

    fake_yt_dlp, ydl = _build_fake_yt_dlp()

    def write_wav(_urls):
        wav_path.write_bytes(b"RIFF....WAVEfmt ")

    ydl.download.side_effect = write_wav

    with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
        with patch(
            "services.transcript.whisper_service.tempfile.mkdtemp",
            return_value=str(tmp_dir),
        ) as mkdtemp_mock:
            with patch("services.transcript.whisper_service.shutil.rmtree") as rmtree_mock:
                result = download_audio(video_url)

    assert result == str(wav_path)
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    ydl.download.assert_called_once_with([video_url])
    rmtree_mock.assert_not_called()


def test_download_audio_returns_none_and_cleans_empty_dir(tmp_path):
    tmp_dir = tmp_path / "empty_audio_dir"
    tmp_dir.mkdir()
    video_url = "https://youtube.com/watch?v=test"

    fake_yt_dlp, ydl = _build_fake_yt_dlp()

    with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
        with patch(
            "services.transcript.whisper_service.tempfile.mkdtemp",
            return_value=str(tmp_dir),
        ) as mkdtemp_mock:
            with patch("services.transcript.whisper_service.shutil.rmtree") as rmtree_mock:
                result = download_audio(video_url)

    assert result is None
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    ydl.download.assert_called_once_with([video_url])
    rmtree_mock.assert_called_once_with(str(tmp_dir), ignore_errors=True)


def test_download_audio_cleans_temp_dir_when_ytdlp_raises(tmp_path):
    tmp_dir = tmp_path / "failed_audio_dir"
    tmp_dir.mkdir()
    video_url = "https://youtube.com/watch?v=test"

    fake_yt_dlp, ydl = _build_fake_yt_dlp(RuntimeError("yt-dlp failed"))

    with patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}):
        with patch(
            "services.transcript.whisper_service.tempfile.mkdtemp",
            return_value=str(tmp_dir),
        ) as mkdtemp_mock:
            with patch("services.transcript.whisper_service.shutil.rmtree") as rmtree_mock:
                result = download_audio(video_url)

    assert result is None
    mkdtemp_mock.assert_called_once_with(prefix="ytdlp_audio_")
    ydl.download.assert_called_once_with([video_url])
    rmtree_mock.assert_called_once_with(str(tmp_dir), ignore_errors=True)
