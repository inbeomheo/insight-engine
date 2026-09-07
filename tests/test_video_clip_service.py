"""video_clip_service 단위 테스트"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from services.media.video_clip_service import (
    _download_video,
    _extract_clip,
    cleanup_clips,
    extract_clips,
)
from services.media.video_deepdive_service import MonitoredDownloadError


class TestVideoClipService(unittest.TestCase):

    def test_extract_clips_empty_list_raises(self):
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', [])

    def test_extract_clips_too_many_raises(self):
        clips = [{'start': '0:00', 'end': '0:10'}] * 11
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', clips)

    def test_extract_clips_missing_fields_raises(self):
        with self.assertRaises(ValueError):
            extract_clips('https://youtube.com/watch?v=test', [{'start': '0:00'}])

    @patch('services.media.video_clip_service._extract_clip')
    @patch('services.media.video_clip_service._download_video')
    def test_extract_clips_success(self, mock_download, mock_extract):
        mock_download.return_value = '/tmp/source.mp4'
        mock_extract.return_value = '/tmp/clip_0.mp4'

        clips = [{'start': '0:00', 'end': '0:30'}]
        result = extract_clips('https://youtube.com/watch?v=dQw4w9WgXcQ', clips)

        self.assertEqual(len(result), 1)
        mock_download.assert_called_once()
        mock_extract.assert_called_once()

    def test_cleanup_clips_nonexistent(self):
        # 존재하지 않는 파일도 에러 없이 처리
        with tempfile.TemporaryDirectory() as td, patch(
            'services.media.video_clip_service.CLIP_OUTPUT_DIR', td
        ):
            cleanup_clips([str(Path(td) / 'clip_1234abcd_0.mp4')])

    def test_cleanup_clips_rejects_file_outside_allowed_root(self):
        with tempfile.TemporaryDirectory() as td, tempfile.TemporaryDirectory() as outside, patch(
            'services.media.video_clip_service.CLIP_OUTPUT_DIR', td
        ):
            victim = Path(outside) / 'clip_1234abcd_0.mp4'
            victim.write_bytes(b'keep')

            with self.assertRaises(ValueError):
                cleanup_clips([str(victim)])

            self.assertEqual(victim.read_bytes(), b'keep')

    def test_extract_clips_rejects_non_youtube_url_before_download(self):
        with patch('services.media.video_clip_service._download_video') as mock_download:
            with self.assertRaises(ValueError):
                extract_clips('file:///etc/passwd', [{'start': '0:00', 'end': '0:10'}])
        mock_download.assert_not_called()

    def test_extract_clips_rejects_overlong_single_clip(self):
        with self.assertRaises(ValueError):
            extract_clips(
                'dQw4w9WgXcQ',
                [{'start': '0:00', 'end': '3:01'}],
            )

    def test_clip_download_maps_live_size_limit_and_uses_unique_prefix(self):
        metadata = subprocess.CompletedProcess(
            [],
            0,
            stdout=json.dumps({'duration': 10}),
            stderr='',
        )
        with tempfile.TemporaryDirectory() as td, patch(
            'services.media.video_clip_service.CLIP_OUTPUT_DIR', td
        ), patch(
            'services.media.video_clip_service._run_process', return_value=metadata
        ), patch(
            'services.media.video_clip_service.run_monitored_download',
            side_effect=MonitoredDownloadError('size'),
        ) as monitored:
            with self.assertRaises(ValueError):
                _download_video('dQw4w9WgXcQ')

        kwargs = monitored.call_args.kwargs
        self.assertEqual(kwargs['watch_root'], str(Path(td).resolve()))
        self.assertTrue(kwargs['watch_prefix'].startswith('source_'))
        self.assertEqual(kwargs['max_bytes'], 512 * 1024 * 1024)


class TestExtractClip(unittest.TestCase):

    @patch('services.media.video_clip_service.subprocess.run')
    def test_extract_clip_ffmpeg_failure(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stderr='error')
        with self.assertRaises(RuntimeError):
            _extract_clip('/tmp/source.mp4', '0:00', '0:30', 0)

    @patch('services.media.video_clip_service.subprocess.run')
    def test_extract_clip_ffmpeg_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        with self.assertRaises(RuntimeError) as ctx:
            _extract_clip('/tmp/source.mp4', '0:00', '0:30', 0)
        self.assertIn('ffmpeg', str(ctx.exception))


if __name__ == '__main__':
    unittest.main()
