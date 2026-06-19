import json
from pathlib import Path

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
