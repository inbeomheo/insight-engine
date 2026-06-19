"""YouTube visual deep-dive utilities.

영상에서 뽑은 화면/슬라이드와 생성된 튜토리얼의 사진 제안을
하나의 markdown-backed study item으로 저장/조회하는 서비스입니다.
외부 도구(yt-dlp/ffmpeg)는 선택적으로 사용하고, 핵심 저장/파싱 로직은
테스트 가능한 순수 Python으로 유지합니다.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
VISUAL_MARKER_RE = re.compile(r"^\[(사진|스크린샷)\s*(\d+)\]\s*:\s*(.+?)\s*$")
SHOWINFO_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")


@dataclass
class VideoSlide:
    """A visual slide/frame attached to a video deep-dive."""

    idx: int
    t: float
    title: str = ""
    note: str = ""
    img: str = ""
    suggestion: str = ""
    source: str = "auto"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "idx": int(self.idx),
            "t": float(self.t),
            "mmss": seconds_to_mmss(self.t),
            "title": self.title or f"화면 {self.idx}",
            "note": self.note or "",
            "img": self.img or "",
            "suggestion": self.suggestion or "",
            "source": self.source or "auto",
        }
        data.update(self.extra)
        return data


def seconds_to_hhmmss(seconds: float | int | str | None) -> str:
    """Return HH:MM:SS for a seconds value, falling back to 0."""
    try:
        total = max(0, int(float(seconds or 0)))
    except (TypeError, ValueError):
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def seconds_to_mmss(seconds: float | int | str | None) -> str:
    """Return MM:SS for slide display, or HH:MM:SS for long videos."""
    hhmmss = seconds_to_hhmmss(seconds)
    return hhmmss[3:] if hhmmss.startswith("00:") else hhmmss


def normalize_youtube_id(value: str) -> str:
    """Extract and validate an 11-character YouTube video id from an id or URL."""
    raw = (value or "").strip()
    if YOUTUBE_ID_RE.match(raw):
        return raw

    parsed = urlparse(raw)
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    candidate = ""
    if "youtu.be" in host:
        candidate = path.split("/", 1)[0]
    elif "youtube.com" in host:
        if path.startswith("shorts/") or path.startswith("embed/"):
            candidate = path.split("/", 1)[1].split("/", 1)[0]
        else:
            candidate = parse_qs(parsed.query).get("v", [""])[0]

    if YOUTUBE_ID_RE.match(candidate):
        return candidate
    raise ValueError("유효한 YouTube 영상 ID가 아닙니다.")


def extract_visual_suggestions(content: str) -> list[dict[str, Any]]:
    """Extract `[사진 N]: ...` / `[스크린샷 N]: ...` markers from generated content.

    The closest previous markdown heading is kept as `section` so the frontend can
    show where that image belongs in the tutorial/course.
    """
    suggestions: list[dict[str, Any]] = []
    current_section = ""
    for line in (content or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            current_section = heading.group(1).strip()
            continue
        marker = VISUAL_MARKER_RE.match(stripped)
        if marker:
            label_kind, number, description = marker.groups()
            idx = int(number)
            suggestions.append(
                {
                    "idx": idx,
                    "kind": "screenshot" if label_kind == "스크린샷" else "photo",
                    "label": f"{label_kind} {idx}",
                    "description": description.strip(),
                    "section": current_section,
                }
            )
    return suggestions


def transcript_segments_to_text(segments: list[dict[str, Any]] | None) -> str:
    """Format transcript segment dicts as `[HH:MM:SS] text` lines."""
    lines: list[str] = []
    for seg in segments or []:
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        lines.append(f"[{seconds_to_hhmmss(seg.get('start', 0))}] {text}")
    return "\n".join(lines)


def select_candidate_times(times: list[float | int], max_slides: int = 24, min_gap: float = 12.0) -> list[float]:
    """Deduplicate scene timestamps by minimum time gap and cap the result."""
    selected: list[float] = []
    for raw in sorted(float(t) for t in times if float(t) >= 0):
        if selected and raw - selected[-1] < min_gap:
            continue
        selected.append(round(raw, 2))
        if len(selected) >= max(1, int(max_slides)):
            break
    return selected


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text or "")
    if not match:
        return {}, text or ""
    raw_meta, body = match.groups()
    try:
        meta = json.loads(raw_meta)
    except json.JSONDecodeError:
        meta = {}
    if body.startswith("## Transcript\n"):
        body = body[len("## Transcript\n") :]
    return meta, body.strip()


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    return "---\n" + json.dumps(meta, ensure_ascii=False, indent=2) + "\n---\n## Transcript\n" + (body or "").strip() + "\n"


class VideoDeepDiveLibrary:
    """Markdown + media storage for video study deep-dives."""

    def __init__(self, root: str | os.PathLike[str] | None = None):
        self.root = Path(root or os.environ.get("VIDEO_DEEPDIVE_DIR", "data/video_deepdives")).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "_media").mkdir(parents=True, exist_ok=True)

    def _safe_id(self, video_id: str) -> str:
        return normalize_youtube_id(video_id)

    def item_path(self, video_id: str) -> Path:
        safe_id = self._safe_id(video_id)
        path = (self.root / f"{safe_id}.md").resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("허용되지 않은 deep-dive 경로입니다.")
        return path

    def media_dir(self, video_id: str) -> Path:
        safe_id = self._safe_id(video_id)
        path = (self.root / "_media" / safe_id).resolve()
        if self.root not in path.parents:
            raise ValueError("허용되지 않은 media 경로입니다.")
        path.mkdir(parents=True, exist_ok=True)
        return path

    def media_url(self, video_id: str, filename: str) -> str:
        safe_id = self._safe_id(video_id)
        clean_name = Path(filename).name
        return f"/api/video-deepdives/{safe_id}/media/{clean_name}"

    def write_item(
        self,
        *,
        video_id: str,
        title: str,
        source_url: str,
        transcript: str = "",
        slides: list[VideoSlide | dict[str, Any]] | None = None,
        visual_suggestions: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        safe_id = self._safe_id(video_id)
        normalized_slides = [s.to_dict() if isinstance(s, VideoSlide) else dict(s) for s in (slides or [])]
        meta = {
            "id": safe_id,
            "title": (title or "YouTube Deep Dive").strip(),
            "youtube_id": safe_id,
            "source_url": source_url or f"https://www.youtube.com/watch?v={safe_id}",
            "created": date.today().isoformat(),
            "slide_count": len(normalized_slides),
            "slides": normalized_slides,
            "visual_suggestions": visual_suggestions or [],
            "tags": tags or [],
        }
        self.item_path(safe_id).write_text(dump_frontmatter(meta, transcript), encoding="utf-8")
        return meta

    def list_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.md")):
            meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
            if not meta:
                continue
            items.append({**meta, "slug": path.stem, "preview": body[:180]})
        return items

    def get_item(self, video_id: str) -> dict[str, Any]:
        path = self.item_path(video_id)
        if not path.exists():
            raise FileNotFoundError("deep-dive 항목을 찾을 수 없습니다.")
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        return {"slug": self._safe_id(video_id), "meta": meta, "body": body}

    def update_slide_notes(self, video_id: str, slides: list[dict[str, Any]]) -> dict[str, Any]:
        loaded = self.get_item(video_id)
        meta = dict(loaded["meta"])
        meta["slides"] = slides
        meta["slide_count"] = len(slides)
        self.item_path(video_id).write_text(dump_frontmatter(meta, loaded["body"]), encoding="utf-8")
        return meta


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} 실행 파일을 찾을 수 없습니다.")
    return path


def run_command(args: list[str], *, timeout: int = 120, cwd: str | os.PathLike[str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, timeout=timeout, check=True, text=True, capture_output=True)


def detect_scene_times(video_path: str | os.PathLike[str], *, threshold: float = 0.30, timeout: int = 180) -> list[float]:
    """Use ffmpeg scene detection and parse candidate timestamps."""
    ffmpeg = require_tool("ffmpeg")
    expr = f"select='gt(scene,{float(threshold):.3f})',showinfo"
    proc = run_command([ffmpeg, "-hide_banner", "-i", str(video_path), "-vf", expr, "-f", "null", "-"], timeout=timeout)
    return [float(m.group(1)) for m in SHOWINFO_TIME_RE.finditer(proc.stderr or "")]


def extract_slide_images(
    *,
    video_id: str,
    video_path: str | os.PathLike[str],
    times: list[float],
    library: VideoDeepDiveLibrary,
    width: int = 1280,
    timeout_per_frame: int = 30,
) -> list[VideoSlide]:
    """Extract selected frames into the deep-dive media folder."""
    ffmpeg = require_tool("ffmpeg")
    safe_id = normalize_youtube_id(video_id)
    out_dir = library.media_dir(safe_id)
    slides: list[VideoSlide] = []
    for idx, t in enumerate(times, 1):
        filename = f"{safe_id}-slide-{idx:02d}.jpg"
        out_path = out_dir / filename
        run_command(
            [
                ffmpeg,
                "-hide_banner",
                "-y",
                "-ss",
                f"{float(t):.2f}",
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                "-vf",
                f"scale={int(width)}:-1",
                "-q:v",
                "3",
                str(out_path),
            ],
            timeout=timeout_per_frame,
        )
        slides.append(
            VideoSlide(
                idx=idx,
                t=float(t),
                title=f"화면 {idx}",
                img=library.media_url(safe_id, filename),
                source="ffmpeg-scene",
            )
        )
    return slides


def download_youtube_video(url_or_id: str, scratch_dir: str | os.PathLike[str], *, timeout: int = 600) -> tuple[str, Path, str]:
    """Download a ≤720p mp4 and return (video_id, path, title). Requires yt-dlp."""
    ytdlp = require_tool("yt-dlp")
    video_id = normalize_youtube_id(url_or_id)
    url = f"https://www.youtube.com/watch?v={video_id}"
    scratch = Path(scratch_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    output_tpl = str(scratch / "video.%(ext)s")
    run_command(
        [
            ytdlp,
            "--no-playlist",
            "--write-info-json",
            "-f",
            "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/best[height<=720]",
            "--merge-output-format",
            "mp4",
            "-o",
            output_tpl,
            url,
        ],
        timeout=timeout,
    )
    video_path = scratch / "video.mp4"
    if not video_path.exists():
        candidates = sorted(scratch.glob("video.*"))
        if not candidates:
            raise RuntimeError("다운로드된 영상 파일을 찾을 수 없습니다.")
        video_path = candidates[0]
    title = "YouTube 영상"
    info_path = scratch / "video.info.json"
    if info_path.exists():
        try:
            title = json.loads(info_path.read_text(encoding="utf-8")).get("title") or title
        except json.JSONDecodeError:
            pass
    return video_id, video_path, title


def build_visual_deepdive_from_video(
    *,
    url_or_id: str,
    transcript: str = "",
    title: str = "",
    content: str = "",
    library: VideoDeepDiveLibrary | None = None,
    max_slides: int = 18,
    scene_threshold: float = 0.30,
    min_gap: float = 12.0,
) -> dict[str, Any]:
    """Download a YouTube video, extract representative screens, and persist an item."""
    lib = library or VideoDeepDiveLibrary()
    with tempfile.TemporaryDirectory(prefix="insight-deepdive-") as td:
        video_id, video_path, downloaded_title = download_youtube_video(url_or_id, td)
        times = select_candidate_times(
            detect_scene_times(video_path, threshold=scene_threshold),
            max_slides=max_slides,
            min_gap=min_gap,
        )
        slides = extract_slide_images(video_id=video_id, video_path=video_path, times=times, library=lib)
        meta = lib.write_item(
            video_id=video_id,
            title=title or downloaded_title,
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            transcript=transcript,
            slides=slides,
            visual_suggestions=extract_visual_suggestions(content),
            tags=["youtube", "visual-deepdive"],
        )
        return {"meta": meta, "slides": [s.to_dict() for s in slides]}
