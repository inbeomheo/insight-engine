"""Video visual deep-dive API routes.

튜토리얼/AI코스 생성 결과의 사진 제안과 YouTube 화면 추출 결과를
markdown-backed deep-dive 라이브러리로 저장/조회합니다.
"""
from __future__ import annotations

from pathlib import Path

from flask import current_app, jsonify, request, send_file

from routes.blog_routes import blog_bp
from services.media.video_deepdive_service import (
    VideoDeepDiveLibrary,
    VideoSlide,
    build_visual_deepdive_from_video,
    extract_visual_suggestions,
    normalize_youtube_id,
    transcript_segments_to_text,
)
from src.contexts.identity.interface.auth_decorators import require_auth


def _library() -> VideoDeepDiveLibrary:
    return VideoDeepDiveLibrary(current_app.config.get("VIDEO_DEEPDIVE_DIR"))


def _json_error(message: str, status: int):
    return jsonify({"error": message}), status


def _slides_from_payload(raw_slides) -> list[VideoSlide | dict]:
    slides: list[VideoSlide | dict] = []
    if not isinstance(raw_slides, list):
        return slides
    for idx, raw in enumerate(raw_slides, 1):
        if not isinstance(raw, dict):
            continue
        try:
            t = float(raw.get("t", raw.get("start", 0)) or 0)
        except (TypeError, ValueError):
            t = 0.0
        slides.append(
            VideoSlide(
                idx=int(raw.get("idx") or idx),
                t=t,
                title=str(raw.get("title") or f"화면 {idx}"),
                note=str(raw.get("note") or ""),
                img=str(raw.get("img") or ""),
                suggestion=str(raw.get("suggestion") or ""),
                source=str(raw.get("source") or "manual"),
            )
        )
    return slides


@blog_bp.route("/api/video-deepdives", methods=["GET"])
@require_auth
def list_video_deepdives():
    """List saved video deep-dive items."""
    items = _library().list_items()
    return jsonify({"items": items, "total": len(items)})


@blog_bp.route("/api/video-deepdives/from-result", methods=["POST"])
@require_auth
def create_video_deepdive_from_result():
    """Persist a deep-dive item from an already generated result.

    This is the cheap path used immediately after tutorial/course generation:
    it extracts `[사진 N]`/`[스크린샷 N]` markers and stores transcript text if present.
    """
    data = request.get_json(silent=True) or {}
    try:
        video_id = normalize_youtube_id(str(data.get("video_id") or data.get("url") or data.get("source_url") or ""))
    except ValueError as exc:
        return _json_error(str(exc), 400)

    transcript = str(data.get("transcript") or "").strip()
    if not transcript:
        transcript = transcript_segments_to_text(data.get("transcript_segments") or [])

    content = str(data.get("content") or "")
    item = _library().write_item(
        video_id=video_id,
        title=str(data.get("title") or "YouTube Deep Dive"),
        source_url=str(data.get("source_url") or f"https://www.youtube.com/watch?v={video_id}"),
        transcript=transcript,
        slides=_slides_from_payload(data.get("slides")),
        visual_suggestions=extract_visual_suggestions(content),
        tags=["youtube", "generated-result"],
    )
    return jsonify({"item": item, "viewer_url": f"/deepdives/{video_id}"}), 201


@blog_bp.route("/api/video-deepdives/extract", methods=["POST"])
@require_auth
def extract_video_deepdive():
    """Download a YouTube video, extract representative frames, and save a deep-dive.

    Requires `yt-dlp` and `ffmpeg` in the deployed environment. This route is
    intentionally explicit because it can be slow and should be triggered by a
    user action, not by every generation request.
    """
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or data.get("video_id") or "").strip()
    if not url:
        return _json_error("YouTube URL 또는 영상 ID가 필요합니다.", 400)
    try:
        result = build_visual_deepdive_from_video(
            url_or_id=url,
            transcript=str(data.get("transcript") or ""),
            title=str(data.get("title") or ""),
            content=str(data.get("content") or ""),
            library=_library(),
            max_slides=min(max(int(data.get("max_slides") or 18), 1), 40),
            scene_threshold=float(data.get("scene_threshold") or 0.30),
            min_gap=float(data.get("min_gap") or 12.0),
        )
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except RuntimeError as exc:
        return _json_error(str(exc), 503)
    return jsonify({**result, "viewer_url": f"/deepdives/{result['meta']['id']}"}), 201


@blog_bp.route("/api/video-deepdives/<video_id>", methods=["GET"])
@blog_bp.route("/api/video-deepdives/<path:video_id>", methods=["GET"])
@require_auth
def get_video_deepdive(video_id: str):
    try:
        item = _library().get_item(video_id)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    return jsonify(item)


@blog_bp.route("/api/video-deepdives/<video_id>", methods=["PATCH"])
@blog_bp.route("/api/video-deepdives/<path:video_id>", methods=["PATCH"])
@require_auth
def patch_video_deepdive(video_id: str):
    data = request.get_json(silent=True) or {}
    slides = data.get("slides")
    if not isinstance(slides, list):
        return _json_error("slides 배열이 필요합니다.", 400)
    try:
        item = _library().update_slide_notes(video_id, slides)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    return jsonify({"ok": True, "item": item})


@blog_bp.route("/api/video-deepdives/<video_id>/media/<filename>", methods=["GET"])
@require_auth
def get_video_deepdive_media(video_id: str, filename: str):
    try:
        safe_id = normalize_youtube_id(video_id)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    clean = Path(filename).name
    media_path = _library().media_dir(safe_id) / clean
    if not media_path.exists() or not media_path.is_file():
        return _json_error("미디어 파일을 찾을 수 없습니다.", 404)
    return send_file(media_path)
