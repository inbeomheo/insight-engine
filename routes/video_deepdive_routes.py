"""Video visual deep-dive API routes.

튜토리얼/AI코스 생성 결과의 사진 제안과 YouTube 화면 추출 결과를
markdown-backed deep-dive 라이브러리로 저장/조회합니다.
"""
from __future__ import annotations

import math

from flask import current_app, g, jsonify, request, send_file
from flask_limiter.util import get_remote_address

from extensions import limiter
from routes.blog_routes import blog_bp
from services.media.video_deepdive_service import (
    VideoDeepDiveBusyError,
    VideoDeepDiveLibrary,
    VideoDeepDiveLimitError,
    VideoDeepDiveLimits,
    VideoSlide,
    build_visual_deepdive_from_video,
    extract_visual_suggestions,
    normalize_youtube_id,
    transcript_segments_to_text,
)
from services.usage import capture_usage_charge_callback, require_usage
from services.usage.usage_lock import UsageLockUnavailable
from src.contexts.identity.interface.auth_decorators import require_auth
from utils.responses import api_error


def _library() -> VideoDeepDiveLibrary:
    # Supabase가 꺼진 로컬 모드도 명시적 네임스페이스를 사용해 기존의
    # 전역 공개 디렉터리로 되돌아가지 않게 한다.
    owner_id = str(g.get("user_id") or "local-anonymous")
    limits = VideoDeepDiveLimits.from_config(current_app.config)
    return VideoDeepDiveLibrary(
        current_app.config.get("VIDEO_DEEPDIVE_DIR"),
        owner_id=owner_id,
        limits=limits,
    )


def _extract_rate_limit_key() -> str:
    return f"video-deepdive:{g.get('user_id') or get_remote_address()}"


def _json_error(message: str, status: int):
    return api_error(message, status)


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
        if not math.isfinite(t) or t < 0:
            t = 0.0
        try:
            slide_idx = int(raw.get("idx") or idx)
        except (TypeError, ValueError):
            slide_idx = idx
        slides.append(
            VideoSlide(
                idx=slide_idx,
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
    try:
        item = _library().write_item(
            video_id=video_id,
            title=str(data.get("title") or "YouTube Deep Dive"),
            source_url=str(data.get("source_url") or f"https://www.youtube.com/watch?v={video_id}"),
            transcript=transcript,
            slides=_slides_from_payload(data.get("slides")),
            visual_suggestions=extract_visual_suggestions(content),
            tags=["youtube", "generated-result"],
        )
    except VideoDeepDiveLimitError as exc:
        return api_error(str(exc), exc.status_code, exc.code)
    except (TypeError, ValueError) as exc:
        return _json_error(str(exc), 400)
    return jsonify({"item": item, "viewer_url": f"/deepdives/{video_id}"}), 201


@blog_bp.route("/api/video-deepdives/extract", methods=["POST"])
@require_auth
@limiter.limit("2/hour;5/day", key_func=_extract_rate_limit_key)
@require_usage
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
    library = _library()
    try:
        max_slides = int(data.get("max_slides") or 18)
        scene_threshold = float(data.get("scene_threshold") or 0.30)
        min_gap = float(data.get("min_gap") or 12.0)
        if not math.isfinite(scene_threshold) or not math.isfinite(min_gap):
            raise ValueError("scene_threshold와 min_gap은 유한한 숫자여야 합니다.")
        with library.extraction_slot():
            result = build_visual_deepdive_from_video(
                url_or_id=url,
                transcript=str(data.get("transcript") or ""),
                title=str(data.get("title") or ""),
                content=str(data.get("content") or ""),
                library=library,
                max_slides=min(max(max_slides, 1), library.limits.max_slides),
                scene_threshold=scene_threshold,
                min_gap=min_gap,
                limits=library.limits,
                on_cost_start=capture_usage_charge_callback(),
            )
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except VideoDeepDiveBusyError as exc:
        return api_error(str(exc), 409, "VIDEO_DEEPDIVE_BUSY")
    except VideoDeepDiveLimitError as exc:
        return api_error(str(exc), exc.status_code, exc.code)
    except UsageLockUnavailable:
        # require_usage가 표준 503/USAGE_LOCK_UNAVAILABLE 응답으로
        # 변환할 수 있도록 임대 상실 신호를 보존한다.
        raise
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
    except VideoDeepDiveLimitError as exc:
        return api_error(str(exc), exc.status_code, exc.code)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except FileNotFoundError as exc:
        return _json_error(str(exc), 404)
    return jsonify({"ok": True, "item": item})


@blog_bp.route("/api/video-deepdives/<video_id>/media/<filename>", methods=["GET"])
@require_auth
def get_video_deepdive_media(video_id: str, filename: str):
    try:
        media_path = _library().media_path(video_id, filename, require_referenced=True)
    except ValueError as exc:
        return _json_error(str(exc), 400)
    except FileNotFoundError:
        return _json_error("미디어 파일을 찾을 수 없습니다.", 404)
    return send_file(media_path)
