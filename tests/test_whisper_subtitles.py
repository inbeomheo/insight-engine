import os
import sys
from unittest.mock import MagicMock, mock_open, patch

from services.transcript.whisper_service import (
    _parse_subtitle_text,
    extract_subtitles_ytdlp,
)


def _build_yt_dlp_mock():
    yt_dlp_mock = MagicMock()
    ydl_context = yt_dlp_mock.YoutubeDL.return_value
    ydl = ydl_context.__enter__.return_value
    ydl_context.__exit__.return_value = False
    return yt_dlp_mock, ydl


def test_extract_subtitles_ytdlp_reads_vtt_and_returns_clean_text():
    video_url = "https://youtu.be/dQw4w9WgXcQ?feature=share"
    tmp_dir = r"C:\tmp\ytdlp_subs_test"
    sub_file = os.path.join(tmp_dir, "subs.ko.vtt")
    raw_vtt = """WEBVTT

NOTE metadata that should be ignored

00:00:00.000 --> 00:00:02.000
<v Speaker><b>First</b> cleaned subtitle line</v>

00:00:02.500 --> 00:00:04.000
<c.colorE5E5E5>Second <u>cleaned</u> subtitle line</c>

00:00:04.000 --> 00:00:06.000
Third cleaned subtitle line
"""
    expected = (
        "First cleaned subtitle line "
        "Second cleaned subtitle line "
        "Third cleaned subtitle line"
    )

    yt_dlp_mock, ydl = _build_yt_dlp_mock()
    open_mock = mock_open(read_data=raw_vtt)

    with patch.dict(sys.modules, {"yt_dlp": yt_dlp_mock}):
        with patch(
            "services.transcript.whisper_service.tempfile.mkdtemp",
            return_value=tmp_dir,
        ):
            with patch(
                "services.transcript.whisper_service.os.path.exists",
                side_effect=lambda path: path == sub_file,
            ):
                with patch(
                    "services.transcript.whisper_service.os.path.getsize",
                    return_value=123,
                ):
                    with patch(
                        "services.transcript.whisper_service.open",
                        open_mock,
                        create=True,
                    ):
                        result = extract_subtitles_ytdlp(video_url)

    assert result == expected
    ydl.download.assert_called_once_with([
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    ])
    open_mock.assert_called_once_with(
        sub_file,
        "r",
        encoding="utf-8",
        errors="ignore",
    )


def test_parse_subtitle_text_removes_headers_timestamps_html_and_duplicates():
    raw = """WEBVTT

NOTE metadata that should be ignored

00:00:00.000 --> 00:00:02.000
<v Speaker><b>Hello</b> <i>world</i></v>

1
00:00:02.500 --> 00:00:04.000
<v Speaker>Hello world</v>

2
00:00:04.000 --> 00:00:06.000
<c.colorE5E5E5>Subtitle <u>line</u></c>

00:00:06.500 --> 00:00:08.000
<c.colorE5E5E5>Subtitle <u>line</u></c>

00:00:08.500 --> 00:00:10.000
Final <font color="red">text</font>
"""

    assert _parse_subtitle_text(raw) == "Hello world Subtitle line Final text"
