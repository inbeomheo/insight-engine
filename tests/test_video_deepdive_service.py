import json
import os
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


_SAMPLE_CONTENT = """
## 설치 가이드

### Step 1: 계정 만들기
**목표**: 대시보드에 들어갈 준비를 합니다.
[스크린샷 1]: 회원가입 버튼과 이메일 입력 화면을 보여주세요.

### Step 2: API 키 확인
**목표**: 연동에 필요한 키를 찾습니다.
[사진 2]: 설정 화면에서 API Keys 메뉴가 선택된 상태를 보여주세요.
"""


def test_extract_visual_suggestions_from_tutorial_markers():
    from services.media.video_deepdive_service import extract_visual_suggestions

    suggestions = extract_visual_suggestions(_SAMPLE_CONTENT)

    assert suggestions == [
        {
            "idx": 1,
            "kind": "screenshot",
            "label": "스크린샷 1",
            "description": "회원가입 버튼과 이메일 입력 화면을 보여주세요.",
            "section": "Step 1: 계정 만들기",
        },
        {
            "idx": 2,
            "kind": "photo",
            "label": "사진 2",
            "description": "설정 화면에서 API Keys 메뉴가 선택된 상태를 보여주세요.",
            "section": "Step 2: API 키 확인",
        },
    ]


def test_markdown_library_roundtrip_preserves_transcript_and_slides(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLibrary,
        VideoSlide,
    )

    lib = VideoDeepDiveLibrary(tmp_path)
    item = lib.write_item(
        video_id="dQw4w9WgXcQ",
        title="테스트 영상",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        transcript="[00:00:01] hello\n[00:00:02] world",
        slides=[
            VideoSlide(
                idx=1,
                t=1.4,
                title="첫 화면",
                note="계정 생성 화면",
                img="/api/video-deepdives/dQw4w9WgXcQ/media/dQw4w9WgXcQ-slide-01.jpg",
                suggestion="회원가입 버튼",
            )
        ],
        visual_suggestions=[{"idx": 1, "kind": "screenshot", "description": "회원가입 버튼"}],
    )

    assert item["id"] == "dQw4w9WgXcQ"
    path = tmp_path / "dQw4w9WgXcQ.md"
    assert path.exists()

    loaded = lib.get_item("dQw4w9WgXcQ")
    assert loaded["meta"]["title"] == "테스트 영상"
    assert loaded["meta"]["slide_count"] == 1
    assert loaded["meta"]["slides"][0]["mmss"] == "00:01"
    assert loaded["body"] == "[00:00:01] hello\n[00:00:02] world"


def test_rejects_path_traversal_video_id(tmp_path):
    from services.media.video_deepdive_service import VideoDeepDiveLibrary

    lib = VideoDeepDiveLibrary(tmp_path)
    with pytest.raises(ValueError):
        lib.get_item("../secret")


def test_select_candidate_times_respects_gap_and_limit():
    from services.media.video_deepdive_service import select_candidate_times

    selected = select_candidate_times([0, 2, 8, 11, 40, 42, 80], max_slides=4, min_gap=10)

    assert selected == [0.0, 11.0, 40.0, 80.0]


def test_transcript_segments_to_text_formats_timestamps():
    from services.media.video_deepdive_service import transcript_segments_to_text

    text = transcript_segments_to_text([
        {"start": 1.2, "text": "첫 문장"},
        {"start": 65.0, "text": "둘째 문장"},
        {"start": "bad", "text": "무시 안 하고 0초"},
    ])

    assert text.splitlines() == [
        "[00:00:01] 첫 문장",
        "[00:01:05] 둘째 문장",
        "[00:00:00] 무시 안 하고 0초",
    ]


def test_owner_namespaces_prevent_public_video_id_collision(tmp_path):
    from services.media.video_deepdive_service import VideoDeepDiveLibrary

    first = VideoDeepDiveLibrary(tmp_path, owner_id="user-a")
    second = VideoDeepDiveLibrary(tmp_path, owner_id="user-b")
    first.write_item(
        video_id="dQw4w9WgXcQ",
        title="A의 영상",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )
    second.write_item(
        video_id="dQw4w9WgXcQ",
        title="B의 영상",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    )

    assert first.item_path("dQw4w9WgXcQ") != second.item_path("dQw4w9WgXcQ")
    assert first.get_item("dQw4w9WgXcQ")["meta"]["title"] == "A의 영상"
    assert second.get_item("dQw4w9WgXcQ")["meta"]["title"] == "B의 영상"
    assert "_owner_scope" not in first.get_item("dQw4w9WgXcQ")["meta"]


def test_media_must_be_owned_and_referenced_by_item(tmp_path):
    from services.media.video_deepdive_service import VideoDeepDiveLibrary, VideoSlide

    lib = VideoDeepDiveLibrary(tmp_path, owner_id="user-a")
    staged = tmp_path / "owned.jpg"
    staged.write_bytes(b"image")
    media_url = lib.media_url("dQw4w9WgXcQ", staged.name)
    lib.write_item(
        video_id="dQw4w9WgXcQ",
        title="A",
        source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        slides=[VideoSlide(idx=1, t=1, img=media_url)],
        media_files=[staged],
    )

    assert lib.media_path("dQw4w9WgXcQ", "owned.jpg").read_bytes() == b"image"
    orphan = lib.media_dir("dQw4w9WgXcQ") / "orphan.jpg"
    orphan.write_bytes(b"private")
    with pytest.raises(FileNotFoundError):
        lib.media_path("dQw4w9WgXcQ", "orphan.jpg")


def test_artifact_storage_limit_is_enforced_before_write(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLibrary,
        VideoDeepDiveLimitError,
        VideoDeepDiveLimits,
    )

    limits = replace(VideoDeepDiveLimits(), max_artifact_bytes=300)
    lib = VideoDeepDiveLibrary(tmp_path, owner_id="user-a", limits=limits)
    with pytest.raises(VideoDeepDiveLimitError):
        lib.write_item(
            video_id="dQw4w9WgXcQ",
            title="A",
            source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            transcript="x" * 1_000,
        )
    assert not lib.item_path("dQw4w9WgXcQ").exists()


def test_download_rejects_video_duration_before_downloading(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLimitError,
        download_youtube_video,
    )

    metadata = subprocess.CompletedProcess(
        [], 0, stdout=json.dumps({"duration": 999, "title": "long"}), stderr=""
    )
    with patch(
        "services.media.video_deepdive_service.require_tool", return_value="yt-dlp"
    ), patch(
        "services.media.video_deepdive_service.run_command", return_value=metadata
    ) as command:
        with pytest.raises(VideoDeepDiveLimitError):
            download_youtube_video(
                "dQw4w9WgXcQ", tmp_path, max_duration_seconds=60
            )

    assert command.call_count == 1


def test_download_cost_callback_runs_after_validation_before_metadata(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLimitError,
        download_youtube_video,
    )

    events = []

    def require_ytdlp(name):
        assert name == "yt-dlp"
        events.append("tool")
        return "yt-dlp"

    def metadata_command(*_args, **_kwargs):
        events.append("metadata")
        return subprocess.CompletedProcess(
            [], 0, stdout=json.dumps({"duration": 999, "title": "long"}), stderr=""
        )

    with patch(
        "services.media.video_deepdive_service.require_tool",
        side_effect=require_ytdlp,
    ), patch(
        "services.media.video_deepdive_service.run_command",
        side_effect=metadata_command,
    ):
        with pytest.raises(VideoDeepDiveLimitError):
            download_youtube_video(
                "dQw4w9WgXcQ",
                tmp_path,
                max_duration_seconds=60,
                on_cost_start=lambda: events.append("cost"),
            )

    assert events == ["tool", "cost", "metadata"]


def test_download_validation_failure_does_not_start_cost(tmp_path):
    from services.media.video_deepdive_service import download_youtube_video

    on_cost_start = MagicMock()
    with patch(
        "services.media.video_deepdive_service.require_tool",
        return_value="yt-dlp",
    ):
        with pytest.raises(ValueError):
            download_youtube_video(
                "https://example.com/watch?v=dQw4w9WgXcQ",
                tmp_path,
                on_cost_start=on_cost_start,
            )

    on_cost_start.assert_not_called()


def test_download_rechecks_lease_before_actual_video_download(tmp_path):
    from services.media.video_deepdive_service import download_youtube_video
    from services.usage.usage_lock import UsageLockUnavailable

    metadata = subprocess.CompletedProcess(
        [], 0, stdout=json.dumps({"duration": 10, "title": "ok"}), stderr=""
    )
    callback = MagicMock(
        side_effect=[None, UsageLockUnavailable("임대 소유권 상실")]
    )
    with patch(
        "services.media.video_deepdive_service.require_tool",
        return_value="yt-dlp",
    ), patch(
        "services.media.video_deepdive_service.run_command",
        return_value=metadata,
    ), patch(
        "services.media.video_deepdive_service.run_monitored_download",
    ) as monitored, pytest.raises(UsageLockUnavailable):
        download_youtube_video(
            "dQw4w9WgXcQ",
            tmp_path,
            on_cost_start=callback,
        )

    assert callback.call_count == 2
    monitored.assert_not_called()


def test_build_checks_storage_then_passes_cost_callback_to_download(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLibrary,
        VideoDeepDiveLimits,
        build_visual_deepdive_from_video,
    )

    events = []
    on_cost_start = MagicMock()
    library = MagicMock(spec=VideoDeepDiveLibrary)
    library.limits = VideoDeepDiveLimits()
    library.assert_can_create.side_effect = lambda _video_id: events.append("capacity")

    def fail_download(*_args, **kwargs):
        events.append("download")
        assert kwargs["on_cost_start"] is on_cost_start
        raise RuntimeError("stop after propagation check")

    with patch(
        "services.media.video_deepdive_service.download_youtube_video",
        side_effect=fail_download,
    ):
        with pytest.raises(RuntimeError, match="propagation check"):
            build_visual_deepdive_from_video(
                url_or_id="dQw4w9WgXcQ",
                library=library,
                on_cost_start=on_cost_start,
            )

    assert events == ["capacity", "download"]
    on_cost_start.assert_not_called()


def test_download_rejects_file_larger_than_cap(tmp_path):
    from services.media.video_deepdive_service import (
        VideoDeepDiveLimitError,
        download_youtube_video,
    )

    def fake_command(args, **_kwargs):
        return subprocess.CompletedProcess(
            args, 0, stdout=json.dumps({"duration": 10, "title": "ok"}), stderr=""
        )

    def fake_download(args, **_kwargs):
        (tmp_path / "video.mp4").write_bytes(b"x" * 20)
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    with patch(
        "services.media.video_deepdive_service.require_tool", return_value="yt-dlp"
    ), patch(
        "services.media.video_deepdive_service.run_command", side_effect=fake_command
    ), patch(
        "services.media.video_deepdive_service.run_monitored_download",
        side_effect=fake_download,
    ):
        with pytest.raises(VideoDeepDiveLimitError):
            download_youtube_video(
                "dQw4w9WgXcQ", tmp_path, max_download_bytes=10
            )

    assert not (tmp_path / "video.mp4").exists()


def test_monitored_download_stops_during_size_overflow_and_cleans_partials(tmp_path):
    from services.media.video_deepdive_service import (
        MonitoredDownloadError,
        run_monitored_download,
    )

    partial = tmp_path / "video.mp4.part"
    writer = """
import os
import pathlib
import sys
import time
p = pathlib.Path(sys.argv[1])
with p.open('wb') as handle:
    for _ in range(100):
        handle.write(b'x' * 4096)
        handle.flush()
        os.fsync(handle.fileno())
        time.sleep(0.02)
time.sleep(10)
"""
    started = time.monotonic()
    with pytest.raises(MonitoredDownloadError) as exc:
        run_monitored_download(
            [sys.executable, "-c", writer, str(partial)],
            watch_root=tmp_path,
            watch_prefix="video",
            max_bytes=8_000,
            timeout=5,
            poll_interval=0.01,
        )

    assert exc.value.reason == "size"
    assert time.monotonic() - started < 2
    assert not list(tmp_path.glob("video*"))


def test_monitored_download_timeout_cleans_partial_file(tmp_path):
    from services.media.video_deepdive_service import (
        MonitoredDownloadError,
        run_monitored_download,
    )

    partial = tmp_path / "video.webm.part"
    sleeper = """
import pathlib
import sys
import time
pathlib.Path(sys.argv[1]).write_bytes(b'partial')
time.sleep(10)
"""
    with pytest.raises(MonitoredDownloadError) as exc:
        run_monitored_download(
            [sys.executable, "-c", sleeper, str(partial)],
            watch_root=tmp_path,
            watch_prefix="video",
            max_bytes=1_000,
            timeout=0.15,
            poll_interval=0.01,
        )

    assert exc.value.reason == "timeout"
    assert not partial.exists()


@pytest.mark.skipif(os.name != "posix", reason="POSIX 프로세스 그룹 회귀 테스트")
def test_monitored_download_kills_child_process_group(tmp_path):
    from services.media.video_deepdive_service import (
        MonitoredDownloadError,
        run_monitored_download,
    )

    partial = tmp_path / "video.mp4.part"
    survived = tmp_path / "child-survived"
    parent = """
import pathlib
import subprocess
import sys
import time
child = "import pathlib,sys,time; time.sleep(0.8); pathlib.Path(sys.argv[1]).write_text('alive')"
subprocess.Popen([sys.executable, '-c', child, sys.argv[2]])
pathlib.Path(sys.argv[1]).write_bytes(b'x' * 16384)
time.sleep(10)
"""
    with pytest.raises(MonitoredDownloadError) as exc:
        run_monitored_download(
            [sys.executable, "-c", parent, str(partial), str(survived)],
            watch_root=tmp_path,
            watch_prefix="video",
            max_bytes=1_000,
            timeout=5,
            poll_interval=0.01,
        )

    assert exc.value.reason == "size"
    time.sleep(1)
    assert not survived.exists()
    assert not partial.exists()


def test_monitored_download_cannot_deadlock_on_large_stdout_stderr(tmp_path):
    from services.media.video_deepdive_service import run_monitored_download

    output = tmp_path / "video.mp4"
    noisy = """
import os
import pathlib
import sys
chunk = b'x' * 65536
for _ in range(32):
    os.write(1, chunk)
    os.write(2, chunk)
pathlib.Path(sys.argv[1]).write_bytes(b'ok')
"""
    result = run_monitored_download(
        [sys.executable, "-c", noisy, str(output)],
        watch_root=tmp_path,
        watch_prefix="video",
        max_bytes=1_000,
        timeout=2,
        poll_interval=0.01,
    )

    assert result.returncode == 0
    assert output.read_bytes() == b"ok"


def test_expired_processing_deadline_fails_closed():
    from services.media.video_deepdive_service import (
        VideoDeepDiveLimitError,
        _bounded_timeout,
    )

    with pytest.raises(VideoDeepDiveLimitError) as exc:
        _bounded_timeout(30, time.monotonic() - 1)
    assert exc.value.status_code == 504
